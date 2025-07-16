"""
Management command to train the Isolation Forest model with research evaluation.
"""
import os
import joblib
import json
import logging
import yaml
from datetime import datetime
from typing import Union, List, Tuple
from django.core.management.base import BaseCommand
from django.conf import settings
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, precision_recall_curve, precision_score, recall_score, f1_score, confusion_matrix
import numpy as np
import pandas as pd

from apps.ai_analytics.services import preprocessing, feature_engineering

# Define default paths to store the trained model
DEFAULT_MODEL_DIR = os.path.join(settings.BASE_DIR, 'apps', 'ai_analytics', 'model_files')
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, 'isolation_forest.joblib')
DEFAULT_COLUMNS_PATH = os.path.join(DEFAULT_MODEL_DIR, 'training_columns.joblib')
DEFAULT_RESEARCH_LOG_PATH = os.path.join(DEFAULT_MODEL_DIR, 'research_log.json')

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Trains the Isolation Forest model for anomaly detection with research-grade evaluation.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            required=True,
            help='Path to YAML configuration file'
        )

    def handle(self, *args, **options):
        logger.info('Starting model training...')
        self.stdout.write('Starting model training...')

        # Load configuration
        config_path = options['config']
        self.config_path = config_path  # Store for use in _get_model_parameters
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

        # Get output paths from configuration or use defaults
        self.model_dir, self.model_path, self.columns_path, self.research_log_path = self._get_output_paths(config)
        
        # Ensure all required directories exist
        self._ensure_directories_exist()
        logger.info(f'All output directories ensured')

        # 1. Get and preprocess data
        logger.info('Fetching and preprocessing transaction data...')
        self.stdout.write('Fetching and preprocessing transaction data...')
        
        # Step 1: Get raw data and clean it
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
                logger.warning('No transaction data found to train the model.')
                self.stdout.write('No transaction data found to train the model.')
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

        
        # Step 2: Engineer features
        logger.info('Starting feature engineering...')

        try:
            df_processed, training_columns = feature_engineering.create_model_features(cleaned_df)
            logger.info(f'Feature engineering completed. Processed data shape: {df_processed.shape}')
            logger.info(f'Training columns: {training_columns}')
        except Exception as e:
            logger.error(f'Error during feature engineering: {e}', exc_info=True)
            self.stderr.write(f'Error during feature engineering: {e}')
            return

        logger.info(f'Successfully processed {df_processed.shape[0]} transactions with {df_processed.shape[1]} features.')
        self.stdout.write(f'Successfully processed {df_processed.shape[0]} transactions with {df_processed.shape[1]} features.')

        # Determine training mode
        research_mode = config.get('training', {}).get('research_mode', False)
        
        if research_mode:
            logger.info('Starting research mode training...')
            contamination_range = config.get('model', {}).get('contamination_range', [0.01, 0.05, 0.10, 0.15])
            self._research_mode_training(df_processed, training_columns, contamination_range)
        else:
            # Standard training
            logger.info('Starting standard training mode...')
            contamination = config.get('model', {}).get('contamination', 'auto')
            self._standard_training(df_processed, training_columns, contamination)

    def _prepare_training_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Union[np.ndarray, None]]:
        """
        Safely prepare training data by extracting labels and dropping 'is_anomaly' column.
        
        Args:
            df: DataFrame that may contain 'is_anomaly' column
            
        Returns:
            Tuple of (training_data, true_labels) where:
            - training_data: DataFrame with 'is_anomaly' column removed
            - true_labels: numpy array of binary labels (1 for anomaly, 0 for normal) or None
        """
        df_copy = df.copy()
        true_labels = None
        
        # Check if 'is_anomaly' column exists
        if 'is_anomaly' in df_copy.columns:
            logger.info("'is_anomaly' column found in dataset")
            
            # Extract true labels before dropping the column
            true_labels_raw = df_copy['is_anomaly'].values
            # Convert to binary: 1 for anomaly, 0 for normal
            true_labels = (true_labels_raw == 1).astype(int)
            
            # Drop 'is_anomaly' column to prevent data leakage
            training_data = df_copy.drop('is_anomaly', axis=1)
            logger.info(f"Dropped 'is_anomaly' column. Training data shape: {training_data.shape}")
            
            # Log label distribution
            if true_labels is not None:
                label_counts = np.bincount(true_labels)
                logger.info(f"True labels distribution: Normal={label_counts[0]}, Anomalies={label_counts[1] if len(label_counts) > 1 else 0}")
        else:
            logger.info("'is_anomaly' column not found in dataset - proceeding with  training")
            training_data = df_copy
            true_labels = None
        
        return training_data, true_labels

    def _validate_config(self, config: dict) -> bool:
        """Validate the configuration structure."""
        required_sections = ['model', 'training']
        
        for section in required_sections:
            if section not in config:
                logger.error(f'Missing required configuration section: {section}')
                self.stderr.write(f'Missing required configuration section: {section}')
                return False
        
        # Validate model configuration
        model_config = config.get('model', {})
        if 'contamination' not in model_config and 'contamination_range' not in model_config:
            logger.error('Either contamination or contamination_range must be specified in model configuration')
            self.stderr.write('Either contamination or contamination_range must be specified in model configuration')
            return False
        
        return True

    def _get_output_paths(self, config: dict) -> Tuple[str, str, str, str]:
        """
        Get output paths from configuration or use defaults.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Tuple of (model_dir, model_path, columns_path, research_log_path)
        """
        # Get output configuration section
        output_config = config.get('output', {})
        
        # Get model directory (can be relative or absolute path)
        model_dir = output_config.get('model_dir', DEFAULT_MODEL_DIR)
        if not os.path.isabs(model_dir):
            # If relative path, make it relative to BASE_DIR
            model_dir = os.path.join(settings.BASE_DIR, model_dir)
        
        # Get individual file paths (can be relative to model_dir or absolute)
        model_filename = output_config.get('model_filename', 'isolation_forest.joblib')
        columns_filename = output_config.get('columns_filename', 'training_columns.joblib')
        research_log_filename = output_config.get('research_log_filename', 'research_log.json')
        
        # Construct full paths
        model_path = output_config.get('model_path')
        if model_path:
            if not os.path.isabs(model_path):
                model_path = os.path.join(settings.BASE_DIR, model_path)
        else:
            model_path = os.path.join(model_dir, model_filename)
        
        columns_path = output_config.get('columns_path')
        if columns_path:
            if not os.path.isabs(columns_path):
                columns_path = os.path.join(settings.BASE_DIR, columns_path)
        else:
            columns_path = os.path.join(model_dir, columns_filename)
        
        research_log_path = output_config.get('research_log_path')
        if research_log_path:
            if not os.path.isabs(research_log_path):
                research_log_path = os.path.join(settings.BASE_DIR, research_log_path)
        else:
            research_log_path = os.path.join(model_dir, research_log_filename)
        
        logger.info(f'Output paths configured:')
        logger.info(f'  Model directory: {model_dir}')
        logger.info(f'  Model file: {model_path}')
        logger.info(f'  Columns file: {columns_path}')
        logger.info(f'  Research log: {research_log_path}')
        
        return model_dir, model_path, columns_path, research_log_path

    def _validate_output_paths(self, model_dir: str, model_path: str, columns_path: str, research_log_path: str):
        """
        Validate that output paths are valid and accessible.
        
        Args:
            model_dir: Directory for model files
            model_path: Path to model file
            columns_path: Path to columns file
            research_log_path: Path to research log file
        """
        paths_to_check = [model_dir, os.path.dirname(model_path), 
                         os.path.dirname(columns_path), os.path.dirname(research_log_path)]
        
        for path in paths_to_check:
            if path and not os.path.exists(path):
                logger.info(f'Directory will be created: {path}')
            elif path:
                logger.info(f'Directory already exists: {path}')
        
        # Check if we can write to the directories
        for path in paths_to_check:
            if path:
                try:
                    # Try to create a temporary file to test write permissions
                    test_file = os.path.join(path, '.write_test')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    logger.info(f'Write permissions confirmed for: {path}')
                except Exception as e:
                    logger.warning(f'Write permissions issue for {path}: {e}')
                    self.stderr.write(f'Warning: Write permissions issue for {path}: {e}')

    def _ensure_directories_exist(self):
        """
        Ensure all required directories exist for output files.
        Creates parent directories as needed.
        """
        directories_to_create = set()
        
        # Add directories for all output files
        directories_to_create.add(os.path.dirname(self.model_path))
        directories_to_create.add(os.path.dirname(self.columns_path))
        directories_to_create.add(os.path.dirname(self.research_log_path))
        
        # Create each directory
        for directory in directories_to_create:
            if directory and directory != '.':  # Skip empty directory names and current directory
                try:
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f'Ensured directory exists: {directory}')
                    self.stdout.write(f'Created directory: {directory}')
                except Exception as e:
                    error_msg = f'Failed to create directory {directory}: {e}'
                    logger.error(error_msg)
                    self.stderr.write(error_msg)
                    raise

    def _research_mode_training(self, df_processed, training_columns, contamination_range):
        """Research mode with cross-validation and multiple contamination values."""
        logger.info('Running research mode with cross-validation...')
        self.stdout.write('Running research mode with cross-validation...')
        
        try:
            # Prepare training data and extract labels
            training_data, true_labels = self._prepare_training_data(df_processed) #drops 'is_anomaly' column
            
            # Validate that we have labels for research mode
            if true_labels is None:
                logger.error("Research mode requires labeled data with 'is_anomaly' column")
                self.stderr.write("Research mode requires labeled data with 'is_anomaly' column")
                return
            
            logger.info(f'Training data shape: {training_data.shape}')
            logger.info(f'True labels shape: {true_labels.shape}')
            logger.info(f'is_anomaly values (first 10): {true_labels[:10]}...')

        except Exception as e:
            logger.error(f'Error preparing training data: {e}', exc_info=True)
            self.stderr.write(f'Error preparing training data: {e}')
            return
        
        # Load full configuration for inclusion in results
        try:
            with open(self.config_path, 'r') as f:
                full_config = yaml.safe_load(f)
        except Exception as e:
            logger.warning(f'Could not load full configuration for results: {e}')
            full_config = {}
        
        # Initialize research results dictionary
        research_results = {
            'training_date': datetime.now().isoformat(),
            'configuration': full_config,
            'dataset_info': {
                'sample_count': training_data.shape[0],
                'feature_count': training_data.shape[1],
                'feature_columns': training_columns,
                'labeled_data_count': len(true_labels),
                'true_anomalies': np.sum(true_labels),
                'true_normal': len(true_labels) - np.sum(true_labels)
            },
            'contamination_analysis': {},
            'best_model': None,
            'recommendations': []
        }
        
        logger.info(f'Research results initialized. Dataset info: {research_results["dataset_info"]}')

        best_f1_score = -1
        best_contamination = None

        for contamination in contamination_range:
            logger.info(f'Testing contamination={contamination}...')
            self.stdout.write(f'{"="*7}Testing contamination={contamination}... {"="*7}')
            
            # Get model parameters from config
            model_params = self._get_model_parameters(contamination)
            
            model = IsolationForest(**model_params)
            logger.info(f'IsolationForest model created with contamination={contamination}')
            
            try:
                # Get anomaly predictions for evaluation
                logger.info(f'Fitting and predicting with contamination={contamination}...')
                scores = model.fit_predict(training_data)
                # returns an array where:
                # -1 indicates an anomaly (outlier)
                # 1 indicates normal data (inlier)

                # Convert scores to binary predictions: -1 (anomaly) -> 1, 1 (normal) -> 0
                predicted_labels = (scores == -1).astype(int) #  returns a new numpy.ndarray filled with True or False values -> int (1 or 0)
                logger.info(f'Predicted anomalies: {np.sum(predicted_labels)} out of {len(predicted_labels)}')
                
                # Calculate metrics using true labels
                
                # Handle case where no anomalies are predicted
                if np.sum(predicted_labels) == 0:
                    logger.warning(f'No anomalies predicted for contamination={contamination}')
                    precision = 0.0
                    recall = 0.0
                    f1 = 0.0
                else:
                    precision = precision_score(true_labels, predicted_labels, zero_division='warn')
                    # zero_division='warn' is used to handle the case where there are no anomalies predicted.
                    # It sets the precision to 0.0 in such cases.
                    # This is useful because precision is undefined when there are no predicted anomalies.
                    
                    recall = recall_score(true_labels, predicted_labels, zero_division='warn')

                    f1 = f1_score(true_labels, predicted_labels, zero_division='warn')
                    logger.info(f'Metrics for contamination={contamination}: precision={precision:.4f}, recall={recall:.4f}, f1={f1:.4f}')
                
                # Calculate confusion matrix
                cm = confusion_matrix(true_labels, predicted_labels)
                logger.info(f'Confusion matrix for contamination={contamination}: {cm.tolist()}')
                
                # Interpret confusion matrix correctly:
                # For labels [0, 1] where 0=normal, 1=anomaly:
                # cm[0,0] = True Negatives (TN): predicted normal, actually normal
                # cm[0,1] = False Positives (FP): predicted anomaly, actually normal  
                # cm[1,0] = False Negatives (FN): predicted normal, actually anomaly
                # cm[1,1] = True Positives (TP): predicted anomaly, actually anomaly
                
                # Extract confusion matrix values safely
                if cm.shape == (2, 2):
                    tn, fp, fn, tp = cm[0,0], cm[0,1], cm[1,0], cm[1,1]
                else:
                    # Handle edge cases where confusion matrix might not be 2x2
                    tn = cm[0,0] if cm.shape[0] > 0 and cm.shape[1] > 0 else 0
                    fp = cm[0,1] if cm.shape[0] > 0 and cm.shape[1] > 1 else 0
                    fn = cm[1,0] if cm.shape[0] > 1 and cm.shape[1] > 0 else 0
                    tp = cm[1,1] if cm.shape[0] > 1 and cm.shape[1] > 1 else 0
                
                # Store results
                research_results['contamination_analysis'][contamination] = {
                    'precision': precision,
                    'recall': recall,
                    'f1_score': f1,
                    'predicted_anomalies': np.sum(predicted_labels),
                    'predicted_normal': len(predicted_labels) - np.sum(predicted_labels),
                    'true_anomalies': np.sum(true_labels),
                    'true_normal': len(true_labels) - np.sum(true_labels),
                    'confusion_matrix': cm.tolist(),
                    'confusion_matrix_interpreted': {
                        'true_negatives': int(tn),
                        'false_positives': int(fp), 
                        'false_negatives': int(fn),
                        'true_positives': int(tp)
                    },
                    'model_config': model_params
                }
                
                # Log detailed anomaly information with correct interpretation
                logger.info(f'Contamination {contamination} Results:')
                logger.info(f'  - True anomalies: {np.sum(true_labels)}')
                logger.info(f'  - Predicted anomalies: {np.sum(predicted_labels)}')
                logger.info(f'  - True positives (TP): {tp} (predicted anomaly, actually anomaly)')
                logger.info(f'  - False positives (FP): {fp} (predicted anomaly, actually normal)')
                logger.info(f'  - False negatives (FN): {fn} (predicted normal, actually anomaly)')
                logger.info(f'  - True negatives (TN): {tn} (predicted normal, actually normal)')
                logger.info(f'  - Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}')
                
                # Verify confusion matrix interpretation
                logger.info(f'  - Verification: TP+FN={tp+fn} (should equal true anomalies: {np.sum(true_labels)})')
                logger.info(f'  - Verification: FP+TN={fp+tn} (should equal true normals: {len(true_labels)-np.sum(true_labels)})')
                
                # Track best performing model based on F1-score
                if f1 > best_f1_score:
                    best_f1_score = f1
                    best_contamination = contamination
                    logger.info(f'New best model found: contamination={contamination}, f1_score={f1:.4f}')
                    
            except Exception as e:
                logger.error(f'Error testing contamination={contamination}: {e}', exc_info=True)
                self.stderr.write(f'Error testing contamination={contamination}: {e}')

        # Train final model with best contamination
        if best_contamination:
            logger.info(f'Best contamination value: {best_contamination} (F1-score: {best_f1_score:.4f})')
            self.stdout.write(f'Best contamination value: {best_contamination} (F1-score: {best_f1_score:.4f})')
            
            # Log summary of best model performance
            best_results = research_results['contamination_analysis'][best_contamination]
            logger.info('Best Model Summary:')
            logger.info(f'  - True anomalies in dataset: {best_results["true_anomalies"]}')
            logger.info(f'  - Predicted anomalies: {best_results["predicted_anomalies"]}')
            logger.info(f'  - Precision: {best_results["precision"]:.4f}')
            logger.info(f'  - Recall: {best_results["recall"]:.4f}')
            logger.info(f'  - F1-Score: {best_results["f1_score"]:.4f}')
            
            # Get model parameters for best contamination
            final_model_params = self._get_model_parameters(best_contamination)
            final_model = IsolationForest(**final_model_params)
            logger.info('Training final model with best contamination...')
            final_model.fit(training_data)
            
            # Store final model parameters in results
            research_results['final_model_parameters'] = final_model_params
            
            # Save model and research results
            logger.info(f'Saving final model to {self.model_path}')
            joblib.dump(final_model, self.model_path)
            logger.info(f'Saving training columns to {self.columns_path}')
            joblib.dump(training_columns, self.columns_path)
            
            research_results['best_model'] = {
                'contamination': best_contamination,
                'f1_score': best_f1_score,
                'precision': research_results['contamination_analysis'][best_contamination]['precision'],
                'recall': research_results['contamination_analysis'][best_contamination]['recall'],
                'true_anomalies': research_results['contamination_analysis'][best_contamination]['true_anomalies'],
                'predicted_anomalies': research_results['contamination_analysis'][best_contamination]['predicted_anomalies']
            }
            
            # Add training summary
            research_results['training_summary'] = {
                'total_contamination_values_tested': len(contamination_range),
                'contamination_values_tested': contamination_range,
                'best_contamination': best_contamination,
                'best_f1_score': best_f1_score,
                'training_completed_at': datetime.now().isoformat(),
                'model_saved_to': self.model_path,
                'columns_saved_to': self.columns_path,
                'research_log_saved_to': self.research_log_path
            }
            
            # Save research log using the same mechanism as evaluate_model
            logger.info(f'Saving research results to {self.research_log_path}')
            self._save_training_results(research_results, self.research_log_path)
            
            logger.info(f'Research results saved to {self.research_log_path}')
            self.stdout.write(f'Research results saved to {self.research_log_path}')
            
            # Log final summary
            logger.info('Research Mode Complete - Final Summary:')
            logger.info(f'  - Dataset size: {research_results["dataset_info"]["sample_count"]} transactions')
            logger.info(f'  - True anomalies in dataset: {research_results["dataset_info"]["true_anomalies"]}')
            logger.info(f'  - Best contamination: {best_contamination}')
            logger.info(f'  - Best F1-Score: {best_f1_score:.4f}')
            logger.info(f'  - Best Precision: {research_results["best_model"]["precision"]:.4f}')
            logger.info(f'  - Best Recall: {research_results["best_model"]["recall"]:.4f}')
            
            logger.info('Research mode training complete.')
            self.stdout.write('Research mode training complete.')

    def _standard_training(self, df_processed, training_columns, contamination):
        """Standard training mode."""
        logger.info('Training Isolation Forest model...')
        self.stdout.write('Training Isolation Forest model...')
        
        try:
            # Prepare training data (drops 'is_anomaly' if present)
            training_data, _ = self._prepare_training_data(df_processed)
            logger.info(f'Training data prepared. Shape: {training_data.shape}')
            
        except Exception as e:
            logger.error(f'Error preparing training data: {e}', exc_info=True)
            self.stderr.write(f'Error preparing training data: {e}')
            return
        
        # Get model parameters from config
        model_params = self._get_model_parameters(contamination)
        
        model = IsolationForest(**model_params)
        logger.info(f'IsolationForest model created with contamination={contamination}')

        logger.info('Fitting model to processed data...')
        model.fit(training_data)
        logger.info('Model training complete.')
        self.stdout.write('Model training complete.')

        # Save model and training columns
        logger.info(f'Saving model to {self.model_path}')
        self.stdout.write(f'Saving model to {self.model_path}')
        joblib.dump(model, self.model_path)
        
        logger.info(f'Saving training columns to {self.columns_path}')
        self.stdout.write(f'Saving training columns to {self.columns_path}')
        joblib.dump(training_columns, self.columns_path)
        
        # Save training results for standard mode
        try:
            # Load full configuration for inclusion in results
            with open(self.config_path, 'r') as f:
                full_config = yaml.safe_load(f)
        except Exception as e:
            logger.warning(f'Could not load full configuration for results: {e}')
            full_config = {}
        
        # Create standard training results
        standard_results = {
            'training_date': datetime.now().isoformat(),
            'training_mode': 'standard',
            'configuration': full_config,
            'dataset_info': {
                'sample_count': training_data.shape[0],
                'feature_count': training_data.shape[1],
                'feature_columns': training_columns
            },
            'model_parameters': model_params,
            'training_summary': {
                'contamination_used': contamination,
                'training_completed_at': datetime.now().isoformat(),
                'model_saved_to': self.model_path,
                'columns_saved_to': self.columns_path
            }
        }
        
        # Save formatted results to research log using the same mechanism as evaluate_model
        logger.info(f'Saving standard training results to {self.research_log_path}')
        self._save_training_results(standard_results, self.research_log_path)

        logger.info('Successfully trained and saved the model and column list.')
        self.stdout.write('Successfully trained and saved the model and column list.')

    def _get_model_parameters(self, contamination: Union[float, str]) -> dict:
        """Get model parameters from configuration."""
        # Load config to get model parameters
        config_path = self.config_path if hasattr(self, 'config_path') else None
        if config_path:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        else:
            # Fallback to default parameters
            config = {'model': {}}
        
        model_config = config.get('model', {})
        
        # Base parameters
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

    def _save_training_results(self, training_results, training_log_path):
        """Save training results to JSON file, appending to top."""
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
            
            serializable_results = convert_numpy_types(training_results)
            
            # Read existing results if file exists
            existing_results = []
            if os.path.exists(training_log_path):
                try:
                    with open(training_log_path, 'r') as f:
                        existing_results = json.load(f)
                    if not isinstance(existing_results, list):
                        existing_results = [existing_results]
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_results = []
            
            # Add timestamp to new result
            serializable_results['training_timestamp'] = datetime.now().isoformat()
            
            # Prepend new result to existing results
            all_results = [serializable_results] + existing_results
            
            # Write all results back to file
            with open(training_log_path, 'w') as f:
                json.dump(all_results, f, indent=2)
            
            logger.info(f'Training results appended to top of {training_log_path}')
            self.stdout.write(f'Training results appended to top of {training_log_path}')
            
        except Exception as e:
            logger.error(f'Error saving training results: {e}', exc_info=True)
            self.stderr.write(f'Error saving training results: {e}') 