"""
Management command to train and evaluate Isolation Forest models with research mode.
Combines training and evaluation functionality using separate datasets.
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
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, classification_report, roc_curve, auc
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from apps.ai_analytics.services import preprocessing, feature_engineering

# Define default paths for the trained model
DEFAULT_MODEL_DIR = os.path.join(settings.BASE_DIR, 'apps', 'ai_analytics', 'model_files')
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, 'isolation_forest.joblib')
DEFAULT_COLUMNS_PATH = os.path.join(DEFAULT_MODEL_DIR, 'training_columns.joblib')

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Trains and evaluates Isolation Forest models with research mode using separate training and evaluation datasets.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            required=True,
            help='Path to YAML configuration file'
        )

    def handle(self, *args, **options):
        """Main entry point for the command."""
        logger.info('Starting research model training and evaluation...')
        self.stdout.write('Starting research model training and evaluation...')

        try:
            # Load and validate configuration
            config = self._load_configuration(options['config'])
            if not config:
                return

            # Get output paths
            output_paths = self._get_output_paths(config)
            self._ensure_directories_exist(output_paths)

            # Process training data
            training_data, training_columns = self._process_training_data(config)
            if training_data is None or training_columns is None:
                return

            # Process evaluation data
            evaluation_data, true_labels = self._process_evaluation_data(config)
            if evaluation_data is None or true_labels is None:
                return

            # Perform research mode training and evaluation
            research_results = self._research_mode_training_and_evaluation(
                training_data, training_columns, evaluation_data, true_labels, 
                output_paths, config
            )
            if not research_results:
                return

            # Output results
            self._output_results(research_results, config)

            logger.info('Research model training and evaluation complete.')
            self.stdout.write('Research model training and evaluation complete.')

        except Exception as e:
            logger.error(f'Unexpected error during research: {e}', exc_info=True)
            self.stderr.write(f'Unexpected error during research: {e}')

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

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the configuration structure."""
        required_sections = ['data_source', 'model', 'training', 'evaluation']
        
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
        
        # Validate model configuration
        model_config = config.get('model', {})
        if 'contamination_range' not in model_config:
            logger.error('contamination_range must be specified in model configuration')
            self.stderr.write('contamination_range must be specified in model configuration')
            return False
        
        return True

    def _get_output_paths(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Get output paths from configuration."""
        output_config = config.get('output', {})
        base_dir = output_config.get('base_dir', DEFAULT_MODEL_DIR)

        if not os.path.isabs(base_dir):
            base_dir = os.path.join(settings.BASE_DIR, base_dir)

        # Define separate directories for models and results
        model_dir = os.path.join(base_dir, 'models')
        results_dir = os.path.join(base_dir, 'results')

        # Get filenames
        model_filename = output_config.get('model_filename', 'research_isolation_forest.joblib')
        columns_filename = output_config.get('columns_filename', 'research_training_columns.joblib')
        results_filename = output_config.get('results_filename', 'research_results.json')
        roc_curve_filename = output_config.get('roc_curve_filename', 'research_roc_curve.png')

        output_paths = {
            'model_dir': model_dir,
            'results_dir': results_dir,
            'model_path': os.path.join(model_dir, model_filename),
            'columns_path': os.path.join(model_dir, columns_filename),
            'results_path': os.path.join(results_dir, results_filename),
            'roc_curve_path': os.path.join(results_dir, roc_curve_filename)
        }
        
        logger.info(f'Output paths configured:')
        for key, value in output_paths.items():
            logger.info(f'  - {key.replace("_", " ").title()}: {value}')
            
        return output_paths

    def _ensure_directories_exist(self, output_paths: Dict[str, str]):
        """Ensure all required directories exist."""
        directories_to_create = {
            output_paths['model_dir'],
            output_paths['results_dir']
        }
        
        for directory in directories_to_create:
            if directory:
                try:
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f'Ensured directory exists: {directory}')
                except Exception as e:
                    error_msg = f'Failed to create directory {directory}: {e}'
                    logger.error(error_msg)
                    self.stderr.write(error_msg)
                    raise

    def _process_training_data(self, config: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Optional[List[str]]]:
        """Process training data and extract features."""
        logger.info('Processing training data...')
        self.stdout.write('Processing training data...')
        
        try:
            # Get training data
            training_csv_path = config.get('data_source', {}).get('training_csv_path')
            if not training_csv_path:
                logger.error('Training CSV path not specified in configuration')
                self.stderr.write('Training CSV path not specified in configuration')
                return None, None
            
            logger.info(f'Loading training data from: {training_csv_path}')
            df_training = preprocessing.get_dataframe(training_csv_path)
            
            if df_training is None or df_training.empty:
                logger.error('No training data found')
                self.stderr.write('No training data found')
                return None, None
            
            logger.info(f'Training data shape: {df_training.shape}')
            
            # Clean and process training data
            cleaned_df = preprocessing.clean_raw_data(df_training)
            logger.info(f'Cleaned training data shape: {cleaned_df.shape}')
            
            # Engineer features
            df_processed, training_columns = feature_engineering.create_features(cleaned_df)
            logger.info(f'Feature engineering completed. Training data shape: {df_processed.shape}')
            logger.info(f'Training columns: {training_columns}')
            
            return df_processed, training_columns
            
        except Exception as e:
            logger.error(f'Error processing training data: {e}', exc_info=True)
            self.stderr.write(f'Error processing training data: {e}')
            return None, None

    def _process_evaluation_data(self, config: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Optional[np.ndarray]]:
        """Process evaluation data and extract labels."""
        logger.info('Processing evaluation data...')
        self.stdout.write('Processing evaluation data...')
        
        try:
            # Get evaluation data
            evaluation_csv_path = config.get('data_source', {}).get('evaluation_csv_path')
            if not evaluation_csv_path:
                logger.error('Evaluation CSV path not specified in configuration')
                self.stderr.write('Evaluation CSV path not specified in configuration')
                return None, None
            
            logger.info(f'Loading evaluation data from: {evaluation_csv_path}')
            df_evaluation = preprocessing.get_dataframe(evaluation_csv_path)
            
            if df_evaluation is None or df_evaluation.empty:
                logger.error('No evaluation data found')
                self.stderr.write('No evaluation data found')
                return None, None
            
            logger.info(f'Evaluation data shape: {df_evaluation.shape}')
            
            # Extract labels before processing
            true_labels = preprocessing.extract_labels(df_evaluation)
            if true_labels is None:
                logger.error('No anomaly labels found in evaluation data')
                self.stderr.write('No anomaly labels found in evaluation data')
                return None, None
            
            logger.info(f'Labels extracted successfully. Distribution: {np.bincount(true_labels)}')
            
            # Clean and process evaluation data
            cleaned_df = preprocessing.clean_raw_data(df_evaluation)
            logger.info(f'Cleaned evaluation data shape: {cleaned_df.shape}')
            
            # Engineer features (same process as training)
            df_processed, _ = feature_engineering.create_features(cleaned_df)
            logger.info(f'Feature engineering completed. Evaluation data shape: {df_processed.shape}')
            
            return df_processed, true_labels
            
        except Exception as e:
            logger.error(f'Error processing evaluation data: {e}', exc_info=True)
            self.stderr.write(f'Error processing evaluation data: {e}')
            return None, None

    def _research_mode_training_and_evaluation(self, training_data: pd.DataFrame, training_columns: List[str],
                                            evaluation_data: pd.DataFrame, true_labels: np.ndarray,
                                            output_paths: Dict[str, str],
                                            config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform research mode training and evaluation with separate datasets."""
        logger.info('Starting research mode training and evaluation...')
        self.stdout.write('Starting research mode training and evaluation...')
        
        # Get contamination range from config
        contamination_range = config.get('model', {}).get('contamination_range', [0.1])
        
        # Calculate actual contamination from evaluation data
        actual_contamination = np.sum(true_labels) / len(true_labels) if len(true_labels) > 0 else 0
        
        # Initialize research results
        research_results = {
            'research_date': datetime.now().isoformat(),
            'configuration': config,
            'dataset_info': {
                'training_sample_count': training_data.shape[0],
                'training_feature_count': training_data.shape[1],
                'training_feature_columns': training_columns,
                'evaluation_sample_count': evaluation_data.shape[0],
                'evaluation_feature_count': evaluation_data.shape[1],
                'evaluation_labeled_data_count': len(true_labels),
                'true_anomalies': np.sum(true_labels),
                'true_normal': len(true_labels) - np.sum(true_labels),
                'actual_contamination': actual_contamination
            },
            'contamination_analysis': {},
            'best_model': None,
            'recommendations': []
        }
        
        best_f1_score = -1
        best_contamination = None
        best_model = None
        
        # Test each contamination value
        for contamination in contamination_range:
            logger.info(f'Testing contamination={contamination}...')
            self.stdout.write(f'{"="*7}Testing contamination={contamination}... {"="*7}')
            
            try:
                # Train model with current contamination
                model_params = self._get_model_parameters(contamination, config)
                model = IsolationForest(**model_params)
                logger.info(f'Training model with contamination={contamination}...')
                model.fit(training_data)
                
                # Evaluate on evaluation dataset
                trial_results = self._evaluate_model_on_evaluation_data(
                    model, evaluation_data, training_columns, true_labels, contamination, config
                )
                
                research_results['contamination_analysis'][contamination] = trial_results
                
                f1 = trial_results['f1_score']
                
                # Track best performing model
                if f1 > best_f1_score:
                    best_f1_score = f1
                    best_contamination = contamination
                    best_model = model
                    logger.info(f'New best model found: contamination={contamination}, f1_score={f1:.4f}')
                
            except Exception as e:
                logger.error(f'Error testing contamination={contamination}: {e}', exc_info=True)
                self.stderr.write(f'Error testing contamination={contamination}: {e}')
        
        # Save best model and results
        # !! best model is defined as the model with the highest f1_score

        if best_model and best_contamination:
            best_results = research_results['contamination_analysis'][best_contamination]
            logger.info(f'Best contamination value: {best_contamination} (F1-score: {best_f1_score:.4f}, AUC-score: {best_results["auc_score"]:.4f})')
            self.stdout.write(f'Best contamination value: {best_contamination} (F1-score: {best_f1_score:.4f}, AUC-score: {best_results["auc_score"]:.4f})')
            
            # Save best model
            logger.info(f'Saving best model to {output_paths["model_path"]}')
            joblib.dump(best_model, output_paths['model_path'])
            
            # Save training columns
            logger.info(f'Saving training columns to {output_paths["columns_path"]}')
            joblib.dump(training_columns, output_paths['columns_path'])
            
            # Update research results with best model info
            best_results = research_results['contamination_analysis'][best_contamination]
            research_results['best_model'] = {
                'contamination': best_contamination,
                'f1_score': best_f1_score,
                'precision': best_results['precision'],
                'recall': best_results['recall'],
                'auc_score': best_results['auc_score'],
                'true_anomalies': best_results['true_anomalies'],
                'predicted_anomalies': best_results['predicted_anomalies'],
                'model_path': output_paths['model_path'],
                'columns_path': output_paths['columns_path']
            }

            # Generate and save ROC curve for the best model if enabled
            if config.get('output', {}).get('generate_roc_curve', True):
                roc_auc_score = self._generate_and_save_roc_curve(
                    true_labels=true_labels,
                    anomaly_scores=best_results['anomaly_scores'],
                    output_path=output_paths['roc_curve_path']
                )
                # Update best model with ROC AUC score (should match the calculated AUC score)
                research_results['best_model']['roc_auc_score'] = roc_auc_score

            # Add training summary
            research_results['training_summary'] = {
                'total_contamination_values_tested': len(contamination_range),
                'contamination_values_tested': contamination_range,
                'best_contamination': best_contamination,
                'best_f1_score': best_f1_score,
                'best_auc_score': best_results['auc_score'],
                'training_completed_at': datetime.now().isoformat(),
                'model_saved_to': output_paths['model_path'],
                'columns_saved_to': output_paths['columns_path'],
                'research_log_saved_to': output_paths['results_path']
            }
            
            # Save research results
            self._save_research_results(research_results, output_paths['results_path'])
            
            logger.info(f'Research results saved to {output_paths["results_path"]}')
            self.stdout.write(f'Research results saved to {output_paths["results_path"]}')
            
            return research_results
        
        else:
            logger.error('No valid models found during research')
            self.stderr.write('No valid models found during research')
            return None

    def _evaluate_model_on_evaluation_data(self, model, evaluation_data: pd.DataFrame, 
                                         training_columns: List[str], true_labels: np.ndarray,
                                         contamination: float, config: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a trained model on evaluation data."""
        logger.info(f'Evaluating model with contamination={contamination} on evaluation data...')
        
        try:
            # Prepare features for evaluation
            features_df = self._prepare_features_for_evaluation(evaluation_data, training_columns, config)
            if features_df is None:
                raise ValueError('Failed to prepare features for evaluation')
            
            # Get predictions and scores
            prediction_results = self._get_predictions_and_scores(model, features_df, contamination)
            if prediction_results is None:
                raise ValueError('Failed to get predictions and scores')
            
            predicted_labels, anomaly_scores, threshold = prediction_results
            
            # Calculate metrics
            metrics = self._calculate_evaluation_metrics(true_labels, predicted_labels)
            
            # Calculate AUC score
            auc_score = self._calculate_auc_score(true_labels, anomaly_scores)
            metrics['auc_score'] = auc_score
            
            # Add prediction details
            trial_results = {
                'contamination': contamination,
                'threshold': threshold,
                'predicted_anomalies': np.sum(predicted_labels),
                'predicted_normal': len(predicted_labels) - np.sum(predicted_labels),
                'true_anomalies': np.sum(true_labels),
                'true_normal': len(true_labels) - np.sum(true_labels),
                'anomaly_scores': anomaly_scores,
                **metrics
            }
            
            logger.info(f'Evaluation results for contamination={contamination}:')
            logger.info(f'  - Precision: {metrics["precision"]:.4f}')
            logger.info(f'  - Recall: {metrics["recall"]:.4f}')
            logger.info(f'  - F1-Score: {metrics["f1_score"]:.4f}')
            logger.info(f'  - AUC Score: {metrics["auc_score"]:.4f}')
            logger.info(f'  - Predicted anomalies: {trial_results["predicted_anomalies"]}')
            
            return trial_results
            
        except Exception as e:
            logger.error(f'Error evaluating model: {e}', exc_info=True)
            raise

    def _prepare_features_for_evaluation(self, evaluation_data: pd.DataFrame, training_columns: List[str],
                                       config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Prepare features for evaluation, handling column mismatches."""
        features_df = evaluation_data.copy()
        
        # Get advanced configuration
        advanced_config = config.get('advanced', {})
        handle_missing_columns = advanced_config.get('handle_missing_columns', True)
        missing_column_default = advanced_config.get('missing_column_default', 0)
        remove_extra_columns = advanced_config.get('remove_extra_columns', True)
        
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
        
        logger.info(f'Features shape for evaluation: {features_df.shape}')
        logger.info(f'Final feature columns: {list(features_df.columns)}')
        
        return features_df

    def _get_predictions_and_scores(self, model, features_df: pd.DataFrame, contamination: float) -> Optional[Tuple[np.ndarray, np.ndarray, float]]:
        """Get predictions and anomaly scores from the trained model."""
        try:
            # Get raw anomaly scores (lower score means more anomalous)
            anomaly_scores = model.score_samples(features_df)
            
            # Calculate threshold based on contamination rate
            threshold = np.percentile(anomaly_scores, contamination * 100)
            
            # Classify samples as anomalies (1) or normal (0)
            predicted_labels = (anomaly_scores <= threshold).astype(int)
            
            logger.info(f'Predicted anomalies: {np.sum(predicted_labels)} out of {len(predicted_labels)}')
            logger.info(f'Contamination rate: {contamination:.4f}')
            logger.info(f'Threshold: {threshold:.4f}')
            
            return predicted_labels, anomaly_scores, threshold
            
        except Exception as e:
            logger.error(f'Error getting predictions and scores: {e}', exc_info=True)
            return None

    def _calculate_evaluation_metrics(self, true_labels: np.ndarray, predicted_labels: np.ndarray) -> Dict[str, Any]:
        """Calculate comprehensive evaluation metrics."""
        # Handle case where no anomalies are predicted
        if np.sum(predicted_labels) == 0:
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
        
        return {
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'accuracy': float(accuracy),
            'specificity': float(specificity),
            'balanced_accuracy': float(balanced_accuracy),
            'confusion_matrix': cm.tolist(),
            'true_positives': int(tp),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_negatives': int(tn)
        }

    def _generate_and_save_roc_curve(self, true_labels: np.ndarray, anomaly_scores: np.ndarray, output_path: str) -> float:
        """Generate and save the ROC curve. Returns the AUC score."""
        try:
            # The Isolation Forest scores are inverted (lower is more anomalous),
            # so we negate them to treat higher scores as more anomalous for ROC calculation.
            fpr, tpr, _ = roc_curve(true_labels, -anomaly_scores)
            roc_auc = auc(fpr, tpr)

            plt.figure(figsize=(10, 8))
            plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
            plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')
            plt.title('Receiver Operating Characteristic (ROC) Curve')
            plt.legend(loc="lower right")
            
            # Save the plot
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f'ROC curve saved to {output_path}')
            logger.info(f'AUC score: {roc_auc:.4f}')
            self.stdout.write(f'ROC curve saved to {output_path}')
            self.stdout.write(f'AUC score: {roc_auc:.4f}')

            return float(roc_auc)

        except Exception as e:
            logger.error(f'Failed to generate or save ROC curve: {e}', exc_info=True)
            self.stderr.write(f'Failed to generate or save ROC curve: {e}')
            return 0.0

    def _calculate_auc_score(self, true_labels: np.ndarray, anomaly_scores: np.ndarray) -> float:
        """Calculate AUC score from true labels and anomaly scores."""
        try:
            # The Isolation Forest scores are inverted (lower is more anomalous),
            # so we negate them to treat higher scores as more anomalous for ROC calculation.
            fpr, tpr, _ = roc_curve(true_labels, -anomaly_scores)
            roc_auc = auc(fpr, tpr)
            return float(roc_auc)
        except Exception as e:
            logger.error(f'Failed to calculate AUC score: {e}', exc_info=True)
            return 0.0

    def _get_model_parameters(self, contamination: Union[float, str], config: Dict[str, Any]) -> Dict[str, Any]:
        """Get model parameters from configuration."""
        model_config = config.get('model', {})
        
        params = {
            'contamination': contamination,
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

    def _save_research_results(self, research_results: Dict[str, Any], research_log_path: str):
        """Save research results to JSON file."""
        try:
            # Convert numpy types for JSON serialization
            serializable_results = self._convert_numpy_types(research_results)
            serializable_results['research_timestamp'] = datetime.now().isoformat()
            
            # Read existing results and prepend new result
            existing_results = self._read_existing_results(research_log_path)
            all_results = [serializable_results] + existing_results
            
            # Write results
            with open(research_log_path, 'w') as f:
                json.dump(all_results, f, indent=2)
            
            logger.info(f'Research results appended to top of {research_log_path}')
            self.stdout.write(f'Research results appended to top of {research_log_path}')
            
        except Exception as e:
            logger.error(f'Error saving research results: {e}', exc_info=True)
            self.stderr.write(f'Error saving research results: {e}')

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
        """Read existing research results from file."""
        if not os.path.exists(log_path):
            return []
        
        try:
            with open(log_path, 'r') as f:
                existing_results = json.load(f)
            return existing_results if isinstance(existing_results, list) else [existing_results]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _output_results(self, research_results: Dict[str, Any], config: Dict[str, Any]):
        """Output research results in specified format."""
        evaluation_config = config.get('evaluation', {})
        output_format = evaluation_config.get('output_format', 'both')
        
        if output_format in ['json', 'both']:
            # Results already saved in _save_research_results
            pass
        
        if output_format in ['console', 'both']:
            self._print_research_results(research_results, config)

    def _print_research_results(self, research_results: Dict[str, Any], config: Dict[str, Any]):
        """Print research results to console."""
        if not research_results:
            return
        
        self.stdout.write('\n' + '='*80)
        self.stdout.write('RESEARCH MODEL TRAINING AND EVALUATION RESULTS')
        self.stdout.write('='*80)
        
        # Dataset information
        dataset_info = research_results.get('dataset_info', {})
        self.stdout.write(f'\nDataset Information:')
        self.stdout.write(f'  - Training samples: {dataset_info.get("training_sample_count", "N/A")}')
        self.stdout.write(f'  - Training features: {dataset_info.get("training_feature_count", "N/A")}')
        self.stdout.write(f'  - Evaluation samples: {dataset_info.get("evaluation_sample_count", "N/A")}')
        self.stdout.write(f'  - Evaluation features: {dataset_info.get("evaluation_feature_count", "N/A")}')
        self.stdout.write(f'  - True anomalies: {dataset_info.get("true_anomalies", "N/A")}')
        self.stdout.write(f'  - True normal: {dataset_info.get("true_normal", "N/A")}')
        self.stdout.write(f'  - Actual contamination: {dataset_info.get("actual_contamination", "N/A"):.4f}')
        
        # Best model information
        best_model = research_results.get('best_model', {})
        if best_model:
            self.stdout.write(f'\nBest Model Information:')
            self.stdout.write(f'  - Best contamination: {best_model.get("contamination", "N/A")}')
            self.stdout.write(f'  - Best F1-Score: {best_model.get("f1_score", "N/A"):.4f}')
            self.stdout.write(f'  - Best AUC-Score: {best_model.get("auc_score", "N/A"):.4f}')
            self.stdout.write(f'  - Best Precision: {best_model.get("precision", "N/A"):.4f}')
            self.stdout.write(f'  - Best Recall: {best_model.get("recall", "N/A"):.4f}')
            self.stdout.write(f'  - Predicted anomalies: {best_model.get("predicted_anomalies", "N/A")}')
            self.stdout.write(f'  - Model saved to: {best_model.get("model_path", "N/A")}')
        
        # Contamination analysis summary
        contamination_analysis = research_results.get('contamination_analysis', {})
        if contamination_analysis:
            self.stdout.write(f'\nContamination Analysis Summary:')
            for contamination, results in contamination_analysis.items():
                self.stdout.write(f'  - Contamination {contamination}:')
                self.stdout.write(f'    F1-Score: {results.get("f1_score", 0):.4f}')
                self.stdout.write(f'    AUC-Score: {results.get("auc_score", 0):.4f}')
                self.stdout.write(f'    Precision: {results.get("precision", 0):.4f}')
                self.stdout.write(f'    Recall: {results.get("recall", 0):.4f}')
                self.stdout.write(f'    Predicted anomalies: {results.get("predicted_anomalies", 0)}')
        
        # Training summary
        training_summary = research_results.get('training_summary', {})
        if training_summary:
            self.stdout.write(f'\nTraining Summary:')
            self.stdout.write(f'  - Contamination values tested: {training_summary.get("total_contamination_values_tested", "N/A")}')
            self.stdout.write(f'  - Values tested: {training_summary.get("contamination_values_tested", "N/A")}')
            self.stdout.write(f'  - Best contamination: {training_summary.get("best_contamination", "N/A")}')
            self.stdout.write(f'  - Best F1-Score: {training_summary.get("best_f1_score", "N/A"):.4f}')
            self.stdout.write(f'  - Best AUC-Score: {training_summary.get("best_auc_score", "N/A"):.4f}')
            self.stdout.write(f'  - Research log saved to: {training_summary.get("research_log_saved_to", "N/A")}')
        
        self.stdout.write('\n' + '='*80) 