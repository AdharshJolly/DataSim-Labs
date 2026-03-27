import numpy as np
import pandas as pd
from typing import Dict, Any, List
from scipy import stats

from app.engine.dataset_generator import DatasetGenerator
from app.engine.distribution_engine import sample_numeric, sample_weighted_categories
from app.engine.generators.faker_generator import (
    generate_address,
    generate_city,
    generate_company,
    generate_country,
    generate_email,
    generate_gender,
    generate_name,
    generate_phone,
    generate_url,
    generate_zip,
)
from app.engine.generators.identity_generator import (
    detect_semantic_type,
    generate_identity_batch,
)
from app.models.data_profile import DataProfile
from app.engine.semantic_rule_engine import (
    SemanticRuleEngine,
    filter_rules_by_confidence,
    sort_rules_by_priority,
    CONFIDENCE_THRESHOLD,
)


class EnhancedDatasetGenerator(DatasetGenerator):
    """Generates synthetic data using learned statistical profiles, Gaussian Copulas, and CPTs."""

    def __init__(self, seed: int | None = None) -> None:
        super().__init__(seed)

    def generate_from_profile(
        self,
        profile: DataProfile,
        row_count: int,
        realism_rules: list[dict] | None = None,
    ) -> pd.DataFrame:
        frame, _ = self._generate_from_profile_with_stats(
            profile, row_count, realism_rules
        )
        return frame

    def _nearest_psd(self, matrix: np.ndarray, threshold: float = 1e-8) -> np.ndarray:
        """Find the nearest positive semi-definite matrix using eigenvalue decomposition."""
        matrix = (matrix + matrix.T) / 2.0
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        eigenvalues_clipped = np.maximum(eigenvalues, threshold)
        psd_matrix = eigenvectors @ np.diag(eigenvalues_clipped) @ eigenvectors.T
        d = 1.0 / np.sqrt(np.diag(psd_matrix))
        psd_matrix = psd_matrix * d[:, np.newaxis] * d[np.newaxis, :]
        return (psd_matrix + psd_matrix.T) / 2.0

    def _generate_from_profile_with_stats(
        self,
        profile: DataProfile,
        row_count: int,
        realism_rules: list[dict] | None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        # 1. Determine generation order based on dependencies
        dependency_graph = profile.dependency_graph
        all_columns = list(profile.columns.keys())

        # Adjacency list for topological sort
        adj = {col: [] for col in all_columns}

        copula_cols = set()
        for dep in dependency_graph:
            if dep.get("type") == "multivariate_copula":
                copula_cols.update(dep.get("target", []))
            elif dep.get("type") in [
                "conditional_probability",
                "conditional_numeric",
                "linear_regression",
                "numeric_to_categorical",
            ]:
                targets = (
                    [dep["target"]] if isinstance(dep["target"], str) else dep["target"]
                )
                sources = (
                    dep["sources"]
                    if isinstance(dep["sources"], list)
                    else [dep["sources"]]
                )
                for t in targets:
                    for s in sources:
                        adj[t].append(s)

        ordered_columns = self._topological_sort(all_columns, adj)

        semantic_rules = getattr(profile, "semantic_rules", []) or []
        filtered_semantic_rules = filter_rules_by_confidence(
            semantic_rules, CONFIDENCE_THRESHOLD
        )
        sorted_semantic_rules = self._topological_sort_semantic_rules(
            filtered_semantic_rules
        )
        _, dependent_semantic_columns = self._extract_dependencies(
            sorted_semantic_rules
        )

        data: dict[str, pd.Series] = {}
        frame = pd.DataFrame(index=range(row_count))

        semantic_group_columns = self._apply_semantic_groups(
            frame=frame,
            profile=profile,
            row_count=row_count,
            all_columns=all_columns,
        )

        # 2. Generate Multivariate Copula Data first
        if copula_cols and hasattr(profile, "correlation_matrices"):
            corr_matrices = profile.correlation_matrices
            if corr_matrices and "spearman" in corr_matrices:
                cols = corr_matrices.get("columns", [])
                # Ensure we only use columns that are in profile
                cols = [c for c in cols if c in all_columns]

                if len(cols) > 0:
                    spearman_matrix = (
                        pd.DataFrame(corr_matrices["spearman"])
                        .loc[cols, cols]
                        .fillna(0)
                        .values
                    )

                    low_confidence = bool(profile.metadata.get("low_confidence", False)) or int(profile.row_count) < 50
                    if low_confidence:
                        shrinkage_factor = max(0.3, min(1.0, float(profile.row_count) / 100.0))
                        identity = np.eye(len(cols))
                        spearman_matrix = (
                            shrinkage_factor * spearman_matrix
                            + (1.0 - shrinkage_factor) * identity
                        )

                    cond_number = np.linalg.cond(spearman_matrix)
                    if cond_number > 1e10:
                        import logging

                        logging.warning(
                            f"Correlation matrix condition number is very high ({cond_number}). Adjusting to PSD."
                        )

                    spearman_matrix = self._nearest_psd(spearman_matrix)

                    # Generate Z ~ N(0, R)
                    try:
                        Z = self.rng.multivariate_normal(
                            mean=np.zeros(len(cols)),
                            cov=spearman_matrix,
                            size=row_count,
                        )
                        U = stats.norm.cdf(Z)

                        for i, col in enumerate(cols):
                            if col in semantic_group_columns:
                                continue
                            col_prof = profile.columns[col]
                            frame[col] = self._inverse_transform_sample(
                                U[:, i], col_prof
                            )
                    except Exception as e:
                        raise ValueError(
                            f"Multivariate copula generation failed for profiled dependency columns: {e}"
                        ) from e
            elif copula_cols:
                raise ValueError(
                    "Profile dependency graph requires copula sampling, but correlation matrices are missing."
                )

        # 3. Generate remaining columns except semantic-rule targets
        for col in ordered_columns:
            if col in semantic_group_columns:
                continue

            # Semantic-rule targets are generated only via semantic rules.
            if col in dependent_semantic_columns:
                continue

            col_profile = profile.columns[col]

            # If already generated by copula, skip base generation
            if col not in frame.columns:
                frame[col] = self._generate_profile_column(col_profile, row_count)

            # Find dependencies where this column is the target (excluding copula)
            col_deps = [
                d
                for d in dependency_graph
                if d.get("type") != "multivariate_copula"
                and (
                    (isinstance(d.get("target"), str) and d.get("target") == col)
                    or (isinstance(d.get("target"), list) and col in d.get("target"))
                )
            ]

            if col_deps:
                frame[col] = self._apply_dependencies(
                    frame[col], frame, col_deps, col_profile
                )

        # 4. Apply Semantic Rules (row-by-row, after base columns are generated)
        semantic_stats: dict[str, Any] = {
            "rules_applied": [],
            "rows_affected": 0,
            "errors": [],
        }
        
        semantic_rules_to_apply = [
            rule
            for rule in sorted_semantic_rules
            if str(rule.get("target", "")).strip() not in semantic_group_columns
        ]

        if semantic_rules_to_apply:
            frame, semantic_stats = self._apply_semantic_rules(
                frame,
                semantic_rules_to_apply,
                all_columns,
            )

        realism_stats: dict[str, Any] = {
            "rule_impacts": {},
            "total_rows_affected": 0,
            "rule_count": 0,
        }

        if realism_rules:
            from app.engine.realism_processor import RealismProcessor

            processor = RealismProcessor(faker=self.faker, rng=self.rng)
            frame, realism_stats = processor.apply_with_stats(frame, realism_rules)

        # Inject Nulls
        from app.engine.null_injector import inject_nulls

        for col in ordered_columns:
            if col not in frame.columns:
                frame[col] = pd.Series([None] * row_count, name=col)
            null_pct = profile.columns[col].get("null_percentage", 0.0)
            frame[col] = inject_nulls(
                series=frame[col],
                null_percentage=null_pct,
                rng=self.rng,
            )

        return frame, realism_stats

    def _apply_semantic_groups(
        self,
        frame: pd.DataFrame,
        profile: DataProfile,
        row_count: int,
        all_columns: List[str],
    ) -> set[str]:
        """Generate identity-linked semantic columns before independent generators run."""
        groups = getattr(profile, "semantic_groups", []) or []
        generated_columns: set[str] = set()

        for group in groups:
            if str(group.get("type", "")).lower() != "identity":
                continue

            group_columns = [
                str(column)
                for column in group.get("columns", [])
                if str(column) in all_columns
            ]
            if not group_columns or any(col in generated_columns for col in group_columns):
                continue

            identity_data = generate_identity_batch(
                row_count=row_count,
                faker=self.faker,
                rng=self.rng,
                columns=group_columns,
                email_domains=group.get("observed_domains"),
                email_domain_weights=group.get("observed_domain_weights"),
                column_type_map=group.get("column_type_map"),
                unique=True,
            )
            for column in group_columns:
                # Identity-linked values take priority over independently generated values.
                frame[column] = pd.Series(identity_data[column], name=column)
                generated_columns.add(column)

        return generated_columns

    def _inverse_transform_sample(
        self, u_values: np.ndarray, col_profile: Dict[str, Any]
    ) -> pd.Series:
        """Sample from quantile data or histogram using inverse CDF (U is uniform [0,1])."""
        data_type = col_profile.get("data_type")
        dist = col_profile.get("distribution", {})
        name = col_profile.get("name")
        semantic_type = (
            col_profile.get("semantic_type")
            or dist.get("semantic_type")
            or detect_semantic_type(name)
        )

        if "quantiles" in dist:
            quantiles = np.array(dist["quantiles"])
            q_levels = np.linspace(0, 1, len(quantiles))
            sampled = np.interp(u_values, q_levels, quantiles)
        else:
            if not dist:
                raise ValueError(
                    f"Missing learned distribution for profile column '{name}'."
                )
            # Fallback to normal/uniform based on min/max/mean/std
            mean = dist.get("mean", 0.0)
            std = dist.get("std", 1.0)
            minimum = dist.get("min", 0.0)
            maximum = dist.get("max", 1.0)

            if dist.get("type") == "normal" and std > 0:
                sampled = stats.norm.ppf(u_values, loc=mean, scale=std)
                sampled = np.clip(sampled, minimum, maximum)
            else:
                sampled = minimum + u_values * (maximum - minimum)

        series = pd.Series(sampled, name=name)
        if data_type == "integer":
            series = series.round().astype(int)
        return series

    def _topological_sort(
        self, columns: List[str], adj: Dict[str, List[str]]
    ) -> List[str]:
        """Sort columns so sources are generated before targets."""
        visited = set()
        temp_mark = set()
        order = []

        def visit(node):
            if node in temp_mark:
                return
            if node not in visited:
                temp_mark.add(node)
                for src in adj.get(node, []):
                    if src in columns:
                        visit(src)
                temp_mark.remove(node)
                visited.add(node)
                order.append(node)

        for col in columns:
            if col not in visited:
                visit(col)

        return order

    def _generate_profile_column(
        self, col_profile: Dict[str, Any], row_count: int
    ) -> pd.Series:
        """Generate a single column independently if copula isn't used."""
        data_type = col_profile.get("data_type")
        dist = col_profile.get("distribution", {})
        name = col_profile.get("name")
        semantic_type = (
            col_profile.get("semantic_type")
            or dist.get("semantic_type")
            or detect_semantic_type(name)
        )

        if data_type in ["integer", "float"]:
            u_values = self.rng.uniform(0, 1, size=row_count)
            return self._inverse_transform_sample(u_values, col_profile)

        if data_type in ["categorical", "boolean"]:
            if semantic_type == "name":
                return generate_name(name, row_count, self.faker)
            if semantic_type == "email":
                return generate_email(name, row_count, self.faker)
            categories = dist.get("categories", ["N/A"])
            probabilities = dist.get("probabilities", None)
            if not categories:
                categories = ["N/A"]
                probabilities = [1.0]
            values = sample_weighted_categories(
                categories, probabilities, row_count, self.rng
            )
            return pd.Series(values, name=name)

        if data_type == "date":
            min_date = dist.get("min_date", "2000-01-01")
            max_date = dist.get("max_date", "2020-01-01")
            start = pd.to_datetime(min_date).value
            end = pd.to_datetime(max_date).value
            values = self.rng.integers(start, end, size=row_count)
            return pd.Series(pd.to_datetime(values), name=name)

        if data_type == "text":
            from app.engine.generators.text_generator import generate_text

            return generate_text(name, {}, row_count, self.rng, self.faker)

        if data_type == "semantic":
            if semantic_type == "email":
                return generate_email(name, row_count, self.faker)
            if semantic_type == "name":
                return generate_name(name, row_count, self.faker)
            if semantic_type == "address":
                return generate_address(name, row_count, self.faker)
            if semantic_type == "phone":
                return generate_phone(name, row_count, self.faker)
            if semantic_type == "url":
                return generate_url(name, row_count, self.faker)
            if semantic_type == "company":
                return generate_company(name, row_count, self.faker)
            if semantic_type == "city":
                return generate_city(name, row_count, self.faker)
            if semantic_type == "country":
                return generate_country(name, row_count, self.faker)
            if semantic_type == "zip":
                return generate_zip(name, row_count, self.faker)
            if semantic_type == "gender":
                return generate_gender(name, row_count, self.faker)
            from app.engine.generators.text_generator import generate_text

            return generate_text(name, {}, row_count, self.rng, self.faker)

        return pd.Series([None] * row_count, name=name)

    def _apply_dependencies(
        self,
        series: pd.Series,
        frame: pd.DataFrame,
        deps: List[Dict],
        col_profile: Dict[str, Any],
    ) -> pd.Series:
        """Modify series using advanced conditional models (CPTs, Regression, Conditional Numeric)."""
        for dep in deps:
            sources = dep.get("sources", [])
            if isinstance(sources, str):
                sources = [sources]

            if any(src not in frame.columns for src in sources):
                continue

            dep_type = dep.get("type")
            model = dep.get("model", {})

            if dep_type == "conditional_probability":
                cpt = model.get("cpt", {})
                source_col = sources[0]

                def sample_cpt(src_val):
                    src_str = str(src_val)
                    if src_str in cpt:
                        probs = cpt[src_str]
                        cats = list(probs.keys())
                        weights = list(probs.values())
                        return self.rng.choice(cats, p=weights)
                    return None

                new_vals = frame[source_col].apply(sample_cpt)
                # Only overwrite where CPT gave a value
                mask = new_vals.notna()
                series.loc[mask] = new_vals.loc[mask]

                if col_profile.get("data_type") == "boolean":
                    series = (
                        series.astype(str).str.lower().isin(["true", "1", "t", "yes"])
                    )

            elif dep_type == "conditional_numeric":
                cond_dists = model.get("distributions", {})
                source_col = sources[0]

                def generate_cond(val, original_val):
                    val_str = str(val)
                    if val_str in cond_dists:
                        dist = cond_dists[val_str]
                        mean = dist.get("mean", original_val)
                        std = dist.get("std", 1.0)
                        new_val = self.rng.normal(mean, std)
                        if col_profile.get("data_type") == "integer":
                            return int(round(new_val))
                        return float(new_val)
                    return original_val

                series = pd.Series(
                    [generate_cond(s, t) for s, t in zip(frame[source_col], series)]
                )

            elif dep_type == "numeric_to_categorical":
                bins = model.get("bins", [])
                cpt = model.get("cpt", {})
                source_col = sources[0]

                def generate_num_to_cat(val):
                    if pd.isna(val):
                        return None
                    # Find which bin this value falls into
                    for i in range(len(bins) - 1):
                        if bins[i] <= val <= bins[i + 1]:
                            key = f"{bins[i]},{bins[i+1]}"
                            if key in cpt:
                                probs = cpt[key]
                                cats = list(probs.keys())
                                weights = list(probs.values())
                                return self.rng.choice(cats, p=weights)
                    return None

                new_vals = frame[source_col].apply(generate_num_to_cat)
                mask = new_vals.notna()
                series.loc[mask] = new_vals.loc[mask]

                if col_profile.get("data_type") == "boolean":
                    series = (
                        series.astype(str).str.lower().isin(["true", "1", "t", "yes"])
                    )

            elif dep_type == "linear_regression":
                coeffs = model.get("coefficients", {})
                intercept = model.get("intercept", 0.0)
                residual_std = model.get("residual_std", 0.0)

                y_pred = np.full(len(series), intercept)
                for src in sources:
                    if src in coeffs:
                        y_pred += frame[src] * coeffs[src]

                # Add noise
                y_pred += self.rng.normal(0, residual_std, size=len(series))

                # Scale to target distribution shape using rank mapping (Gaussian copula is better but regression is explicit)
                # To preserve distribution, we can rank-map y_pred to the target's quantiles
                ranks = pd.Series(y_pred).rank(pct=True).values
                series = self._inverse_transform_sample(ranks, col_profile)

        return series

    def _extract_dependencies(
        self,
        rules: List[Dict[str, Any]],
    ) -> tuple[set[str], set[str]]:
        """Return independent and dependent columns from semantic rules."""
        dependent_cols: set[str] = set()
        source_cols: set[str] = set()

        for rule in rules:
            target = str(rule.get("target", "")).strip()
            if target:
                dependent_cols.add(target)

            sources = rule.get("sources", []) or []
            if isinstance(sources, str):
                sources = [sources]
            for src in sources:
                src_name = str(src).strip()
                if src_name:
                    source_cols.add(src_name)

        independent_cols = source_cols - dependent_cols
        return independent_cols, dependent_cols

    def _build_dependency_graph(self, rules: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build a source->targets graph from semantic rules."""
        graph: Dict[str, List[str]] = {}
        for rule in rules:
            target = str(rule.get("target", "")).strip()
            if not target:
                continue
            sources = rule.get("sources", []) or []
            if isinstance(sources, str):
                sources = [sources]

            for src in sources:
                src_name = str(src).strip()
                if not src_name:
                    continue
                graph.setdefault(src_name, []).append(target)
        return graph

    def _topological_sort_semantic_rules(
        self,
        rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Sort rules so sources are resolved before dependent targets."""
        if not rules:
            return []

        targets = {
            str(rule.get("target", "")).strip()
            for rule in rules
            if str(rule.get("target", "")).strip()
        }

        unresolved = list(sort_rules_by_priority(rules))
        sorted_rules: List[Dict[str, Any]] = []
        resolved_targets: set[str] = set()

        while unresolved:
            progress = False
            remaining: List[Dict[str, Any]] = []

            for rule in unresolved:
                sources = rule.get("sources", []) or []
                if isinstance(sources, str):
                    sources = [sources]

                can_run = all(
                    src not in targets or src in resolved_targets for src in sources
                )
                if can_run:
                    sorted_rules.append(rule)
                    target = str(rule.get("target", "")).strip()
                    if target:
                        resolved_targets.add(target)
                    progress = True
                else:
                    remaining.append(rule)

            if not progress:
                # Cycle or invalid graph: keep deterministic ordering fallback.
                sorted_rules.extend(sort_rules_by_priority(remaining))
                break

            unresolved = remaining

        return sorted_rules

    def _apply_semantic_rules(
        self,
        frame: pd.DataFrame,
        semantic_rules: List[Dict[str, Any]],
        all_columns: List[str],
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """Apply semantic rules row-by-row to generate dependent columns."""
        stats = {
            "rules_applied": [],
            "rows_affected": 0,
            "errors": [],
        }
        
        if not semantic_rules:
            return frame, stats
        
        sorted_rules = self._topological_sort_semantic_rules(semantic_rules)
        if not sorted_rules:
            return frame, stats

        targets = [
            str(rule.get("target", "")).strip()
            for rule in sorted_rules
            if str(rule.get("target", "")).strip() in all_columns
        ]
        for target in targets:
            if target not in frame.columns:
                frame[target] = None

        rule_affected_count: Dict[str, int] = {
            str(rule.get("id", "unknown")): 0 for rule in sorted_rules
        }

        for idx in frame.index:
            row_context = frame.loc[idx].to_dict()
            row_context["__rng__"] = self.rng

            for rule in sorted_rules:
                rule_id = str(rule.get("id", "unknown"))
                target = str(rule.get("target", "")).strip()
                sources = rule.get("sources", []) or []
                if isinstance(sources, str):
                    sources = [sources]

                if not target or target not in all_columns:
                    continue

                missing_sources = [src for src in sources if src not in row_context]
                if missing_sources:
                    stats["errors"].append(
                        {
                            "rule_id": rule_id,
                            "row_index": int(idx),
                            "error": f"Missing source columns: {missing_sources}",
                        }
                    )
                    continue

                try:
                    value = SemanticRuleEngine.apply_rule(rule, row_context)
                    if value is None:
                        continue

                    frame.at[idx, target] = value
                    row_context[target] = value
                    rule_affected_count[rule_id] = rule_affected_count.get(rule_id, 0) + 1
                    stats["rows_affected"] += 1
                    print(f"[RULE APPLIED] {target} -> {value}")
                except Exception as e:
                    stats["errors"].append(
                        {
                            "rule_id": rule_id,
                            "row_index": int(idx),
                            "error": str(e),
                        }
                    )

        for rule in sorted_rules:
            rule_id = str(rule.get("id", "unknown"))
            target = str(rule.get("target", "")).strip()
            stats["rules_applied"].append(
                {
                    "rule_id": rule_id,
                    "target": target,
                    "rows_affected": rule_affected_count.get(rule_id, 0),
                    "confidence": rule.get("confidence", 0.5),
                }
            )
        
        return frame, stats
