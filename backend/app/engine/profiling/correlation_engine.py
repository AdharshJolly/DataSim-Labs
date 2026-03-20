import pandas as pd
import numpy as np
from typing import Dict, Any, List
from sklearn.linear_model import LinearRegression

class CorrelationEngine:
    def compute_dependencies(self, df: pd.DataFrame, column_profiles: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Compute dependencies between columns to form a dependency graph and matrices."""
        dependencies = []
        correlation_matrices = {}

        numeric_cols = [col for col, prof in column_profiles.items() if prof["data_type"] in ["integer", "float"]]
        categorical_cols = [col for col, prof in column_profiles.items() if prof["data_type"] in ["categorical", "boolean"]]

        # 1. Numeric Correlations (Full Matrix for Gaussian Copula)
        if len(numeric_cols) > 1:
            numeric_df = df[numeric_cols].dropna()
            if len(numeric_df) > 10:
                try:
                    numeric_df = numeric_df.astype(float)
                    pearson_corr = numeric_df.corr(method='pearson').fillna(0).to_dict()
                    spearman_corr = numeric_df.corr(method='spearman').fillna(0).to_dict()

                    correlation_matrices = {
                        "pearson": pearson_corr,
                        "spearman": spearman_corr,
                        "columns": numeric_cols
                    }

                    # We add a generic global dependency for all numerics to be handled by Copula
                    dependencies.append({
                        "type": "multivariate_copula",
                        "sources": numeric_cols,
                        "target": numeric_cols,
                        "model": {}
                    })
                except (ValueError, TypeError):
                    pass

        # 2. Conditional Probability Tables (Categorical to Categorical)
        for target_col in categorical_cols:
            for source_col in categorical_cols:
                if source_col == target_col:
                    continue

                cpt_dep = self._check_categorical_cpt(df, source_col, target_col)
                if cpt_dep:
                    dependencies.append(cpt_dep)

        # 3. Multi-Column Regression Dependencies (Numeric -> Numeric)
        if len(numeric_cols) > 2:
            regression_deps = self._find_regression_dependencies(df, numeric_cols)
            dependencies.extend(regression_deps)

        # 4. Conditional Numeric (Categorical -> Numeric)
        for cat_col in categorical_cols:
            for num_col in numeric_cols:
                cond_dep = self._check_conditional_numeric(df, cat_col, num_col)
                if cond_dep:
                    dependencies.append(cond_dep)

        # 5. Numeric -> Categorical mapping (e.g. Income -> Premium User)
        for num_col in numeric_cols:
            for cat_col in categorical_cols:
                num_to_cat_dep = self._check_numeric_to_categorical(df, num_col, cat_col)
                if num_to_cat_dep:
                    dependencies.append(num_to_cat_dep)

        return {
            "dependencies": dependencies,
            "correlation_matrices": correlation_matrices
        }

    def _check_categorical_cpt(self, df: pd.DataFrame, source: str, target: str) -> Dict[str, Any]:
        """Build Conditional Probability Table (CPT) for target given source."""
        clean_df = df[[source, target]].dropna()
        if len(clean_df) < 20:
            return None

        crosstab = pd.crosstab(clean_df[source], clean_df[target], normalize='index')
        marginal = clean_df[target].value_counts(normalize=True)

        divergence_sum = 0
        valid_groups = 0

        cpt = {}
        for src_val, row in crosstab.iterrows():
            src_val_str = str(src_val)
            probs = {}
            for tgt_val, prob in row.items():
                if prob > 0:
                    probs[str(tgt_val)] = float(prob)
            cpt[src_val_str] = probs

            # Simple KL divergence proxy
            for tgt_val, prob in row.items():
                if prob > 0:
                    marg_prob = marginal.get(tgt_val, 0)
                    if marg_prob > 0:
                        divergence_sum += prob * np.log(prob / marg_prob)
            valid_groups += 1

        if valid_groups == 0:
            return None

        avg_divergence = divergence_sum / valid_groups
        if avg_divergence > 0.1:  # Significant information gain
            return {
                "type": "conditional_probability",
                "sources": [source],
                "target": target,
                "model": {
                    "cpt": cpt
                }
            }
        return None

    def _check_conditional_numeric(self, df: pd.DataFrame, source: str, target: str) -> Dict[str, Any]:
        """Check if numeric target distribution changes based on categorical source."""
        clean_df = df[[source, target]].dropna()
        if len(clean_df) < 20:
            return None

        try:
            clean_df[target] = clean_df[target].astype(float)
        except (ValueError, TypeError):
            return None

        grouped = clean_df.groupby(source)[target]
        conditional_dists = {}

        overall_std = clean_df[target].std()
        if pd.isna(overall_std) or overall_std == 0:
            return None

        significant_diff = False
        overall_mean = clean_df[target].mean()

        for val, group in grouped:
            if len(group) < 5:
                continue
            group_mean = group.mean()
            group_std = group.std()

            if abs(group_mean - overall_mean) > overall_std * 0.4:
                significant_diff = True

            conditional_dists[str(val)] = {
                "mean": float(group_mean),
                "std": float(group_std) if pd.notna(group_std) and len(group) > 1 and group_std > 0 else float(overall_std),
                "min": float(group.min()),
                "max": float(group.max())
            }

        if significant_diff and len(conditional_dists) > 0:
            return {
                "type": "conditional_numeric",
                "sources": [source],
                "target": target,
                "model": {
                    "distributions": conditional_dists
                }
            }

        return None

    def _check_numeric_to_categorical(self, df: pd.DataFrame, source: str, target: str) -> Dict[str, Any]:
        """Check if categorical target depends on numeric source via quantile binning."""
        clean_df = df[[source, target]].dropna()
        if len(clean_df) < 50:
            return None

        try:
            clean_df[source] = clean_df[source].astype(float)
        except (ValueError, TypeError):
            return None

        # Bin numeric source into quintiles
        try:
            clean_df['source_bins'], bins = pd.qcut(clean_df[source], q=5, retbins=True, duplicates='drop')
        except Exception:
            return None

        if len(bins) < 3: # Not enough unique values to split
            return None

        # Build CPT for bins -> categorical
        crosstab = pd.crosstab(clean_df['source_bins'], clean_df[target], normalize='index')
        marginal = clean_df[target].value_counts(normalize=True)

        divergence_sum = 0
        valid_groups = 0

        cpt = {}
        for interval, row in crosstab.iterrows():
            probs = {}
            for tgt_val, prob in row.items():
                if prob > 0:
                    probs[str(tgt_val)] = float(prob)

            # Key format: "left,right"
            key = f"{interval.left},{interval.right}"
            cpt[key] = probs

            for tgt_val, prob in row.items():
                if prob > 0:
                    marg_prob = marginal.get(tgt_val, 0)
                    if marg_prob > 0:
                        divergence_sum += prob * np.log(prob / marg_prob)
            valid_groups += 1

        if valid_groups == 0:
            return None

        avg_divergence = divergence_sum / valid_groups
        if avg_divergence > 0.15:  # Needs stronger signal for numeric->cat
            return {
                "type": "numeric_to_categorical",
                "sources": [source],
                "target": target,
                "model": {
                    "bins": bins.tolist(),
                    "cpt": cpt
                }
            }
        return None

    def _find_regression_dependencies(self, df: pd.DataFrame, numeric_cols: List[str]) -> List[Dict[str, Any]]:
        """Find targets that are strongly predicted by multiple other numeric columns."""
        deps = []
        clean_df = df[numeric_cols].dropna()
        if len(clean_df) < 30:
            return deps

        try:
            clean_df = clean_df.astype(float)
        except Exception:
            return deps

        for target in numeric_cols:
            sources = [c for c in numeric_cols if c != target]
            X = clean_df[sources]
            y = clean_df[target]

            model = LinearRegression()
            model.fit(X, y)
            r2 = model.score(X, y)

            if r2 > 0.6:
                coefficients = dict(zip(sources, model.coef_))
                sig_sources = [s for s, c in coefficients.items() if abs(c) > 0.05 * abs(y.mean())]
                if not sig_sources:
                    sig_sources = sources

                deps.append({
                    "type": "linear_regression",
                    "sources": sig_sources,
                    "target": target,
                    "model": {
                        "coefficients": {s: float(coefficients[s]) for s in sig_sources},
                        "intercept": float(model.intercept_),
                        "residual_std": float(y.std() * np.sqrt(1 - r2)),
                        "r2": float(r2)
                    }
                })

        return deps
