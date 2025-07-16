"""
Management command to evaluate the Isolation Forest model metrics on test data.
"""
import os
import joblib
import json
import logging
import yaml
from datetime import datetime
from typing import Union, List
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
        logger.info('Starting model evaluation...')
        self.stdout.write('Starting model evaluation...')

        # Load configuration
        config_path = options['config']
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f'Loaded configuration from {config_path}')
        except Exception as e:
            logger.error(f'Error loading configuration: {e}', exc_info=True)
            self.stderr.write(f'Error loading configuration: {e}')
            return

        # Validate configuration
        if not self._validate_config(config):
            return

        # Get model paths from config or use defaults
        model_config = config.get('model', {})
        
        # Handle model path - can be relative or absolute
        model_path = model_config.get('model_path', DEFAULT_MODEL_PATH)
        if model_path and not os.path.isabs(model_path):
            # If relative path, make it relative to BASE_DIR
            model_path = os.path.join(settings.BASE_DIR, model_path)
        
        # Handle columns path - can be relative or absolute
        columns_path = model_config.get('columns_path', DEFAULT_COLUMNS_PATH)
        if columns_path and not os.path.isabs(columns_path):
            # If relative path, make it relative to BASE_DIR
            columns_path = os.path.join(settings.BASE_DIR, columns_path)
        
        # Get contamination parameter from config (optional)
        contamination = model_config.get('contamination', 'auto')
        logger.info(f'Contamination parameter from config: {contamination}')
        self.stdout.write(f'Contamination parameter from config: {contamination}')
        
        # Get evaluation configuration
        evaluation_config = config.get('evaluation', {})
        output_format = evaluation_config.get('output_format', 'both')
        
        # Setup evaluation log path - single file with results appended to top
        log_directory = evaluation_config.get('log_directory', 'data/evaluation_logs')
        log_filename = evaluation_config.get('log_filename', 'evaluation_results.json')
        
        # Create log directory if it doesn't exist
        os.makedirs(log_directory, exist_ok=True)
        logger.info(f'Evaluation log directory ensured: {log_directory}')
        
        evaluation_log_path = os.path.join(log_directory, log_filename)
        logger.info(f'Evaluation log path: {evaluation_log_path}')

        # Check if trained model exists
        if not os.path.exists(model_path):
            logger.error(f'Trained model not found at {model_path}')
            self.stderr.write(f'Trained model not found at {model_path}. Please train the model first.')
            return

        if not os.path.exists(columns_path):
            logger.error(f'Training columns not found at {columns_path}')
            self.stderr.write(f'Training columns not found at {columns_path}. Please train the model first.')
            return

        # Load trained model and training columns
        try:
            model = joblib.load(model_path)
            training_columns = joblib.load(columns_path)
            logger.info('Successfully loaded trained model and training columns')
            
            
            if contamination != 'auto':
                if hasattr(model, 'contamination'):
                    old_contamination = model.contamination
                    model.contamination = contamination
                    logger.info(f'Updated model contamination from {old_contamination} to {contamination}')
                    self.stdout.write(f'Updated model contamination from {old_contamination} to {contamination}')
                else:
                    logger.warning('Model does not have contamination attribute, ignoring config parameter')
                    self.stdout.write('Model does not have contamination attribute, ignoring config parameter')
                    
        except Exception as e:
            logger.error(f'Error loading trained model: {e}', exc_info=True)
            self.stderr.write(f'Error loading trained model: {e}')
            return

        # Get and preprocess evaluation data
        logger.info('Fetching and preprocessing evaluation data...')
        self.stdout.write('Fetching and preprocessing evaluation data...')
        
        try:
            csv_source = config.get('data_source', {}).get('csv_path')
            if csv_source:
                logger.info(f'Using CSV source: {csv_source}')
                self.stdout.write(f'Using CSV source: {csv_source}')
                df = preprocessing.get_dataframe(csv_source)
            else:
                logger.info('Using database as data source')
                self.stdout.write('Using database as data source')
                df = preprocessing.get_dataframe()
                
            logger.info(f'Raw data shape: {df.shape}')
            if df.empty:
                logger.warning('No transaction data found for evaluation.')
                self.stdout.write('No transaction data found for evaluation.')
                return
        except Exception as e:
            logger.error(f'Error during data fetching: {e}', exc_info=True)
            self.stderr.write(f'Error during data fetching: {e}')
            return
        
        try:
            logger.info('Cleaning raw data...')
            cleaned_df = preprocessing.clean_raw_data(df)
            logger.info(f'Cleaned data shape: {cleaned_df.shape}')
        except Exception as e:
            logger.error(f'Error during data preprocessing: {e}', exc_info=True)
            self.stderr.write(f'Error during data preprocessing: {e}')
            return

        # Engineer features
        logger.info('Starting feature engineering...')
        try:
            df_processed, _ = feature_engineering.create_model_features(cleaned_df)
            logger.info(f'Feature engineering completed. Processed data shape: {df_processed.shape}')
        except Exception as e:
            logger.error(f'Error during feature engineering: {e}', exc_info=True)
            self.stderr.write(f'Error during feature engineering: {e}')
            return

        # Check if data has labels for evaluation
        if 'is_anomaly' not in df_processed.columns:
            logger.warning('No anomaly labels found in data. Cannot perform supervised evaluation.')
            self.stdout.write('No anomaly labels found in data. Cannot perform supervised evaluation.')
            return

        # Perform evaluation
        evaluation_results = self._evaluate_model(model, df_processed, training_columns, config, model_path)
        
        # Output results
        if output_format in ['json', 'both']:
            self._save_evaluation_results(evaluation_results, evaluation_log_path)
        
        if output_format in ['console', 'both']:
            self._print_evaluation_results(evaluation_results, config)

        logger.info('Model evaluation complete.')
        self.stdout.write('Model evaluation complete.')

    def _validate_config(self, config: dict) -> bool:
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

    def _evaluate_model(self, model, df_processed, training_columns, config=None, model_path=None):
        """Evaluate the trained model on labeled data."""
        logger.info('Evaluating trained model...')
        self.stdout.write('Evaluating trained model...')
        
        try:
            labeled_df = df_processed.copy()
            logger.info(f'Labeled data shape: {labeled_df.shape}')
            
            # Get true labels (1 for anomaly, 0 for normal)
            true_labels = labeled_df['is_anomaly'].values
            true_labels_binary = (true_labels == 1).astype(int)
            logger.info(f'True labels binary distribution: {np.bincount(true_labels_binary)}')
            
            # Get advanced configuration
            advanced_config = config.get('advanced', {}) if config else {}
            handle_missing_columns = advanced_config.get('handle_missing_columns', True)
            missing_column_default = advanced_config.get('missing_column_default', 0)
            remove_extra_columns = advanced_config.get('remove_extra_columns', True)
            
            # Get contamination from config if available
            contamination = None
            if config and 'model' in config:
                contamination = config['model'].get('contamination', 'auto')
            
            # Prepare features for prediction (drop label column)
            features_df = labeled_df.drop('is_anomaly', axis=1)
            
            # Debug: Check what columns we have after dropping is_anomaly
            logger.info(f'Columns after dropping is_anomaly: {list(features_df.columns)}')
            logger.info(f'Training columns: {list(training_columns)}')
            
            # Ensure we have the same columns as training
            missing_columns = set(training_columns) - set(features_df.columns)
            extra_columns = set(features_df.columns) - set(training_columns)
            
            logger.info(f'Missing columns: {missing_columns}')
            logger.info(f'Extra columns: {extra_columns}')
            
            if missing_columns and handle_missing_columns:
                logger.warning(f'Missing columns in evaluation data: {missing_columns}')
                # Add missing columns with default values
                for col in missing_columns:
                    features_df[col] = missing_column_default
            
            if extra_columns and remove_extra_columns:
                logger.warning(f'Extra columns in evaluation data: {extra_columns}')
                # Remove extra columns
                features_df = features_df[training_columns]
            
            logger.info(f'Features shape for prediction: {features_df.shape}')
            logger.info(f'Final feature columns: {list(features_df.columns)}')

            # Safety check: Ensure is_anomaly is not in features
            if 'is_anomaly' in features_df.columns:
                logger.error('is_anomaly column still present in features! Removing it...')
                features_df = features_df.drop('is_anomaly', axis=1)
                logger.info(f'Features shape after removing is_anomaly: {features_df.shape}')

            # Get predictions from trained model
            logger.info('Getting predictions from trained model...')
            scores = model.predict(features_df)
            
            # Convert scores to binary predictions: -1 (anomaly) -> 1, 1 (normal) -> 0
            predicted_labels = (scores == -1).astype(int)
            logger.info(f'Predicted anomalies: {np.sum(predicted_labels)} out of {len(predicted_labels)}')
            
            # Calculate evaluation metrics
            evaluation_results = self._calculate_metrics(true_labels_binary, predicted_labels, config)
            
            # Add dataset information
            evaluation_results['dataset_info'] = {
                'sample_count': df_processed.shape[0],
                'feature_count': df_processed.shape[1],
                'feature_columns': list(training_columns),
                'labeled_data_count': len(true_labels_binary),
                'true_anomalies': np.sum(true_labels_binary),
                'true_normal': len(true_labels_binary) - np.sum(true_labels_binary),
                'evaluation_date': datetime.now().isoformat()
            }
            
            # Add model information
            model_info = {
                'model_type': 'IsolationForest',
                'model_path': model_path,  # Include model path
                'contamination': model.contamination,
                'n_estimators': model.n_estimators,
                'max_samples': model.max_samples,
                'bootstrap': model.bootstrap,
                'random_state': model.random_state
            }
            
            # Add config contamination if specified and not 'auto'
            if contamination != 'auto':
                model_info['config_contamination'] = contamination
                
            evaluation_results['model_info'] = model_info
            
            return evaluation_results

        except Exception as e:
            logger.error(f'Error during model evaluation: {e}', exc_info=True)
            self.stderr.write(f'Error during model evaluation: {e}')
            return None

    def _calculate_metrics(self, true_labels, predicted_labels, config=None):
        """Calculate comprehensive evaluation metrics."""
        logger.info('Calculating evaluation metrics...')
        
        # Get evaluation configuration
        evaluation_config = config.get('evaluation', {}) if config else {}
        metrics_to_calculate = evaluation_config.get('metrics', [
            'precision', 'recall', 'f1_score', 'accuracy', 
            'specificity', 'balanced_accuracy', 'confusion_matrix'
        ])
        
        # Handle case where no anomalies are predicted
        if np.sum(predicted_labels) == 0:
            logger.warning('No anomalies predicted by the model')
            precision = 0.0
            recall = 0.0
            f1 = 0.0
        else:
            precision = precision_score(true_labels, predicted_labels, zero_division='warn')
            recall = recall_score(true_labels, predicted_labels, zero_division='warn')
            f1 = f1_score(true_labels, predicted_labels, zero_division='warn')
        
        # Calculate confusion matrix
        cm = confusion_matrix(true_labels, predicted_labels)
        
        # Calculate additional metrics
        tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
        
        # Calculate specificity (True Negative Rate)
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        
        # Calculate accuracy
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
        
        # Calculate balanced accuracy
        balanced_accuracy = (recall + specificity) / 2
        
        metrics = {}
        
        # Only include metrics that are requested
        if 'precision' in metrics_to_calculate:
            metrics['precision'] = float(precision)
        if 'recall' in metrics_to_calculate:
            metrics['recall'] = float(recall)
        if 'f1_score' in metrics_to_calculate:
            metrics['f1_score'] = float(f1)
        if 'accuracy' in metrics_to_calculate:
            metrics['accuracy'] = float(accuracy)
        if 'specificity' in metrics_to_calculate:
            metrics['specificity'] = float(specificity)
        if 'balanced_accuracy' in metrics_to_calculate:
            metrics['balanced_accuracy'] = float(balanced_accuracy)
        if 'confusion_matrix' in metrics_to_calculate:
            metrics['confusion_matrix'] = cm.tolist()
        
        # Always include prediction counts
        metrics.update({
            'predicted_anomalies': int(np.sum(predicted_labels)),
            'predicted_normal': int(len(predicted_labels) - np.sum(predicted_labels)),
            'true_anomalies': int(np.sum(true_labels)),
            'true_normal': int(len(true_labels) - np.sum(true_labels)),
            'true_positives': int(tp),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_negatives': int(tn)
        })
        
        logger.info(f'Evaluation metrics calculated:')
        if 'precision' in metrics:
            logger.info(f'  - Precision: {precision:.4f}')
        if 'recall' in metrics:
            logger.info(f'  - Recall: {recall:.4f}')
        if 'f1_score' in metrics:
            logger.info(f'  - F1-Score: {f1:.4f}')
        if 'accuracy' in metrics:
            logger.info(f'  - Accuracy: {accuracy:.4f}')
        if 'specificity' in metrics:
            logger.info(f'  - Specificity: {specificity:.4f}')
        if 'balanced_accuracy' in metrics:
            logger.info(f'  - Balanced Accuracy: {balanced_accuracy:.4f}')
        
        return metrics

    def _save_evaluation_results(self, evaluation_results, evaluation_log_path):
        """Save evaluation results to JSON file, appending to top."""
        try:
            # Convert numpy types to native Python types for JSON serialization
            def convert_numpy_types(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {key: convert_numpy_types(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_types(item) for item in obj]
                else:
                    return obj
            
            serializable_results = convert_numpy_types(evaluation_results)
            
            # Read existing results if file exists
            existing_results = []
            if os.path.exists(evaluation_log_path):
                try:
                    with open(evaluation_log_path, 'r') as f:
                        existing_results = json.load(f)
                    if not isinstance(existing_results, list):
                        existing_results = [existing_results]
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_results = []
            
            # Add timestamp to new result
            serializable_results['evaluation_timestamp'] = datetime.now().isoformat()
            
            # Prepend new result to existing results
            all_results = [serializable_results] + existing_results
            
            # Write all results back to file
            with open(evaluation_log_path, 'w') as f:
                json.dump(all_results, f, indent=2)
            
            logger.info(f'Evaluation results appended to top of {evaluation_log_path}')
            self.stdout.write(f'Evaluation results appended to top of {evaluation_log_path}')
            
        except Exception as e:
            logger.error(f'Error saving evaluation results: {e}', exc_info=True)
            self.stderr.write(f'Error saving evaluation results: {e}')

    def _print_evaluation_results(self, evaluation_results, config=None):
        """Print evaluation results to console."""
        if not evaluation_results:
            return
        
        # Get reporting configuration
        evaluation_config = config.get('evaluation', {}) if config else {}
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
            dataset_info = evaluation_results.get('dataset_info', {})
            self.stdout.write(f'\nDataset Information:')
            self.stdout.write(f'  - Total samples: {dataset_info.get("sample_count", "N/A")}')
            self.stdout.write(f'  - Features: {dataset_info.get("feature_count", "N/A")}')
            self.stdout.write(f'  - True anomalies: {dataset_info.get("true_anomalies", "N/A")}')
            self.stdout.write(f'  - True normal: {dataset_info.get("true_normal", "N/A")}')
        
        # Model information
        if include_model_info:
            model_info = evaluation_results.get('model_info', {})
            self.stdout.write(f'\nModel Information:')
            self.stdout.write(f'  - Model type: {model_info.get("model_type", "N/A")}')
            self.stdout.write(f'  - Contamination: {model_info.get("contamination", "N/A")}')
            self.stdout.write(f'  - Estimators: {model_info.get("n_estimators", "N/A")}')
        
        # Performance metrics
        self.stdout.write(f'\nPerformance Metrics:')
        if 'precision' in evaluation_results:
            self.stdout.write(f'  - Precision: {evaluation_results.get("precision", 0):.4f}')
        if 'recall' in evaluation_results:
            self.stdout.write(f'  - Recall: {evaluation_results.get("recall", 0):.4f}')
        if 'f1_score' in evaluation_results:
            self.stdout.write(f'  - F1-Score: {evaluation_results.get("f1_score", 0):.4f}')
        if 'accuracy' in evaluation_results:
            self.stdout.write(f'  - Accuracy: {evaluation_results.get("accuracy", 0):.4f}')
        if 'specificity' in evaluation_results:
            self.stdout.write(f'  - Specificity: {evaluation_results.get("specificity", 0):.4f}')
        if 'balanced_accuracy' in evaluation_results:
            self.stdout.write(f'  - Balanced Accuracy: {evaluation_results.get("balanced_accuracy", 0):.4f}')
        
        # Prediction summary
        if include_prediction_summary:
            self.stdout.write(f'\nPrediction Summary:')
            self.stdout.write(f'  - Predicted anomalies: {evaluation_results.get("predicted_anomalies", 0)}')
            self.stdout.write(f'  - Predicted normal: {evaluation_results.get("predicted_normal", 0)}')
            self.stdout.write(f'  - True positives: {evaluation_results.get("true_positives", 0)}')
            self.stdout.write(f'  - False positives: {evaluation_results.get("false_positives", 0)}')
            self.stdout.write(f'  - False negatives: {evaluation_results.get("false_negatives", 0)}')
            self.stdout.write(f'  - True negatives: {evaluation_results.get("true_negatives", 0)}')
        
        # Confusion matrix
        if include_confusion_matrix and 'confusion_matrix' in evaluation_results:
            cm = evaluation_results.get('confusion_matrix', [])
            if cm:
                self.stdout.write(f'\nConfusion Matrix:')
                self.stdout.write(f'  [[{cm[0][0]:>6} {cm[0][1]:>6}]')
                self.stdout.write(f'   [{cm[1][0]:>6} {cm[1][1]:>6}]]')
                self.stdout.write(f'  (TN: {cm[0][0]}, FP: {cm[0][1]}, FN: {cm[1][0]}, TP: {cm[1][1]})')
        
        self.stdout.write('\n' + '='*60)
