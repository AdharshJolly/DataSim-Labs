import numpy as np
import pandas as pd
from typing import Dict, Any, List

from app.engine.dataset_generator import DatasetGenerator, AttributeSpec
from app.engine.distribution_engine import sample_numeric, sample_weighted_categories
from app.models.data_profile import DataProfile

class EnhancedDatasetGenerator(DatasetGenerator):
    """Generates synthetic data using learned statistical profiles and dependency graphs."""

    def __init__(self, seed: int | None = None) -> None:
        super().__init__(seed)

    def generate_from_profile(
        self,
        profile: DataProfile,
        row_count: int,
        realism_rules: list[dict] | None = None,
    ) -> pd.DataFrame:
        """Generate data using a learned data profile, honoring dependencies."""
        frame, _ = self._generate_from_profile_with_stats(profile, row_count, realism_rules)
        return frame

    def _generate_from_profile_with_stats(
        self,
        profile: DataProfile,
        row_count: int,
        realism_rules: list[dict] | None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        # 1. Determine generation order based on dependencies
        dependency_graph = profile.dependency_graph
        all_columns = list(profile.columns.keys())

        # Build dependency adjacency list: target -> list of sources it depends on
        dependencies = {col: [] for col in all_columns}
        for dep in dependency_graph:
            dependencies[dep["target"]].append(dep)

        # Topo sort the columns
        ordered_columns = self._topological_sort(all_columns, dependencies)

        # 2. Generate data column by column
        data: dict[str, pd.Series] = {}
        frame = pd.DataFrame(index=range(row_count))

        for col in ordered_columns:
            col_profile = profile.columns[col]
            col_deps = dependencies[col]

            # Generate base column data
            series = self._generate_profile_column(col_profile, row_count)

            # Apply dependencies if any exist
            if col_deps:
                series = self._apply_dependencies(series, frame, col_deps, col_profile)

            frame[col] = series

        realism_stats: dict[str, Any] = {
            "rule_impacts": {},
            "total_rows_affected": 0,
            "rule_count": 0,
        }

        # Apply realism rules
        if realism_rules:
            from app.engine.realism_processor import RealismProcessor
            processor = RealismProcessor(faker=self.faker, rng=self.rng)
            frame, realism_stats = processor.apply_with_stats(frame, realism_rules)

        # Apply nulls based on learned null_percentage
        from app.engine.null_injector import inject_nulls
        for col in ordered_columns:
            null_pct = profile.columns[col].get("null_percentage", 0.0)
            frame[col] = inject_nulls(
                series=frame[col],
                null_percentage=null_pct,
                rng=self.rng,
            )

        return frame, realism_stats

    def _topological_sort(self, columns: List[str], dependencies: Dict[str, List[Dict]]) -> List[str]:
        """Sort columns so dependencies are generated first."""
        visited = set()
        temp_mark = set()
        order = []

        def visit(node):
            if node in temp_mark:
                # Cycle detected, just ignore for now and break it
                return
            if node not in visited:
                temp_mark.add(node)
                for dep in dependencies.get(node, []):
                    visit(dep["source"])
                temp_mark.remove(node)
                visited.add(node)
                order.append(node)

        for col in columns:
            if col not in visited:
                visit(col)

        return order

    def _generate_profile_column(self, col_profile: Dict[str, Any], row_count: int) -> pd.Series:
        """Generate a single column from its distribution profile independently."""
        data_type = col_profile.get("data_type")
        dist = col_profile.get("distribution", {})
        name = col_profile.get("name")

        if data_type in ["integer", "float"]:
            minimum = dist.get("min", 0.0)
            maximum = dist.get("max", 100.0)
            if minimum == maximum:
                values = np.full(row_count, minimum)
            else:
                values = sample_numeric(
                    count=row_count,
                    distribution=dist.get("type", "uniform"),
                    minimum=minimum,
                    maximum=maximum,
                    rng=self.rng,
                    skew_direction=dist.get("skew_direction", "right"),
                    skew_intensity=abs(dist.get("skewness", 2.0)),
                )
            series = pd.Series(values, name=name)
            if data_type == "integer":
                series = series.round().astype(int)
            return series

        if data_type in ["categorical", "boolean"]:
            categories = dist.get("categories", ["N/A"])
            probabilities = dist.get("probabilities", None)
            if not categories:
                categories = ["N/A"]
                probabilities = [1.0]
            values = sample_weighted_categories(categories, probabilities, row_count, self.rng)
            return pd.Series(values, name=name)

        if data_type == "date":
            # Basic fallback for dates without specific generator config, since date_generator requires strings
            min_date = dist.get("min_date", "2000-01-01")
            max_date = dist.get("max_date", "2020-01-01")
            start = pd.to_datetime(min_date).value
            end = pd.to_datetime(max_date).value
            values = self.rng.integers(start, end, size=row_count)
            return pd.Series(pd.to_datetime(values), name=name)

        if data_type == "text":
            from app.engine.generators.text_generator import generate_text
            # We use Faker text generator since we only have length profiles for now
            return generate_text(name, {}, row_count, self.rng, self.faker)

        return pd.Series([None] * row_count, name=name)

    def _apply_dependencies(self, series: pd.Series, frame: pd.DataFrame, deps: List[Dict], col_profile: Dict[str, Any]) -> pd.Series:
        """Modify generated series based on dependencies on already generated columns."""
        for dep in deps:
            source_col = dep["source"]
            if source_col not in frame.columns:
                continue

            dep_type = dep.get("type")

            if dep_type == "linear_correlation":
                corr = dep.get("correlation", 0.0)
                # Combine source column and base series to induce correlation
                # This is a basic approach: target = source * corr + noise * sqrt(1 - corr^2)
                source_series = frame[source_col]
                # Normalize source
                source_norm = (source_series - source_series.mean()) / (source_series.std() + 1e-9)
                target_norm = (series - series.mean()) / (series.std() + 1e-9)

                # Combine
                combined = source_norm * corr + target_norm * np.sqrt(1 - corr**2)

                # Scale back to target distribution
                series = combined * series.std() + series.mean()
                if col_profile.get("data_type") == "integer":
                    series = series.round().astype(int)

            elif dep_type == "categorical_mapping":
                mapping = dep.get("mapping", {})
                source_series = frame[source_col]

                def map_value(val, original_val):
                    val_str = str(val)
                    if val_str in mapping:
                        if self.rng.random() < mapping[val_str]["probability"]:
                            # Attempt to cast mapped value to correct type
                            target_val = mapping[val_str]["value"]
                            try:
                                if col_profile.get("data_type") == "integer":
                                    return int(float(target_val))
                                elif col_profile.get("data_type") == "float":
                                    return float(target_val)
                                elif col_profile.get("data_type") == "boolean":
                                    return str(target_val).lower() in ["true", "1", "t", "yes"]
                                return target_val
                            except (ValueError, TypeError):
                                return target_val
                    return original_val

                series = pd.Series([map_value(s, t) for s, t in zip(source_series, series)])

            elif dep_type == "conditional_numeric":
                cond_dists = dep.get("distributions", {})
                source_series = frame[source_col]

                def generate_cond(val, original_val):
                    val_str = str(val)
                    if val_str in cond_dists:
                        dist = cond_dists[val_str]
                        mean = dist.get("mean", original_val)
                        std = dist.get("std", 1.0)
                        # Generate normally distributed point
                        new_val = self.rng.normal(mean, std)
                        if col_profile.get("data_type") == "integer":
                            return int(round(new_val))
                        return float(new_val)
                    return original_val

                series = pd.Series([generate_cond(s, t) for s, t in zip(source_series, series)])

        return series
