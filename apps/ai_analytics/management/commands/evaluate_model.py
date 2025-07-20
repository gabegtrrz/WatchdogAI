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

            # Get the actual model file path for metadata
            model_config = config.get('model', {})
            actual_model_path = self._resolve_path(model_config.get('model_path', DEFAULT_MODEL_PATH))

            # Process evaluation data
            df_processed, true_labels = self._process_evaluation_data(config)
            if df_processed is None or true_labels is None:
                return

            # Perform evaluation
            evaluation_results = self._evaluate_model(
                model, df_processed, training_columns, config, 
                actual_model_path, true_labels
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
            df_processed = self._clean_and_add_features(df)
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

    def _clean_and_add_features(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Clean and process the raw data."""
        try:
            logger.info('Cleaning raw data...')
            cleaned_df = preprocessing.clean_raw_data(df)
            logger.info(f'Cleaned data shape: {cleaned_df.shape}')

            logger.info('Starting feature engineering...')
            df_processed, _ = feature_engineering.create_features(cleaned_df)
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

            # Get predictions and anomaly scores
            prediction_results = self._get_predictions_and_scores(model, features_df, config)
            if prediction_results is None:
                return None
            
            predicted_labels, anomaly_scores, threshold = prediction_results

            # Calculate metrics
            evaluation_results = self._calculate_metrics(true_labels, predicted_labels, config)
            
            # Add metadata
            evaluation_results = self._add_metadata(evaluation_results, df_processed, training_columns, 
                                                 true_labels, model, model_path, config)
            
            # Create output DataFrame with anomaly detection results
            output_df = self._create_output_dataframe(df_processed, predicted_labels, anomaly_scores, 
                                                    threshold, true_labels, config)
            if output_df is not None:
                self._save_output_dataframe(output_df, config)
            
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
        
        # Ensure we return a DataFrame, not a Series
        if isinstance(features_df, pd.Series):
            features_df = features_df.to_frame().T
        
        return features_df

    def _get_predictions_and_scores(self, model, features_df: pd.DataFrame, config: Dict[str, Any]) -> Optional[tuple[np.ndarray, np.ndarray, float]]:
        """Get predictions and anomaly scores from the trained model."""
        logger.info('Getting predictions and anomaly scores from trained model...')

        try:
            # Get raw anomaly scores (lower score means more anomalous)
            anomaly_scores = model.score_samples(features_df)

            logger.debug(f'Anomaly scores:\n{chr(10).join([f"  [{i}]: {score}" for i, score in enumerate(anomaly_scores)])}')

            # Determine contamination rate for thresholding
            contamination = self._get_contamination_rate(model, config)
            
            logger.debug(f'Contamination before thresholding: {contamination}')

            # Calculate threshold based on contamination rate
            threshold = np.percentile(anomaly_scores, contamination * 100)

            logger.debug(f'Threshold: {threshold}')

            # Classify samples as anomalies (1) or normal (0)
            predicted_labels = (anomaly_scores <= threshold).astype(int)

            logger.debug(f'Predicted labels:\n{chr(10).join([f"  [{i}]: {label}" for i, label in enumerate(predicted_labels)])}')

            logger.info(f'Predicted anomalies: {np.sum(predicted_labels)} out of {len(predicted_labels)}')
            logger.info(f'Contamination rate: {contamination:.4f}')
            logger.info(f'Final Threshold: {threshold:.4f}')

            return predicted_labels, anomaly_scores, threshold
            
        except Exception as e:
            logger.error(f'Error getting predictions and scores: {e}', exc_info=True)
            self.stderr.write(f'Error getting predictions and scores: {e}')
            return None

    def _get_contamination_rate(self, model, config: Dict[str, Any]) -> float:
        """Get the contamination rate from the config, falling back to the model's default."""
        
        contamination_from_config = config.get('model', {}).get('contamination', None)

        # Check if the config value exists before trying to parse it.
        if contamination_from_config is not None:
            try:
                if str(contamination_from_config).lower() == 'auto':
                    logger.info("Using 'auto' contamination rate from config.")
                    # For 'auto', use model's contamination rate
                    return float(getattr(model, 'contamination', 0.05))
                
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

        return float(default_rate)

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
        
        # Add anomaly configuration from YAML
        evaluation_results['anomaly_configuration'] = {
            'model_config': config.get('model', {}),
            'data_source_config': config.get('data_source', {}),
            'evaluation_config': config.get('evaluation', {}),
            'advanced_config': config.get('advanced', {})
        }
        
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
        self.stdout.write(f'  - Model path: {model_info.get("model_path", "N/A")}')
        self.stdout.write(f'  - Model Contamination: {model_info.get("contamination", "N/A")}')
        self.stdout.write(f'  - Configured Contamination: {model_info.get("config_contamination", "N/A")}')
        self.stdout.write(f'  - Estimators: {model_info.get("n_estimators", "N/A")}')
        
        # Print anomaly configuration summary
        anomaly_config = evaluation_results.get('anomaly_configuration', {})
        if anomaly_config:
            self.stdout.write(f'\nAnomaly Configuration:')
            model_config = anomaly_config.get('model_config', {})
            if model_config:
                self.stdout.write(f'  - Model path: {model_config.get("model_path", "Default")}')
                self.stdout.write(f'  - Contamination: {model_config.get("contamination", "Default")}')
            
            data_source = anomaly_config.get('data_source_config', {})
            if data_source:
                csv_path = data_source.get('csv_path')
                if csv_path:
                    self.stdout.write(f'  - Data source: CSV ({csv_path})')
                else:
                    self.stdout.write(f'  - Data source: Database')

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

    def _create_output_dataframe(self, df_processed: pd.DataFrame, predicted_labels: np.ndarray, 
                                anomaly_scores: np.ndarray, threshold: float, true_labels: np.ndarray, 
                                config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Create output DataFrame with original data plus anomaly detection results."""
        try:
            # Get the original raw data to include original columns
            original_df = self._get_original_data_for_output(config)
            
            # Start with the processed data
            output_df = df_processed.copy()
            
            # Add original columns if available and different from processed data
            if original_df is not None and not original_df.empty:
                # Get original columns that are not in processed data
                original_cols = [col for col in original_df.columns if col not in output_df.columns]
                if original_cols:
                    # Add original columns to output DataFrame
                    for col in original_cols:
                        if col in original_df.columns:
                            output_df[col] = original_df[col].values[:len(output_df)]
                    logger.info(f'Added {len(original_cols)} original columns to output DataFrame')
            
            # Filter columns based on configuration
            output_df = self._filter_output_columns(output_df, config)
            
            # Add anomaly detection columns
            output_df['anomaly_score'] = anomaly_scores
            output_df['predicted_anomaly'] = predicted_labels
            output_df['anomaly_threshold'] = threshold
            
            # Add true labels if available
            if true_labels is not None:
                output_df['true_anomaly'] = true_labels
                output_df['prediction_correct'] = (predicted_labels == true_labels).astype(int)
            
            # Add contamination rate used for prediction
            contamination_rate = self._get_contamination_rate_from_config(config)
            output_df['contamination_rate'] = contamination_rate
            
            # Add prediction confidence (distance from threshold)
            output_df['prediction_confidence'] = np.abs(anomaly_scores - threshold)
            
            # Add anomaly severity (how far below threshold)
            output_df['anomaly_severity'] = threshold - anomaly_scores
            output_df['anomaly_severity'] = output_df['anomaly_severity'].clip(lower=0)  # Only positive values
            
            # Ensure proper column ordering
            output_df = self._reorder_columns(output_df)
            
            logger.info(f'Created output DataFrame with {output_df.shape[0]} rows and {output_df.shape[1]} columns')
            return output_df
            
        except Exception as e:
            logger.error(f'Error creating output DataFrame: {e}', exc_info=True)
            self.stderr.write(f'Error creating output DataFrame: {e}')
            return None

    def _filter_output_columns(self, output_df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Filter columns based on configuration settings."""
        evaluation_config = config.get('evaluation', {})
        output_config = evaluation_config.get('output', {})
        
        # Get column inclusion settings
        include_original_features = output_config.get('include_original_features', True)
        include_anomaly_columns = output_config.get('include_anomaly_columns', True)
        include_specific_columns = output_config.get('include_specific_columns', [])
        exclude_specific_columns = output_config.get('exclude_specific_columns', [])
        
        # Define anomaly detection columns
        anomaly_columns = [
            'anomaly_score', 'predicted_anomaly', 'anomaly_threshold', 'contamination_rate',
            'prediction_confidence', 'anomaly_severity', 'true_anomaly', 'prediction_correct'
        ]
        
        # Start with all columns
        available_columns = list(output_df.columns)
        columns_to_keep = []
        
        # Add original features if requested
        if include_original_features:
            original_columns = [col for col in available_columns if col not in anomaly_columns]
            columns_to_keep.extend(original_columns)
        
        # Add specific columns if requested
        if include_specific_columns:
            for col in include_specific_columns:
                if col in available_columns and col not in columns_to_keep:
                    columns_to_keep.append(col)
                    logger.info(f'Including specific column: {col}')
        
        # Remove excluded columns
        if exclude_specific_columns:
            for col in exclude_specific_columns:
                if col in columns_to_keep:
                    columns_to_keep.remove(col)
                    logger.info(f'Excluding specific column: {col}')
        
        # Filter the DataFrame
        if columns_to_keep:
            filtered_df = output_df[columns_to_keep]
            # Ensure we return a DataFrame, not a Series
            if isinstance(filtered_df, pd.Series):
                output_df = filtered_df.to_frame().T
            else:
                output_df = filtered_df
            logger.info(f'Filtered output DataFrame to {len(columns_to_keep)} columns')
        
        return output_df

    def _reorder_columns(self, output_df: pd.DataFrame) -> pd.DataFrame:
        """Reorder columns to ensure proper ordering, especially procurement_method__name before is_anomaly."""
        try:
            # Define priority columns that should appear first
            priority_columns = [
                'transaction_id',
                'item_name', 
                'quantity',
                'unit_purchase_price',
                'procurement_method__name',  # Ensure this comes before is_anomaly
                'supplier',
                'transaction_date'
            ]
            
            # Get all available columns
            all_columns = list(output_df.columns)
            
            # Start with priority columns that exist in the DataFrame
            ordered_columns = [col for col in priority_columns if col in all_columns]
            
            # Add remaining columns (excluding priority columns already added)
            remaining_columns = [col for col in all_columns if col not in ordered_columns]
            ordered_columns.extend(remaining_columns)
            
            # Reorder the DataFrame
            if ordered_columns:
                reordered_df = output_df[ordered_columns]
                # Ensure we return a DataFrame, not a Series
                if isinstance(reordered_df, pd.Series):
                    output_df = reordered_df.to_frame().T
                else:
                    output_df = reordered_df
                logger.info(f'Reordered columns with {len(ordered_columns)} total columns')
            
            return output_df
            
        except Exception as e:
            logger.warning(f'Error reordering columns: {e}')
            return output_df

    def _get_original_data_for_output(self, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Get original raw data for including original columns in output."""
        try:
            # Get raw data using the same method as in _get_raw_data
            csv_source = config.get('data_source', {}).get('csv_path')
            
            if csv_source:
                logger.info(f'Getting original data from CSV: {csv_source}')
                return preprocessing.get_dataframe(csv_source)
            else:
                logger.info('Getting original data from database')
                return preprocessing.get_dataframe()
                
        except Exception as e:
            logger.warning(f'Could not retrieve original data for output: {e}')
            return None

    def _get_contamination_rate_from_config(self, config: Dict[str, Any]) -> float:
        """Get contamination rate from config or return default."""
        contamination_from_config = config.get('model', {}).get('contamination', None)
        
        if contamination_from_config is not None:
            try:
                if str(contamination_from_config).lower() == 'auto':
                    return 0.05  # Default auto value
                return float(contamination_from_config)
            except (ValueError, TypeError):
                pass
        
        return 0.05  # Default fallback

    def _save_output_dataframe(self, output_df: pd.DataFrame, config: Dict[str, Any]):
        """Save the output DataFrame with anomaly detection results to CSV."""
        try:
            # Get output configuration
            evaluation_config = config.get('evaluation', {})
            output_config = evaluation_config.get('output', {})
            
            # Determine output path
            output_directory = output_config.get('output_directory', 'data/evaluation_output')
            output_filename = output_config.get('output_filename', '')
            if output_filename:
                output_filename = f'{output_filename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            else:
                output_filename = f'iforest_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
            # Create directory if it doesn't exist
            os.makedirs(output_directory, exist_ok=True)
            output_path = os.path.join(output_directory, output_filename)
            
            # Save DataFrame to CSV
            output_df.to_csv(output_path, index=False)
            
            logger.info(f'Anomaly detection results saved to: {output_path}')
            self.stdout.write(f'Anomaly detection results saved to: {output_path}')
            
            # Print summary statistics
            self._print_output_summary(output_df)
            
        except Exception as e:
            logger.error(f'Error saving output DataFrame: {e}', exc_info=True)
            self.stderr.write(f'Error saving output DataFrame: {e}')

    def _print_output_summary(self, output_df: pd.DataFrame):
        """Print summary of the output DataFrame."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('ANOMALY DETECTION OUTPUT SUMMARY')
        self.stdout.write('='*60)
        
        # Basic statistics
        total_samples = len(output_df)
        predicted_anomalies = output_df['predicted_anomaly'].sum()
        predicted_normal = total_samples - predicted_anomalies
        
        self.stdout.write(f'\nDataset Summary:')
        self.stdout.write(f'  - Total samples: {total_samples}')
        self.stdout.write(f'  - Predicted anomalies: {predicted_anomalies}')
        self.stdout.write(f'  - Predicted normal: {predicted_normal}')
        self.stdout.write(f'  - Anomaly rate: {predicted_anomalies/total_samples:.2%}')
        
        # Column information
        all_columns = list(output_df.columns)
        original_columns = [col for col in all_columns if col not in [
            'anomaly_score', 'predicted_anomaly', 'anomaly_threshold', 'contamination_rate',
            'prediction_confidence', 'anomaly_severity', 'true_anomaly', 'prediction_correct'
        ]]
        
        self.stdout.write(f'\nOutput DataFrame Columns:')
        self.stdout.write(f'  - Total columns: {len(all_columns)}')
        self.stdout.write(f'  - Original columns: {len(original_columns)}')
        self.stdout.write(f'  - Anomaly detection columns: {len(all_columns) - len(original_columns)}')
        
        if original_columns:
            self.stdout.write(f'  - Original columns: {", ".join(original_columns[:5])}')
            if len(original_columns) > 5:
                self.stdout.write(f'    ... and {len(original_columns) - 5} more')
        
        # Anomaly score statistics
        if 'anomaly_score' in output_df.columns:
            scores = output_df['anomaly_score']
            self.stdout.write(f'\nAnomaly Score Statistics:')
            self.stdout.write(f'  - Mean: {scores.mean():.4f}')
            self.stdout.write(f'  - Std: {scores.std():.4f}')
            self.stdout.write(f'  - Min: {scores.min():.4f}')
            self.stdout.write(f'  - Max: {scores.max():.4f}')
            self.stdout.write(f'  - Threshold: {output_df["anomaly_threshold"].iloc[0]:.4f}')
        
        # Prediction confidence statistics
        if 'prediction_confidence' in output_df.columns:
            confidence = output_df['prediction_confidence']
            self.stdout.write(f'\nPrediction Confidence Statistics:')
            self.stdout.write(f'  - Mean: {confidence.mean():.4f}')
            self.stdout.write(f'  - Std: {confidence.std():.4f}')
            self.stdout.write(f'  - Min: {confidence.min():.4f}')
            self.stdout.write(f'  - Max: {confidence.max():.4f}')
        
        # Anomaly severity statistics
        if 'anomaly_severity' in output_df.columns:
            severity = output_df['anomaly_severity']
            anomaly_severity = severity[severity > 0]
            if len(anomaly_severity) > 0:
                self.stdout.write(f'\nAnomaly Severity Statistics (for detected anomalies):')
                self.stdout.write(f'  - Mean: {anomaly_severity.mean():.4f}')
                self.stdout.write(f'  - Std: {anomaly_severity.std():.4f}')
                self.stdout.write(f'  - Min: {anomaly_severity.min():.4f}')
                self.stdout.write(f'  - Max: {anomaly_severity.max():.4f}')
        
        # Accuracy if true labels are available
        if 'prediction_correct' in output_df.columns:
            accuracy = output_df['prediction_correct'].mean()
            self.stdout.write(f'\nPrediction Accuracy: {accuracy:.2%}')
        
        self.stdout.write('\n' + '='*60)

    def _get_predictions(self, model, features_df: pd.DataFrame, config: Dict[str, Any]) -> Optional[np.ndarray]:
        """Get predictions from the trained model (deprecated - use _get_predictions_and_scores instead)."""
        prediction_results = self._get_predictions_and_scores(model, features_df, config)
        if prediction_results is None:
            return None
        predicted_labels, _, _ = prediction_results
        return predicted_labels