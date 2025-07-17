"""
Management command to evaluate the Isolation Forest model metrics on test data.
"""
import os
import joblib
import json
import logging
import yaml
from datetime import datetime
from typing import Union, List, Optional, Dict, Any
from django.core.management.base import BaseCommand
from django.conf import settings
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, classification_report
import numpy as np
import pandas as pd

from apps.ai_analytics.services import preprocessing, feature_engineering

# Define default paths for the trained model
DEFAULT_MODEL_DIR = os.path.join(settings.BASE_DIR, 'apps', 'ai_analytics', 'model_files')
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, 'isolation_forest.joblib')
DEFAULT_COLUMNS_PATH = os.path.join(DEFAULT_MODEL_DIR, 'training_columns.joblib')

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Evaluates the trained Isolation Forest model metrics on test data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            required=True,
            help='Path to YAML configuration file'
        )

    def handle(self, *args, **options):
        """Main entry point for the command."""
        logger.info('Starting model evaluation...')
        self.stdout.write('Starting model evaluation...')

        try:
            # Load and validate configuration
            config = self._load_configuration(options['config'])
            if not config:
                return

            # Load model and training data
            model, training_columns = self._load_model_and_columns(config)
            if not model or training_columns is None:
                return

            # Process evaluation data
            df_processed, true_labels = self._process_evaluation_data(config)
            if df_processed is None or true_labels is None:
                return

            # Perform evaluation
            evaluation_results = self._evaluate_model(
                model, df_processed, training_columns, config, 
                options['config'], true_labels
            )
            if not evaluation_results:
                return

            # Output results
            self._output_results(evaluation_results, config)

            logger.info('Model evaluation complete.')
            self.stdout.write('Model evaluation complete.')

        except Exception as e:
            logger.error(f'Unexpected error during evaluation: {e}', exc_info=True)
            self.stderr.write(f'Unexpected error during evaluation: {e}')

    def _load_configuration(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Load and validate configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f'Loaded configuration from {config_path}')
            
            if not self._validate_config(config):
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

    def _load_model_and_columns(self, config: Dict[str, Any]) -> tuple[Optional[Any], Optional[List[str]]]:
        """Load trained model and training columns."""
        # Get model paths from config or use defaults
        model_config = config.get('model', {})
        
        model_path = self._resolve_path(model_config.get('model_path', DEFAULT_MODEL_PATH))
        columns_path = self._resolve_path(model_config.get('columns_path', DEFAULT_COLUMNS_PATH))
        
        # Check if files exist
        if not self._check_file_exists(model_path, 'trained model'):
            return None, None
        if not self._check_file_exists(columns_path, 'training columns'):
            return None, None

        # Load model and columns
        try:
            model = joblib.load(model_path)
            training_columns = joblib.load(columns_path)
            logger.info('Successfully loaded trained model and training columns')
            return model, training_columns
                    
        except Exception as e:
            logger.error(f'Error loading trained model: {e}', exc_info=True)
            self.stderr.write(f'Error loading trained model: {e}')
            return None, None

    def _process_evaluation_data(self, config: Dict[str, Any]) -> tuple[Optional[pd.DataFrame], Optional[np.ndarray]]:
        """Process evaluation data and extract labels."""
        logger.info('Fetching and preprocessing evaluation data...')
        self.stdout.write('Fetching and preprocessing evaluation data...')
        
        try:
            # Get raw data
            df = self._get_raw_data(config)
            if df is None or df.empty:
                logger.warning('No transaction data found for evaluation.')
                self.stdout.write('No transaction data found for evaluation.')
                return None, None

            # Extract labels before processing
            true_labels = self._extract_labels(df)
            if true_labels is None:
                return None, None

            # Clean and process data
            df_processed = self._clean_and_process_data(df)
            if df_processed is None:
                return None, None

            return df_processed, true_labels

        except Exception as e:
            logger.error(f'Error during data processing: {e}', exc_info=True)
            self.stderr.write(f'Error during data processing: {e}')
            return None, None

    def _get_raw_data(self, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Get raw data from CSV or database."""
        csv_source = config.get('data_source', {}).get('csv_path')
        
        if csv_source:
            logger.info(f'Using CSV source: {csv_source}')
            self.stdout.write(f'Using CSV source: {csv_source}')
            return preprocessing.get_dataframe(csv_source)
        else:
            logger.info('Using database as data source')
            self.stdout.write('Using database as data source')
            return preprocessing.get_dataframe()

    def _extract_labels(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        """Extract labels from raw data."""
        logger.info('Extracting labels from raw data...')
        try:
            true_labels = preprocessing.extract_labels(df)
            if true_labels is not None:
                logger.info(f'Labels extracted successfully. Distribution: {np.bincount(true_labels)}')
                self.stdout.write(f'Labels extracted successfully. Distribution: {np.bincount(true_labels)}')
                return true_labels
            else:
                logger.warning('No anomaly labels found in raw data. Cannot perform supervised evaluation.')
                self.stdout.write('No anomaly labels found in raw data. Cannot perform supervised evaluation.')
                return None
        except Exception as e:
            logger.error(f'Error extracting labels: {e}', exc_info=True)
            self.stderr.write(f'Error extracting labels: {e}')
            return None

    def _clean_and_process_data(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Clean and process the raw data."""
        try:
            logger.info('Cleaning raw data...')
            cleaned_df = preprocessing.clean_raw_data(df)
            logger.info(f'Cleaned data shape: {cleaned_df.shape}')

            logger.info('Starting feature engineering...')
            df_processed, _ = feature_engineering.create_model_features(cleaned_df)
            logger.info(f'Feature engineering completed. Processed data shape: {df_processed.shape}')
            
            return df_processed

        except Exception as e:
            logger.error(f'Error during data preprocessing: {e}', exc_info=True)
            self.stderr.write(f'Error during data preprocessing: {e}')
            return None

    def _evaluate_model(self, model, df_processed: pd.DataFrame, training_columns: List[str], 
                       config: Dict[str, Any], model_path: str, true_labels: np.ndarray) -> Optional[Dict[str, Any]]:
        """Evaluate the trained model on labeled data."""
        logger.info('Evaluating trained model...')
        self.stdout.write('Evaluating trained model...')
        
        try:
            # Prepare features for prediction
            features_df = self._prepare_features(df_processed, training_columns, config)
            if features_df is None:
                return None

            # Get predictions
            predicted_labels = self._get_predictions(model, features_df, config)
            if predicted_labels is None:
                return None

            # Calculate metrics
            evaluation_results = self._calculate_metrics(true_labels, predicted_labels, config)
            
            # Add metadata
            evaluation_results = self._add_metadata(evaluation_results, df_processed, training_columns, 
                                                 true_labels, model, model_path, config)
            
            return evaluation_results

        except Exception as e:
            logger.error(f'Error during model evaluation: {e}', exc_info=True)
            self.stderr.write(f'Error during model evaluation: {e}')
            return None

    def _prepare_features(self, df_processed: pd.DataFrame, training_columns: List[str], 
                         config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Prepare features for model prediction."""
        features_df = df_processed.copy()
        
        # Get advanced configuration
        advanced_config = config.get('advanced', {})
        handle_missing_columns = advanced_config.get('handle_missing_columns', True)
        missing_column_default = advanced_config.get('missing_column_default', 0)
        remove_extra_columns = advanced_config.get('remove_extra_columns', True)
        
        # Debug column information
        logger.info(f'Columns after dropping is_anomaly: {list(features_df.columns)}')
        logger.info(f'Training columns: {list(training_columns)}')
        
        # Handle column mismatches
        missing_columns = set(training_columns) - set(features_df.columns)
        extra_columns = set(features_df.columns) - set(training_columns)
        
        logger.info(f'Missing columns: {missing_columns}')
        logger.info(f'Extra columns: {extra_columns}')
        
        # Add missing columns
        if missing_columns and handle_missing_columns:
            logger.warning(f'Missing columns in evaluation data: {missing_columns}')
            for col in missing_columns:
                features_df[col] = missing_column_default
        
        # Remove extra columns
        if extra_columns and remove_extra_columns:
            logger.warning(f'Extra columns in evaluation data: {extra_columns}')
            features_df = features_df[training_columns]
        
        # Safety check: Ensure is_anomaly is not in features
        if 'is_anomaly' in features_df.columns:
            logger.error('is_anomaly column still present in features! Removing it...')
            features_df = features_df.drop('is_anomaly', axis=1)
        
        logger.info(f'Features shape for prediction: {features_df.shape}')
        logger.info(f'Final feature columns: {list(features_df.columns)}')
        
        return features_df

    def _get_predictions(self, model, features_df: pd.DataFrame, config: Dict[str, Any]) -> Optional[np.ndarray]:
        """Get predictions from the trained model."""

        logger.info('Getting predictions from trained model...')

        # Get raw anomaly scores (lower score means more anomalous)
        anomaly_scores = model.score_samples(features_df)

        # Determine contamination rate for thresholding
        contamination_rate = self._get_contamination_rate(model, config)
        
        # Calculate threshold based on contamination rate
        threshold = np.percentile(anomaly_scores, contamination_rate * 100)

        # Classify samples as anomalies (1) or normal (0)
        predicted_labels = (anomaly_scores <= threshold).astype(int)

        logger.info(f'Predicted anomalies: {np.sum(predicted_labels)} out of {len(predicted_labels)} '
                   f'using contamination rate of {contamination_rate:.4f} and threshold of {threshold:.4f}')

        return predicted_labels

    def _get_contamination_rate(self, model, config: Dict[str, Any]) -> Union[float, str]:
        """Get the contamination rate from the config, falling back to the model's default."""
        
        contamination_from_config = config.get('model', {}).get('contamination', None)

        # Check if the config value exists before trying to parse it.
        if contamination_from_config is not None:
            try:
                if str(contamination_from_config).lower() == 'auto':
                    logger.info("Using 'auto' contamination rate from config.")
                    return 'auto'
                
                rate = float(contamination_from_config)
                logger.info(f"Using contamination rate from config: {rate}")
                return rate

            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid contamination value '{contamination_from_config}' in config. "
                    f"Falling back to the model's default."
                )
                # Fall through to return the model's default below

        # fallback logic
        default_rate = getattr(model, 'contamination', 0.05) # Safely get model's rate
        logger.info(f"Using model's default contamination rate: {default_rate}")

        return default_rate

    def _calculate_metrics(self, true_labels: np.ndarray, predicted_labels: np.ndarray, 
                          config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive evaluation metrics."""
        logger.info('Calculating evaluation metrics...')
        
        evaluation_config = config.get('evaluation', {})
        metrics_to_calculate = evaluation_config.get('metrics', [
            'precision', 'recall', 'f1_score', 'accuracy', 
            'specificity', 'balanced_accuracy', 'confusion_matrix'
        ])
        
        # Handle case where no anomalies are predicted
        if np.sum(predicted_labels) == 0:
            logger.warning('No anomalies predicted by the model')
            precision = recall = f1 = 0.0
        else:
            precision = precision_score(true_labels, predicted_labels, zero_division='warn')
            recall = recall_score(true_labels, predicted_labels, zero_division='warn')
            f1 = f1_score(true_labels, predicted_labels, zero_division='warn')
        
        # Calculate confusion matrix and derived metrics
        cm = confusion_matrix(true_labels, predicted_labels)
        tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
        
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
        balanced_accuracy = (recall + specificity) / 2
        
        # Build metrics dictionary
        metrics = {}
        metric_values = {
            'precision': precision, 'recall': recall, 'f1_score': f1,
            'accuracy': accuracy, 'specificity': specificity, 'balanced_accuracy': balanced_accuracy
        }
        
        for metric in metrics_to_calculate:
            if metric in metric_values:
                metrics[metric] = float(metric_values[metric])
            elif metric == 'confusion_matrix':
                metrics[metric] = cm.tolist()
        
        # Add prediction counts
        metrics.update({
            'predicted_anomalies': int(np.sum(predicted_labels)),
            'predicted_normal': int(len(predicted_labels) - np.sum(predicted_labels)),
            'true_anomalies': int(np.sum(true_labels)),
            'true_normal': int(len(true_labels) - np.sum(true_labels)),
            'true_positives': int(tp), 'false_positives': int(fp),
            'false_negatives': int(fn), 'true_negatives': int(tn)
        })
        
        # Log key metrics
        self._log_metrics(metrics)
        
        return metrics

    def _log_metrics(self, metrics: Dict[str, Any]):
        """Log calculated metrics."""
        logger.info('Evaluation metrics calculated:')
        for metric in ['precision', 'recall', 'f1_score', 'accuracy', 'specificity', 'balanced_accuracy']:
            if metric in metrics:
                logger.info(f'  - {metric.title()}: {metrics[metric]:.4f}')

    def _add_metadata(self, evaluation_results: Dict[str, Any], df_processed: pd.DataFrame, 
                     training_columns: List[str], true_labels: np.ndarray, model, 
                     model_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Add dataset and model metadata to evaluation results."""
        # Dataset information
        evaluation_results['dataset_info'] = {
            'sample_count': df_processed.shape[0],
            'feature_count': df_processed.shape[1],
            'feature_columns': list(training_columns),
            'labeled_data_count': len(true_labels),
            'true_anomalies': np.sum(true_labels),
            'true_normal': len(true_labels) - np.sum(true_labels),
            'evaluation_date': datetime.now().isoformat()
        }
        
        # Model information
        model_info = {
            'model_type': 'IsolationForest',
            'model_path': model_path,
            'contamination': model.contamination,
            'n_estimators': model.n_estimators,
            'max_samples': model.max_samples,
            'bootstrap': model.bootstrap,
            'random_state': model.random_state
        }
        
        # Add config contamination if specified and not 'auto'
        contamination_from_config = config.get('model', {}).get('contamination', 0)
        if contamination_from_config != 'auto':
            model_info['config_contamination'] = contamination_from_config
            
        evaluation_results['model_info'] = model_info
        
        return evaluation_results

    def _output_results(self, evaluation_results: Dict[str, Any], config: Dict[str, Any]):
        """Output evaluation results in specified format."""
        evaluation_config = config.get('evaluation', {})
        output_format = evaluation_config.get('output_format', 'both')
        
        if output_format in ['json', 'both']:
            self._save_evaluation_results(evaluation_results, evaluation_config)
        
        if output_format in ['console', 'both']:
            self._print_evaluation_results(evaluation_results, config)

    def _save_evaluation_results(self, evaluation_results: Dict[str, Any], evaluation_config: Dict[str, Any]):
        """Save evaluation results to JSON file."""
        try:
            # Setup log path
            log_directory = evaluation_config.get('log_directory', 'data/evaluation_logs')
            log_filename = evaluation_config.get('log_filename', 'evaluation_results.json')
            os.makedirs(log_directory, exist_ok=True)
            
            evaluation_log_path = os.path.join(log_directory, log_filename)
            
            # Convert numpy types for JSON serialization
            serializable_results = self._convert_numpy_types(evaluation_results)
            serializable_results['evaluation_timestamp'] = datetime.now().isoformat()
            
            # Read existing results and prepend new result
            existing_results = self._read_existing_results(evaluation_log_path)
            all_results = [serializable_results] + existing_results
            
            # Write results
            with open(evaluation_log_path, 'w') as f:
                json.dump(all_results, f, indent=2)
            
            logger.info(f'Evaluation results appended to top of {evaluation_log_path}')
            self.stdout.write(f'Evaluation results appended to top of {evaluation_log_path}')
            
        except Exception as e:
            logger.error(f'Error saving evaluation results: {e}', exc_info=True)
            self.stderr.write(f'Error saving evaluation results: {e}')

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

    def _read_existing_results(self, log_path: str) -> List[Dict[str, Any]]:
        """Read existing evaluation results from file."""
        if not os.path.exists(log_path):
            return []
        
        try:
            with open(log_path, 'r') as f:
                existing_results = json.load(f)
            return existing_results if isinstance(existing_results, list) else [existing_results]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _print_evaluation_results(self, evaluation_results: Dict[str, Any], config: Dict[str, Any]):
        """Print evaluation results to console."""
        if not evaluation_results:
            return
        
        evaluation_config = config.get('evaluation', {})
        reporting_config = evaluation_config.get('reporting', {})
        
        include_dataset_info = reporting_config.get('include_dataset_info', True)
        include_model_info = reporting_config.get('include_model_info', True)
        include_prediction_summary = reporting_config.get('include_prediction_summary', True)
        include_confusion_matrix = reporting_config.get('include_confusion_matrix', True)
            
        self.stdout.write('\n' + '='*60)
        self.stdout.write('MODEL EVALUATION RESULTS')
        self.stdout.write('='*60)
        
        # Dataset information
        if include_dataset_info:
            self._print_dataset_info(evaluation_results)
        
        # Model information
        if include_model_info:
            self._print_model_info(evaluation_results)
        
        # Performance metrics
        self._print_performance_metrics(evaluation_results)
        
        # Prediction summary
        if include_prediction_summary:
            self._print_prediction_summary(evaluation_results)
        
        # Confusion matrix
        if include_confusion_matrix and 'confusion_matrix' in evaluation_results:
            self._print_confusion_matrix(evaluation_results)
        
        self.stdout.write('\n' + '='*60)

    def _print_dataset_info(self, evaluation_results: Dict[str, Any]):
        """Print dataset information."""
        dataset_info = evaluation_results.get('dataset_info', {})
        self.stdout.write(f'\nDataset Information:')
        self.stdout.write(f'  - Total samples: {dataset_info.get("sample_count", "N/A")}')
        self.stdout.write(f'  - Features: {dataset_info.get("feature_count", "N/A")}')
        self.stdout.write(f'  - True anomalies: {dataset_info.get("true_anomalies", "N/A")}')
        self.stdout.write(f'  - True normal: {dataset_info.get("true_normal", "N/A")}')

    def _print_model_info(self, evaluation_results: Dict[str, Any]):
        """Print model information."""
        model_info = evaluation_results.get('model_info', {})
        self.stdout.write(f'\nModel Information:')
        self.stdout.write(f'  - Model type: {model_info.get("model_type", "N/A")}')
        self.stdout.write(f'  - Model Contamination: {model_info.get("contamination", "N/A")}')
        self.stdout.write(f'  - Configured Contamination: {model_info.get("config_contamination", "N/A")}')
        self.stdout.write(f'  - Estimators: {model_info.get("n_estimators", "N/A")}')

    def _print_performance_metrics(self, evaluation_results: Dict[str, Any]):
        """Print performance metrics."""
        self.stdout.write(f'\nPerformance Metrics:')
        metrics = ['precision', 'recall', 'f1_score', 'accuracy', 'specificity', 'balanced_accuracy']
        for metric in metrics:
            if metric in evaluation_results:
                self.stdout.write(f'  - {metric.title()}: {evaluation_results.get(metric, 0):.4f}')

    def _print_prediction_summary(self, evaluation_results: Dict[str, Any]):
        """Print prediction summary."""
        self.stdout.write(f'\nPrediction Summary:')
        self.stdout.write(f'  - Predicted anomalies: {evaluation_results.get("predicted_anomalies", 0)}')
        self.stdout.write(f'  - Predicted normal: {evaluation_results.get("predicted_normal", 0)}')
        self.stdout.write(f'  - True positives: {evaluation_results.get("true_positives", 0)}')
        self.stdout.write(f'  - False positives: {evaluation_results.get("false_positives", 0)}')
        self.stdout.write(f'  - False negatives: {evaluation_results.get("false_negatives", 0)}')
        self.stdout.write(f'  - True negatives: {evaluation_results.get("true_negatives", 0)}')

    def _print_confusion_matrix(self, evaluation_results: Dict[str, Any]):
        """Print confusion matrix."""
        cm = evaluation_results.get('confusion_matrix', [])
        if cm:
            self.stdout.write(f'\nConfusion Matrix:')
            self.stdout.write(f'  [[{cm[0][0]:>6} {cm[0][1]:>6}]')
            self.stdout.write(f'   [{cm[1][0]:>6} {cm[1][1]:>6}]]')
            self.stdout.write(f'  (TN: {cm[0][0]}, FP: {cm[0][1]}, FN: {cm[1][0]}, TP: {cm[1][1]})')

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the configuration structure."""
        required_sections = ['data_source']
        
        for section in required_sections:
            if section not in config:
                logger.error(f'Missing required configuration section: {section}')
                self.stderr.write(f'Missing required configuration section: {section}')
                return False
        
        # Validate evaluation configuration if present
        if 'evaluation' in config:
            evaluation_config = config['evaluation']
            if 'log_directory' in evaluation_config:
                log_dir = evaluation_config['log_directory']
                if not isinstance(log_dir, str):
                    logger.error('log_directory must be a string')
                    self.stderr.write('log_directory must be a string')
                    return False
        
        return True

    def _resolve_path(self, path: str) -> str:
        """Resolve relative paths to absolute paths."""
        if path and not os.path.isabs(path):
            return os.path.join(settings.BASE_DIR, path)
        return path

    def _check_file_exists(self, file_path: str, file_description: str) -> bool:
        """Check if a file exists and log appropriate messages."""
        if not os.path.exists(file_path):
            logger.error(f'{file_description.capitalize()} not found at {file_path}')
            self.stderr.write(f'{file_description.capitalize()} not found at {file_path}. Please train the model first.')
            return False
        return True