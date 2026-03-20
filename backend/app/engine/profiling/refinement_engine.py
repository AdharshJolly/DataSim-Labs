import copy
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

from app.models.data_profile import DataProfile
from app.engine.enhanced_generator import EnhancedDatasetGenerator
from app.engine.profiling.validator import StatisticalValidator

class RefinementEngine:
    def refine(
        self,
        profile: DataProfile,
        max_iterations: int = 3,
        target_realism_score: int = 85
    ) -> Tuple[DataProfile, Dict[str, Any]]:
        """Run an adaptive feedback loop to retune distributions based on validation errors."""
        validator = StatisticalValidator()
        current_profile = copy.deepcopy(profile)
        final_report = {}
        best_score = -1
        best_profile = current_profile

        for iteration in range(max_iterations):
            # 1. Generate a sample batch (e.g., 2000 rows)
            generator = EnhancedDatasetGenerator(seed=42 + iteration)
            sample_df = generator.generate_from_profile(profile=current_profile, row_count=2000)

            # 2. Run the validator
            report = validator.validate(
                generated_df=sample_df,
                column_profiles=current_profile.columns,
                correlation_target=getattr(current_profile, 'correlation_matrices', None)
            )

            current_score = report.get("realism_score", 0)
            if current_score is not None and current_score > best_score:
                best_score = current_score
                best_profile = copy.deepcopy(current_profile)
                final_report = report

            # 4. Stop early if realism score is high enough or all passed
            if report.get("passed", False) and current_score is not None and current_score >= target_realism_score:
                break

            if iteration == max_iterations - 1:
                break

            # 3. Adjust parameters based on failures
            new_columns = copy.deepcopy(current_profile.columns)
            new_correlation_matrices = copy.deepcopy(getattr(current_profile, 'correlation_matrices', {}))

            # Adjust Numeric Columns failing KS Test
            for col_name, ks_res in report.get("ks_tests", {}).items():
                if not ks_res.get("passed", True):
                    dist = new_columns[col_name].get("distribution", {})
                    if dist:
                        target_mean = dist.get("mean", 0.0)
                        target_std = dist.get("std", 1.0) or 1.0
                        gen_mean = sample_df[col_name].mean()
                        gen_std = sample_df[col_name].std()

                        # Shift mean down/up by 5% of std
                        if gen_mean > target_mean:
                            dist["mean"] = target_mean - (0.05 * target_std)
                        elif gen_mean < target_mean:
                            dist["mean"] = target_mean + (0.05 * target_std)

                        # Shrink/Grow std by 10%
                        if gen_std > target_std * 1.1:
                            dist["std"] = target_std * 0.9
                        elif gen_std < target_std * 0.9:
                            dist["std"] = target_std * 1.1

            # Adjust Categorical Columns failing KL Divergence
            for col_name, kl_res in report.get("kl_divergence", {}).items():
                if not kl_res.get("passed", True):
                    dist = new_columns[col_name].get("distribution", {})
                    if dist and "categories" in dist and "probabilities" in dist:
                        target_probs = dist["probabilities"]
                        categories = dist["categories"]
                        syn_counts = sample_df[col_name].value_counts(normalize=True)

                        new_probs = []
                        for cat, current_prob in zip(categories, target_probs):
                            gen_prob = syn_counts.get(cat, 0.0)
                            weight_adjustment = 0.3 * (current_prob - gen_prob)
                            new_weight = max(current_prob + weight_adjustment, 1e-6)
                            new_probs.append(new_weight)

                        # Re-normalize
                        total_prob = sum(new_probs)
                        dist["probabilities"] = [p / total_prob for p in new_probs]

            # Adjust Correlation Error
            corr_err = report.get("correlation_error", {})
            if corr_err and not corr_err.get("passed", True):
                if new_correlation_matrices and "spearman" in new_correlation_matrices:
                    cols = new_correlation_matrices.get("columns", [])
                    cols = [c for c in cols if c in sample_df.columns]
                    if len(cols) > 1:
                        target_corr = pd.DataFrame(new_correlation_matrices["spearman"]).loc[cols, cols].values
                        gen_corr = sample_df[cols].astype(float).corr(method='spearman').fillna(0).values

                        # Blended correlation: 0.7 * current_corr + 0.3 * target_corr
                        blended_corr = 0.7 * gen_corr + 0.3 * target_corr
                        np.fill_diagonal(blended_corr, 1.0)

                        adjusted_df = pd.DataFrame(blended_corr, index=cols, columns=cols)
                        orig_spearman_df = pd.DataFrame(new_correlation_matrices["spearman"])
                        orig_spearman_df.update(adjusted_df)
                        new_correlation_matrices["spearman"] = orig_spearman_df.to_dict()

            # Update the profile for the next iteration
            current_profile = DataProfile.new(
                dataset_version_id=current_profile.dataset_version_id,
                columns=new_columns,
                dependency_graph=copy.deepcopy(current_profile.dependency_graph),
                correlation_matrices=new_correlation_matrices,
                row_count=current_profile.row_count
            )

        return best_profile, final_report
