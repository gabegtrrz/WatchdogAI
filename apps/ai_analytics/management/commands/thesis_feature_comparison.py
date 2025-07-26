"""
Django Management Command: Thesis Feature Set Comparison Experiments

This command runs controlled experiments to compare different feature sets as defined
in the YAML configuration file. It dynamically creates feature combinations and evaluates them.

The experiments compare multiple feature sets:
- Set A (Baseline): Raw features only
- Combinations of Financial, Temporal, Supplier, and Efficiency features
- Final Set: All engineered features combined

Each experiment uses the same training/testing data splits and model parameters
to ensure a fair comparison. Results are saved to the thesis directory.
"""
import os
import joblib
import json
import logging
import yaml
from datetime import datetime
from typing import Union, List, Optional, Dict, Any, Tuple
from django.core.management.base import BaseCommand
from django.conf import settings
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score
import numpy as np
import pandas as pd

from apps.ai_analytics.services import preprocessing, feature_engineering

# Define thesis-specific paths
THESIS_DIR = os.path.join(settings.BASE_DIR, '1 Thesis', 'features', 'research_model')
THESIS_MODEL_DIR = os.path.join(THESIS_DIR, 'models')
THESIS_RESULTS_DIR = os.path.join(THESIS_DIR, 'results')

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Runs controlled experiments to compare different feature sets for thesis research.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            required=True,
            help='Path to YAML configuration file for the thesis experiments'
        )

    def handle(self, *args, **options):
        """Main entry point for the command."""
        logger.info('Starting thesis feature set comparison experiments...')
        self.stdout.write('Starting thesis feature set comparison experiments...')

        try:
            config = self._load_configuration(options['config'])
            if not config:
                return

            self._ensure_thesis_directories()

            training_data, evaluation_data, true_labels = self._load_and_process_data(config)
            if any(data is None for data in [training_data, evaluation_data, true_labels]):
                return

            all_engineered_features = self._precompute_all_features(training_data, evaluation_data)

            experiment_results = self._run_feature_set_experiments(
                training_data, evaluation_data, true_labels, all_engineered_features, config
            )

            self._save_thesis_results(experiment_results, config)
            self._output_experiment_summary(experiment_results)

            logger.info('Thesis feature set comparison experiments complete.')
            self.stdout.write(self.style.SUCCESS('Thesis feature set comparison experiments complete.'))

        except Exception as e:
            logger.error(f'Unexpected error during thesis experiments: {e}', exc_info=True)
            self.stderr.write(f'Unexpected error during thesis experiments: {e}')

    def _load_configuration(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Load and validate configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f'Loaded configuration from {config_path}')
            return config if self._validate_thesis_config(config) else None
        except FileNotFoundError:
            logger.error(f'Configuration file not found: {config_path}')
            self.stderr.write(f'Configuration file not found: {config_path}')
            return None
        except yaml.YAMLError as e:
            logger.error(f'Invalid YAML in configuration file: {e}')
            self.stderr.write(f'Invalid YAML in configuration file: {e}')
            return None
        except Exception as e:
            logger.error(f'Error loading configuration: {e}', exc_info=True)
            self.stderr.write(f'Error loading configuration: {e}')
            return None

    def _validate_thesis_config(self, config: Dict[str, Any]) -> bool:
        """Validate the thesis configuration structure."""
        required_sections = ['data_source', 'model', 'feature_sets', 'experiments']
        if not all(section in config for section in required_sections):
            logger.error(f'Missing one or more required configuration sections: {required_sections}')
            return False
        return True

    def _ensure_thesis_directories(self):
        """Ensure thesis output directories exist."""
        for directory in [THESIS_DIR, THESIS_MODEL_DIR, THESIS_RESULTS_DIR]:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f'Ensured thesis directory exists: {directory}')
            except Exception as e:
                logger.error(f'Failed to create thesis directory {directory}: {e}')
                self.stderr.write(f'Failed to create thesis directory {directory}: {e}')
                raise

    def _load_and_process_data(self, config: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[np.ndarray]]:
        """Load and process training and evaluation data."""
        logger.info('Loading and processing data...')
        self.stdout.write('Loading and processing data...')
        try:
            data_source_config = config.get('data_source', {})
            training_csv_path = data_source_config.get('training_csv_path')
            evaluation_csv_path = data_source_config.get('evaluation_csv_path')

            df_training = preprocessing.get_dataframe(training_csv_path)
            df_evaluation = preprocessing.get_dataframe(evaluation_csv_path)

            if df_training is None or df_evaluation is None:
                self.stderr.write('Failed to load training or evaluation data.')
                return None, None, None

            true_labels = preprocessing.extract_labels(df_evaluation)
            if true_labels is None:
                self.stderr.write('No anomaly labels found in evaluation data.')
                return None, None, None

            cleaned_training = preprocessing.clean_raw_data(df_training)
            cleaned_evaluation = preprocessing.clean_raw_data(df_evaluation)
            
            self.stdout.write('Data loaded and processed successfully.')
            return cleaned_training, cleaned_evaluation, true_labels
        except Exception as e:
            logger.error(f'Error loading and processing data: {e}', exc_info=True)
            self.stderr.write(f'Error loading and processing data: {e}')
            return None, None, None

    def _precompute_all_features(self, training_data: pd.DataFrame, evaluation_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Precompute all possible engineered features to select from."""
        logger.info('Pre-computing all engineered features...')
        self.stdout.write('Pre-computing all engineered features...')
        
        all_training_features, _ = feature_engineering.create_features(training_data.copy())
        all_evaluation_features, _ = feature_engineering.create_features(evaluation_data.copy())

        return {'training': all_training_features, 'evaluation': all_evaluation_features}

    def _run_feature_set_experiments(self, training_data: pd.DataFrame, evaluation_data: pd.DataFrame,
                                   true_labels: np.ndarray, all_engineered_features: Dict[str, pd.DataFrame],
                                   config: Dict[str, Any]) -> Dict[str, Any]:
        """Run experiments for each feature set defined in the configuration."""
        logger.info('Running feature set experiments...')
        self.stdout.write('Running feature set experiments...')

        model_params = self._get_model_parameters(config)
        contamination_range = config.get('model', {}).get('contamination_range', [0.05])
        
        experiment_results = {
            'experiment_date': datetime.now().isoformat(),
            'configuration': config,
            'dataset_info': {
                'training_sample_count': training_data.shape[0],
                'evaluation_sample_count': evaluation_data.shape[0],
                'true_anomalies': np.sum(true_labels),
                'actual_contamination': np.sum(true_labels) / len(true_labels) if len(true_labels) > 0 else 0
            },
            'feature_set_results': {}
        }

        feature_sets_config = config.get('feature_sets', {})
        for name, set_config in feature_sets_config.items():
            if not set_config.get('enabled', False):
                continue
            
            self.stdout.write(f'{"="*20} Testing Feature Set: {name.upper()} {"="*20}')
            
            try:
                training_features, evaluation_features, feature_columns = self._create_features_for_set(
                    name, set_config, training_data, evaluation_data, all_engineered_features, config
                )
                
                if training_features is None:
                    continue

                set_results = self._test_contamination_values(
                    training_features, evaluation_features, true_labels, contamination_range, model_params, name
                )

                best_f1, best_contamination, best_metrics = self._find_best_result(set_results)
                
                experiment_results['feature_set_results'][name] = {
                    'description': set_config.get('description'),
                    'feature_columns': feature_columns,
                    'feature_count': len(feature_columns),
                    'contamination_results': set_results,
                    'best_f1_score': best_f1,
                    'best_contamination': best_contamination,
                    'best_metrics': best_metrics
                }
                self.stdout.write(f'Feature Set {name} - Best F1: {best_f1:.4f} (contamination={best_contamination})')

            except Exception as e:
                logger.error(f'Error testing feature set {name}: {e}', exc_info=True)
                self.stderr.write(f'Error testing feature set {name}: {e}')
        
        experiment_results['best_overall_model'] = self._find_best_overall_model(experiment_results['feature_set_results'])
        return experiment_results

    def _create_features_for_set(self, name: str, set_config: Dict[str, Any],
                                 training_data: pd.DataFrame, evaluation_data: pd.DataFrame,
                                 all_engineered_features: Dict[str, pd.DataFrame],
                                 full_config: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], List[str]]:
        """Create a combined feature set based on configuration."""
        logger.info(f"Creating features for set: {name}")



        # Combine baseline and engineered features based on config
        feature_list_config = set_config.get('features', [])
        
        # Get complete feature list from configuration
        feature_list = feature_list_config if isinstance(feature_list_config, list) else []

        if feature_list:
            # Create features from the complete list
            baseline_features = ['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']
            
            # Separate features into raw data features and engineered features
            raw_data_features = []
            engineered_features = []
            
            for feature in feature_list:
                if feature in baseline_features:
                    # Baseline features are handled separately
                    continue
                elif feature in training_data.columns:
                    # Raw data features (like transaction_date, project_name, etc.)
                    raw_data_features.append(feature)
                elif feature in all_engineered_features['training'].columns:
                    # Engineered features
                    engineered_features.append(feature)
                else:
                    # Missing features
                    logger.warning(f"Feature not found in raw data or engineered features: {feature}")
                    self.stdout.write(f"Warning: Feature not found: {feature}")
            
            # Start with baseline features from raw data
            training_features = training_data[baseline_features].copy()
            evaluation_features = evaluation_data[baseline_features].copy()
            
            # Add raw data features
            if raw_data_features:
                raw_training = training_data[raw_data_features].copy()
                raw_evaluation = evaluation_data[raw_data_features].copy()
                
                # Convert datetime and categorical columns to numerical features
                for col in raw_data_features:
                    if pd.api.types.is_datetime64_any_dtype(raw_training[col]):
                        # Convert datetime to numerical features
                        raw_training[f'{col}_year'] = raw_training[col].dt.year
                        raw_training[f'{col}_month'] = raw_training[col].dt.month
                        raw_training[f'{col}_day'] = raw_training[col].dt.day
                        raw_training[f'{col}_dayofweek'] = raw_training[col].dt.dayofweek
                        
                        raw_evaluation[f'{col}_year'] = raw_evaluation[col].dt.year
                        raw_evaluation[f'{col}_month'] = raw_evaluation[col].dt.month
                        raw_evaluation[f'{col}_day'] = raw_evaluation[col].dt.day
                        raw_evaluation[f'{col}_dayofweek'] = raw_evaluation[col].dt.dayofweek
                        
                        # Drop original datetime column
                        raw_training = raw_training.drop(columns=[col])
                        raw_evaluation = raw_evaluation.drop(columns=[col])
                    
                    elif pd.api.types.is_object_dtype(raw_training[col]) or pd.api.types.is_string_dtype(raw_training[col]):
                        # Convert categorical/string columns to numerical using label encoding
                        from sklearn.preprocessing import LabelEncoder
                        le = LabelEncoder()
                        
                        # Fit on training data and transform both
                        raw_training[f'{col}_encoded'] = le.fit_transform(raw_training[col].astype(str))
                        raw_evaluation[f'{col}_encoded'] = le.transform(raw_evaluation[col].astype(str))
                        
                        # Drop original categorical column
                        raw_training = raw_training.drop(columns=[col])
                        raw_evaluation = raw_evaluation.drop(columns=[col])
                
                training_features = pd.concat([training_features, raw_training], axis=1)
                evaluation_features = pd.concat([evaluation_features, raw_evaluation], axis=1)
            
            # Add engineered features
            if engineered_features:
                engineered_training = all_engineered_features['training'][engineered_features].copy()
                engineered_evaluation = all_engineered_features['evaluation'][engineered_features].copy()
                
                training_features = pd.concat([training_features, engineered_training], axis=1)
                evaluation_features = pd.concat([evaluation_features, engineered_evaluation], axis=1)
        else:
            # For baseline-only case, use raw data
            training_features = training_data[['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']].copy()
            evaluation_features = evaluation_data[['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']].copy()

        # Impute and align columns
        training_features.fillna(0, inplace=True)
        evaluation_features.fillna(0, inplace=True)
        
        feature_columns = training_features.columns.tolist()
        evaluation_features = evaluation_features.reindex(columns=feature_columns, fill_value=0)

        return training_features, evaluation_features, feature_columns



    def _test_contamination_values(self, training_features: pd.DataFrame, evaluation_features: pd.DataFrame,
                                 true_labels: np.ndarray, contamination_range: List[float],
                                 model_params: Dict[str, Any], feature_set_name: str) -> Dict[float, Dict[str, Any]]:
        """Test different contamination values for a given feature set."""
        results = {}

        model = IsolationForest(**{**model_params, 'contamination': 0.05})

        for contamination in contamination_range:
            self.stdout.write(f'-- Testing contamination: {contamination}')
            try:
                # model = IsolationForest(**{**model_params, 'contamination': contamination})
                model.fit(training_features)

                predictions= model.score_samples(evaluation_features)
                threshold = np.percentile(predictions, contamination * 100)
                logger.debug(f'Threshold: {threshold}')

                predictions = (predictions <= threshold).astype(int)


                metrics = self._calculate_metrics(true_labels, predictions)
                
                results[contamination] = {**metrics, 'predicted_anomalies': np.sum(predictions)}
            except Exception as e:
                logger.error(f'Error testing contamination={contamination} for {feature_set_name}: {e}')
                results[contamination] = {'error': str(e), 'f1_score': -1, 'precision': -1, 'recall': -1}
        return results

    def _calculate_metrics(self, true_labels: np.ndarray, predicted_labels: np.ndarray) -> Dict[str, float]:
        """Calculate precision, recall, and F1-score."""
        return {
            'precision': precision_score(true_labels, predicted_labels, zero_division=0),
            'recall': recall_score(true_labels, predicted_labels, zero_division=0),
            'f1_score': f1_score(true_labels, predicted_labels, zero_division=0)
        }

    def _find_best_result(self, results: Dict[float, Dict[str, Any]]) -> Tuple[float, float, Dict[str, Any]]:
        """Find the best performing result from a set of contamination trials."""
        best_f1, best_contamination = -1, -1
        for contamination, metrics in results.items():
            if metrics.get('f1_score', -1) > best_f1:
                best_f1 = metrics['f1_score']
                best_contamination = contamination
        return best_f1, best_contamination, results.get(best_contamination, {})
    
    def _find_best_overall_model(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Find the best performing model across all feature sets."""
        best_overall = {'f1_score': -1}
        for name, results in all_results.items():
            if results.get('best_f1_score', -1) > best_overall['f1_score']:
                best_overall = {
                    'feature_set': name,
                    'f1_score': results['best_f1_score'],
                    'contamination': results['best_contamination']
                }
        return best_overall

    def _get_model_parameters(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get model parameters from configuration, ensuring no 'contamination' key."""
        params = config.get('model', {}).copy()
        params.pop('contamination_range', None)
        params.pop('contamination', None) # Explicitly remove if present
        return {k: v for k, v in params.items() if v is not None}

    def _save_thesis_results(self, experiment_results: Dict[str, Any], config: Dict[str, Any]):
        """Save thesis results to a timestamped JSON file."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'thesis_feature_comparison_results_{timestamp}.json'
            filepath = os.path.join(THESIS_RESULTS_DIR, filename)
            
            serializable_results = self._convert_numpy_types(experiment_results)
            
            with open(filepath, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            
            self.stdout.write(self.style.SUCCESS(f'Thesis results saved to {filepath}'))
        except Exception as e:
            logger.error(f'Error saving thesis results: {e}', exc_info=True)
            self.stderr.write(f'Error saving thesis results: {e}')

    def _convert_numpy_types(self, obj: Any) -> Any:
        """Recursively convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, (np.integer, np.int64)): return int(obj)
        if isinstance(obj, (np.floating, np.float64)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, dict): return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        if isinstance(obj, list): return [self._convert_numpy_types(i) for i in obj]
        return obj

    def _output_experiment_summary(self, results: Dict[str, Any]):
        """Output a summary of the experiment results to the console."""
        self.stdout.write('\n' + '='*80)
        self.stdout.write('THESIS FEATURE SET COMPARISON RESULTS')
        self.stdout.write('='*80)
        
        info = results.get('dataset_info', {})
        self.stdout.write(
            f'\nDataset: {info.get("training_sample_count")} training, '
            f'{info.get("evaluation_sample_count")} evaluation samples. '
            f'Actual Contamination: {info.get("actual_contamination", 0):.2%}'
        )
        
        set_results = results.get('feature_set_results', {})
        if set_results:
            self.stdout.write(f'\n{"Feature Set":<30} {"Features":<10} {"Best F1":<10} {"Precision":<10} {"Recall":<10} {"Best Contamination":<20}')
            self.stdout.write('-'*90)
            
            for name, res in sorted(set_results.items(), key=lambda item: item[1].get('best_f1_score', -1), reverse=True):
                metrics = res.get('best_metrics', {})
                self.stdout.write(
                    f'{name:<30} {res.get("feature_count", 0):<10} '
                    f'{res.get("best_f1_score", -1):<10.4f} '
                    f'{metrics.get("precision", -1):<10.4f} '
                    f'{metrics.get("recall", -1):<10.4f} '
                    f'{res.get("best_contamination", "N/A")}'
                )

        best = results.get('best_overall_model', {})
        if best.get('feature_set'):
            self.stdout.write(f'\nBest Overall Model: {best["feature_set"]} with F1-Score of {best["f1_score"]:.4f} at {best["contamination"]} contamination.')
        self.stdout.write('\n' + '='*80) 