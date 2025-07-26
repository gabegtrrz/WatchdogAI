"""
Django Management Command: Thesis Feature Set Comparison Experiments

This command runs controlled experiments to compare different feature sets:
- Set A (Baseline): Raw features only
- Set B: Baseline + Financial Features  
- Set C: Baseline + Temporal Features
- Set D (Final): All engineered features combined

Each experiment uses the same training/testing data splits and model parameters
to ensure fair comparison. Results are saved to the thesis directory.
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
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
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
            help='Path to YAML configuration file'
        )

    def handle(self, *args, **options):
        """Main entry point for the command."""
        logger.info('Starting thesis feature set comparison experiments...')
        self.stdout.write('Starting thesis feature set comparison experiments...')

        try:
            # Load and validate configuration
            config = self._load_configuration(options['config'])
            if not config:
                return

            # Ensure thesis directories exist
            self._ensure_thesis_directories()

            # Load and process data
            training_data, evaluation_data, true_labels = self._load_and_process_data(config)
            if training_data is None or evaluation_data is None or true_labels is None:
                return

            # Run experiments for each feature set
            experiment_results = self._run_feature_set_experiments(
                training_data, evaluation_data, true_labels, config
            )

            # Save comprehensive results
            self._save_thesis_results(experiment_results, config)

            # Output summary
            self._output_experiment_summary(experiment_results)

            logger.info('Thesis feature set comparison experiments complete.')
            self.stdout.write('Thesis feature set comparison experiments complete.')

        except Exception as e:
            logger.error(f'Unexpected error during thesis experiments: {e}', exc_info=True)
            self.stderr.write(f'Unexpected error during thesis experiments: {e}')

    def _load_configuration(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Load and validate configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f'Loaded configuration from {config_path}')
            
            if not self._validate_thesis_config(config):
                return None
                
            return config
            
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
        
        for section in required_sections:
            if section not in config:
                logger.error(f'Missing required configuration section: {section}')
                self.stderr.write(f'Missing required configuration section: {section}')
                return False
        
        # Validate data source configuration
        data_source = config.get('data_source', {})
        if not data_source.get('training_csv_path') or not data_source.get('evaluation_csv_path'):
            logger.error('Both training_csv_path and evaluation_csv_path must be specified in data_source')
            self.stderr.write('Both training_csv_path and evaluation_csv_path must be specified in data_source')
            return False
        
        # Validate feature sets configuration
        feature_sets = config.get('feature_sets', {})
        required_feature_sets = ['baseline', 'financial', 'temporal', 'final']
        for feature_set in required_feature_sets:
            if feature_set not in feature_sets:
                logger.error(f'Missing required feature set: {feature_set}')
                self.stderr.write(f'Missing required feature set: {feature_set}')
                return False
        
        return True

    def _ensure_thesis_directories(self):
        """Ensure thesis directories exist."""
        directories = [THESIS_DIR, THESIS_MODEL_DIR, THESIS_RESULTS_DIR]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f'Ensured thesis directory exists: {directory}')
            except Exception as e:
                error_msg = f'Failed to create thesis directory {directory}: {e}'
                logger.error(error_msg)
                self.stderr.write(error_msg)
                raise

    def _load_and_process_data(self, config: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[np.ndarray]]:
        """Load and process training and evaluation data."""
        logger.info('Loading and processing data...')
        self.stdout.write('Loading and processing data...')
        
        try:
            # Load training data
            training_csv_path = config.get('data_source', {}).get('training_csv_path')
            df_training = preprocessing.get_dataframe(training_csv_path)
            
            if df_training is None or df_training.empty:
                logger.error('No training data found')
                self.stderr.write('No training data found')
                return None, None, None
            
            # Load evaluation data
            evaluation_csv_path = config.get('data_source', {}).get('evaluation_csv_path')
            df_evaluation = preprocessing.get_dataframe(evaluation_csv_path)
            
            if df_evaluation is None or df_evaluation.empty:
                logger.error('No evaluation data found')
                self.stderr.write('No evaluation data found')
                return None, None, None
            
            # Extract labels from evaluation data
            true_labels = preprocessing.extract_labels(df_evaluation)
            if true_labels is None:
                logger.error('No anomaly labels found in evaluation data')
                self.stderr.write('No anomaly labels found in evaluation data')
                return None, None, None
            
            # Clean data
            cleaned_training = preprocessing.clean_raw_data(df_training)
            cleaned_evaluation = preprocessing.clean_raw_data(df_evaluation)
            
            logger.info(f'Data loaded successfully:')
            logger.info(f'  Training data shape: {cleaned_training.shape}')
            logger.info(f'  Evaluation data shape: {cleaned_evaluation.shape}')
            logger.info(f'  True labels distribution: {np.bincount(true_labels)}')
            
            return cleaned_training, cleaned_evaluation, true_labels
            
        except Exception as e:
            logger.error(f'Error loading and processing data: {e}', exc_info=True)
            self.stderr.write(f'Error loading and processing data: {e}')
            return None, None, None

    def _run_feature_set_experiments(self, training_data: pd.DataFrame, evaluation_data: pd.DataFrame, 
                                   true_labels: np.ndarray, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run experiments for each feature set."""
        logger.info('Running feature set experiments...')
        self.stdout.write('Running feature set experiments...')
        
        # Get model parameters
        model_params = self._get_model_parameters(config)
        contamination_range = config.get('model', {}).get('contamination_range', [0.05])
        
        # Initialize results
        experiment_results = {
            'experiment_date': datetime.now().isoformat(),
            'configuration': config,
            'dataset_info': {
                'training_sample_count': training_data.shape[0],
                'evaluation_sample_count': evaluation_data.shape[0],
                'true_anomalies': np.sum(true_labels),
                'true_normal': len(true_labels) - np.sum(true_labels),
                'actual_contamination': np.sum(true_labels) / len(true_labels) if len(true_labels) > 0 else 0
            },
            'feature_set_results': {},
            'best_overall_model': None,
            'recommendations': []
        }
        
        best_overall_f1 = -1
        best_overall_feature_set = None
        
        # Define feature sets
        feature_sets = {
            'baseline': self._create_baseline_features,
            'financial': self._create_financial_features,
            'temporal': self._create_temporal_features,
            'final': self._create_final_features
        }
        
        # Run experiments for each feature set
        for feature_set_name, feature_creator in feature_sets.items():
            logger.info(f'{"="*20} Testing Feature Set: {feature_set_name.upper()} {"="*20}')
            self.stdout.write(f'{"="*20} Testing Feature Set: {feature_set_name.upper()} {"="*20}')
            
            try:
                # Create features for this set
                training_features, evaluation_features, feature_columns = feature_creator(
                    training_data, evaluation_data
                )
                
                if training_features is None or evaluation_features is None:
                    logger.error(f'Failed to create features for {feature_set_name}')
                    continue
                
                # Test contamination values
                feature_set_results = self._test_contamination_values(
                    training_features, evaluation_features, true_labels, 
                    feature_columns, contamination_range, model_params, feature_set_name
                )
                
                experiment_results['feature_set_results'][feature_set_name] = {
                    'feature_columns': feature_columns,
                    'feature_count': len(feature_columns),
                    'contamination_results': feature_set_results,
                    'best_contamination': None,
                    'best_f1_score': -1,
                    'best_metrics': None
                }
                
                # Find best contamination for this feature set
                best_f1 = -1
                best_contamination = None
                best_metrics = None
                
                for contamination, results in feature_set_results.items():
                    if results['f1_score'] > best_f1:
                        best_f1 = results['f1_score']
                        best_contamination = contamination
                        best_metrics = results
                
                # Update feature set results
                experiment_results['feature_set_results'][feature_set_name].update({
                    'best_contamination': best_contamination,
                    'best_f1_score': best_f1,
                    'best_metrics': best_metrics
                })
                
                # Track overall best
                if best_f1 > best_overall_f1:
                    best_overall_f1 = best_f1
                    best_overall_feature_set = feature_set_name
                
                logger.info(f'Feature Set {feature_set_name} - Best F1: {best_f1:.4f} (contamination={best_contamination})')
                self.stdout.write(f'Feature Set {feature_set_name} - Best F1: {best_f1:.4f} (contamination={best_contamination})')
                
            except Exception as e:
                logger.error(f'Error testing feature set {feature_set_name}: {e}', exc_info=True)
                self.stderr.write(f'Error testing feature set {feature_set_name}: {e}')
        
        # Set best overall model
        if best_overall_feature_set:
            experiment_results['best_overall_model'] = {
                'feature_set': best_overall_feature_set,
                'f1_score': best_overall_f1,
                'contamination': experiment_results['feature_set_results'][best_overall_feature_set]['best_contamination']
            }
        
        return experiment_results

    def _create_baseline_features(self, training_data: pd.DataFrame, evaluation_data: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], List[str]]:
        """Create baseline features (raw numerical features only)."""
        logger.info('Creating baseline features...')
        
        try:
            # Select only raw numerical features
            baseline_columns = ['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']
            
            # Filter columns that exist in the data
            available_columns = [col for col in baseline_columns if col in training_data.columns]
            
            if not available_columns:
                logger.error('No baseline columns found in training data')
                return None, None, []
            
            # Create features
            training_features = training_data[available_columns].copy()
            evaluation_features = evaluation_data[available_columns].copy()
            
            # Handle missing values
            training_features = training_features.fillna(0)
            evaluation_features = evaluation_features.fillna(0)
            
            logger.info(f'Baseline features created: {available_columns}')
            return training_features, evaluation_features, available_columns
            
        except Exception as e:
            logger.error(f'Error creating baseline features: {e}', exc_info=True)
            return None, None, []

    def _create_financial_features(self, training_data: pd.DataFrame, evaluation_data: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], List[str]]:
        """Create baseline + financial features."""
        logger.info('Creating financial features...')
        
        try:
            # Start with baseline features
            training_baseline, evaluation_baseline, baseline_columns = self._create_baseline_features(training_data, evaluation_data)
            
            if training_baseline is None:
                return None, None, []
            
            # Add financial engineered features
            financial_features = ['budget_utilization_ratio', 'price_variance_ratio', 'unit_price_ratio']
            
            # Create financial features for training data
            training_financial = self._create_financial_engineered_features(training_data)
            evaluation_financial = self._create_financial_engineered_features(evaluation_data)
            
            # Combine baseline and financial features
            training_combined = pd.concat([training_baseline, training_financial], axis=1)
            evaluation_combined = pd.concat([evaluation_baseline, evaluation_financial], axis=1)
            
            # Handle missing values
            training_combined = training_combined.fillna(0)
            evaluation_combined = evaluation_combined.fillna(0)
            
            all_columns = baseline_columns + financial_features
            
            logger.info(f'Financial features created: {all_columns}')
            return training_combined, evaluation_combined, all_columns
            
        except Exception as e:
            logger.error(f'Error creating financial features: {e}', exc_info=True)
            return None, None, []

    def _create_temporal_features(self, training_data: pd.DataFrame, evaluation_data: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], List[str]]:
        """Create baseline + temporal features."""
        logger.info('Creating temporal features...')
        
        try:
            # Start with baseline features
            training_baseline, evaluation_baseline, baseline_columns = self._create_baseline_features(training_data, evaluation_data)
            
            if training_baseline is None:
                return None, None, []
            
            # Add temporal engineered features
            temporal_features = ['bidding_period_number_of_days', 'award_to_contract_days', 'posting_to_award_days']
            
            # Create temporal features for training data
            training_temporal = self._create_temporal_engineered_features(training_data)
            evaluation_temporal = self._create_temporal_engineered_features(evaluation_data)
            
            # Combine baseline and temporal features
            training_combined = pd.concat([training_baseline, training_temporal], axis=1)
            evaluation_combined = pd.concat([evaluation_baseline, evaluation_temporal], axis=1)
            
            # Handle missing values
            training_combined = training_combined.fillna(0)
            evaluation_combined = evaluation_combined.fillna(0)
            
            all_columns = baseline_columns + temporal_features
            
            logger.info(f'Temporal features created: {all_columns}')
            return training_combined, evaluation_combined, all_columns
            
        except Exception as e:
            logger.error(f'Error creating temporal features: {e}', exc_info=True)
            return None, None, []

    def _create_final_features(self, training_data: pd.DataFrame, evaluation_data: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], List[str]]:
        """Create final feature set using the existing feature engineering service."""
        logger.info('Creating final features using existing feature engineering...')
        
        try:
            # Use the existing feature engineering service
            training_features, training_columns = feature_engineering.create_features(training_data.copy())
            evaluation_features, _ = feature_engineering.create_features(evaluation_data.copy())
            
            # Ensure evaluation features have the same columns as training
            missing_columns = set(training_columns) - set(evaluation_features.columns)
            for col in missing_columns:
                evaluation_features[col] = 0
            
            # Select only the columns used in training
            evaluation_features = evaluation_features[training_columns]
            
            # Handle missing values
            training_features = training_features.fillna(0)
            evaluation_features = evaluation_features.fillna(0)
            
            logger.info(f'Final features created: {len(training_columns)} features')
            return training_features, evaluation_features, training_columns
            
        except Exception as e:
            logger.error(f'Error creating final features: {e}', exc_info=True)
            return None, None, []

    def _create_financial_engineered_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create financial engineered features."""
        features = pd.DataFrame(index=df.index)
        
        # Budget utilization ratio
        if 'total_purchase_price' in df.columns and 'approved_budget' in df.columns:
            features['budget_utilization_ratio'] = df['total_purchase_price'] / df['approved_budget'].replace(0, 1)
        
        # Price variance ratio
        if 'unit_purchase_price' in df.columns and 'average_price' in df.columns:
            features['price_variance_ratio'] = (df['unit_purchase_price'] - df['average_price']) / df['average_price'].replace(0, 1)
        
        # Unit price ratio
        if 'unit_purchase_price' in df.columns and 'average_price' in df.columns:
            features['unit_price_ratio'] = df['unit_purchase_price'] / df['average_price'].replace(0, 1)
        
        return features

    def _create_temporal_engineered_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create temporal engineered features."""
        features = pd.DataFrame(index=df.index)
        
        # Bidding period
        if 'invitation_to_bid_posting_date' in df.columns and 'bid_submission_deadline' in df.columns:
            features['bidding_period_number_of_days'] = (
                pd.to_datetime(df['bid_submission_deadline']) - 
                pd.to_datetime(df['invitation_to_bid_posting_date'])
            ).dt.days
        
        # Award to contract days
        if 'notice_of_award_date' in df.columns and 'contract_signing_date' in df.columns:
            features['award_to_contract_days'] = (
                pd.to_datetime(df['contract_signing_date']) - 
                pd.to_datetime(df['notice_of_award_date'])
            ).dt.days
        
        # Posting to award days
        if 'invitation_to_bid_posting_date' in df.columns and 'notice_of_award_date' in df.columns:
            features['posting_to_award_days'] = (
                pd.to_datetime(df['notice_of_award_date']) - 
                pd.to_datetime(df['invitation_to_bid_posting_date'])
            ).dt.days
        
        return features

    def _test_contamination_values(self, training_features: pd.DataFrame, evaluation_features: pd.DataFrame,
                                 true_labels: np.ndarray, feature_columns: List[str], 
                                 contamination_range: List[float], model_params: Dict[str, Any],
                                 feature_set_name: str) -> Dict[float, Dict[str, Any]]:
        """Test different contamination values for a feature set."""
        results = {}
        
        for contamination in contamination_range:
            logger.info(f'Testing {feature_set_name} with contamination={contamination}...')
            
            try:
                # Update contamination in model parameters
                test_params = model_params.copy()
                test_params['contamination'] = contamination
                
                # Train model
                model = IsolationForest(**test_params)
                model.fit(training_features)
                
                # Get predictions
                anomaly_scores = model.score_samples(evaluation_features)
                threshold = np.percentile(anomaly_scores, contamination * 100)
                predicted_labels = (anomaly_scores <= threshold).astype(int)
                
                # Calculate metrics
                metrics = self._calculate_metrics(true_labels, predicted_labels)
                
                results[contamination] = {
                    'contamination': contamination,
                    'threshold': threshold,
                    'predicted_anomalies': np.sum(predicted_labels),
                    'predicted_normal': len(predicted_labels) - np.sum(predicted_labels),
                    **metrics
                }
                
            except Exception as e:
                logger.error(f'Error testing contamination={contamination} for {feature_set_name}: {e}')
                results[contamination] = {
                    'contamination': contamination,
                    'error': str(e),
                    'f1_score': -1,
                    'precision': -1,
                    'recall': -1
                }
        
        return results

    def _calculate_metrics(self, true_labels: np.ndarray, predicted_labels: np.ndarray) -> Dict[str, float]:
        """Calculate evaluation metrics."""
        if np.sum(predicted_labels) == 0:
            precision = recall = f1 = 0.0
        else:
            precision = precision_score(true_labels, predicted_labels, zero_division=0)
            recall = recall_score(true_labels, predicted_labels, zero_division=0)
            f1 = f1_score(true_labels, predicted_labels, zero_division=0)
        
        return {
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1)
        }

    def _get_model_parameters(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get model parameters from configuration."""
        model_config = config.get('model', {})
        
        params = {
            'random_state': model_config.get('random_state', 42),
            'n_estimators': model_config.get('n_estimators', 100),
            'max_samples': model_config.get('max_samples', 'auto'),
            'bootstrap': model_config.get('bootstrap', False),
            'n_jobs': model_config.get('n_jobs', None),
            'verbose': model_config.get('verbose', 0),
            'warm_start': model_config.get('warm_start', False),
            'max_features': model_config.get('max_features', 1.0)
        }
        
        # Remove None values to use sklearn defaults
        params = {k: v for k, v in params.items() if v is not None}
        
        return params

    def _save_thesis_results(self, experiment_results: Dict[str, Any], config: Dict[str, Any]):
        """Save thesis results to JSON file."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_filename = f'thesis_feature_comparison_results_{timestamp}.json'
            results_path = os.path.join(THESIS_RESULTS_DIR, results_filename)
            
            # Convert numpy types for JSON serialization
            serializable_results = self._convert_numpy_types(experiment_results)
            
            with open(results_path, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            
            logger.info(f'Thesis results saved to {results_path}')
            self.stdout.write(f'Thesis results saved to {results_path}')
            
        except Exception as e:
            logger.error(f'Error saving thesis results: {e}', exc_info=True)
            self.stderr.write(f'Error saving thesis results: {e}')

    def _convert_numpy_types(self, obj: Any) -> Any:
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        else:
            return obj

    def _output_experiment_summary(self, experiment_results: Dict[str, Any]):
        """Output experiment summary to console."""
        if not experiment_results:
            return
        
        self.stdout.write('\n' + '='*80)
        self.stdout.write('THESIS FEATURE SET COMPARISON RESULTS')
        self.stdout.write('='*80)
        
        # Dataset information
        dataset_info = experiment_results.get('dataset_info', {})
        self.stdout.write(f'\nDataset Information:')
        self.stdout.write(f'  - Training samples: {dataset_info.get("training_sample_count", "N/A")}')
        self.stdout.write(f'  - Evaluation samples: {dataset_info.get("evaluation_sample_count", "N/A")}')
        self.stdout.write(f'  - True anomalies: {dataset_info.get("true_anomalies", "N/A")}')
        self.stdout.write(f'  - True normal: {dataset_info.get("true_normal", "N/A")}')
        self.stdout.write(f'  - Actual contamination: {dataset_info.get("actual_contamination", "N/A"):.4f}')
        
        # Feature set comparison
        feature_set_results = experiment_results.get('feature_set_results', {})
        if feature_set_results:
            self.stdout.write(f'\nFeature Set Comparison:')
            self.stdout.write(f'{"Feature Set":<15} {"Features":<10} {"Best F1":<10} {"Best Contamination":<20}')
            self.stdout.write(f'{"-"*15} {"-"*10} {"-"*10} {"-"*20}')
            
            for feature_set, results in feature_set_results.items():
                feature_count = results.get('feature_count', 0)
                best_f1 = results.get('best_f1_score', -1)
                best_contamination = results.get('best_contamination', 'N/A')
                
                self.stdout.write(f'{feature_set:<15} {feature_count:<10} {best_f1:<10.4f} {best_contamination:<20}')
        
        # Best overall model
        best_overall = experiment_results.get('best_overall_model', {})
        if best_overall:
            self.stdout.write(f'\nBest Overall Model:')
            self.stdout.write(f'  - Feature Set: {best_overall.get("feature_set", "N/A")}')
            self.stdout.write(f'  - F1-Score: {best_overall.get("f1_score", "N/A"):.4f}')
            self.stdout.write(f'  - Contamination: {best_overall.get("contamination", "N/A")}')
        
        self.stdout.write('\n' + '='*80) 