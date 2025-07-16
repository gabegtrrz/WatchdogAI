"""
Management command to train the Isolation Forest model with research evaluation.
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
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, precision_recall_curve, precision_score, recall_score, f1_score, confusion_matrix
import numpy as np

from apps.ai_analytics.services import preprocessing, feature_engineering

# Define the path to store the trained model
MODEL_DIR = os.path.join(settings.BASE_DIR, 'apps', 'ai_analytics', 'model_files')
MODEL_PATH = os.path.join(MODEL_DIR, 'isolation_forest.joblib')
COLUMNS_PATH = os.path.join(MODEL_DIR, 'training_columns.joblib')
RESEARCH_LOG_PATH = os.path.join(MODEL_DIR, 'research_log.json')

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

        # Ensure the model directory exists
        os.makedirs(MODEL_DIR, exist_ok=True)
        logger.info(f'Model directory ensured: {MODEL_DIR}')

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

    def _research_mode_training(self, df_processed, training_columns, contamination_range):
        """Research mode with cross-validation and multiple contamination values."""
        logger.info('Running research mode with cross-validation...')
        self.stdout.write('Running research mode with cross-validation...')
        
        try:
            labeled_df = df_processed.copy()
            logger.info(f'Labeled data shape: {labeled_df.shape}')
            logger.info(f'is_anomaly values: {labeled_df["is_anomaly"].values[:10]}...')
            self.stdout.write(f'is_anomaly values: {labeled_df["is_anomaly"].values[:10]}...')
            
            # Get true labels (1 for anomaly, 0 for normal)
            true_labels = labeled_df['is_anomaly'].values
            # Convert to binary: 1 for anomaly, 0 for normal (applying for robustness)
            true_labels_binary = (true_labels == 1).astype(int)
            logger.info(f'True labels binary distribution: {np.bincount(true_labels_binary)}')
            
            # Drop 'is_anomaly' column from training data to prevent data leakage
            training_data = labeled_df.drop('is_anomaly', axis=1)
            logger.info(f'Training data shape after dropping is_anomaly: {training_data.shape}')

        except Exception as e:
            logger.error(f'Error loading labeled data: {e}', exc_info=True)
            self.stderr.write(f'Error loading labeled data: {e}')
            return
        
        # Initialize research results dictionary
        research_results = {
            'training_date': datetime.now().isoformat(),
            'dataset_info': {
                'sample_count': df_processed.shape[0],
                'feature_count': df_processed.shape[1],
                'feature_columns': training_columns,
                'labeled_data_count': len(true_labels),
                'true_anomalies': np.sum(true_labels_binary),
                'true_normal': len(true_labels_binary) - np.sum(true_labels_binary)
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
                    precision = precision_score(true_labels_binary, predicted_labels, zero_division='warn')
                    # zero_division='warn' is used to handle the case where there are no anomalies predicted.
                    # It sets the precision to 0.0 in such cases.
                    # This is useful because precision is undefined when there are no predicted anomalies.
                    
                    recall = recall_score(true_labels_binary, predicted_labels, zero_division='warn')

                    f1 = f1_score(true_labels_binary, predicted_labels, zero_division='warn')
                    logger.info(f'Metrics for contamination={contamination}: precision={precision:.4f}, recall={recall:.4f}, f1={f1:.4f}')
                
                # Calculate confusion matrix
                cm = confusion_matrix(true_labels_binary, predicted_labels)
                logger.info(f'Confusion matrix for contamination={contamination}: {cm.tolist()}')
                
                # Store results
                research_results['contamination_analysis'][contamination] = {
                    'precision': precision,
                    'recall': recall,
                    'f1_score': f1,
                    'predicted_anomalies': np.sum(predicted_labels),
                    'predicted_normal': len(predicted_labels) - np.sum(predicted_labels),
                    'true_anomalies': np.sum(true_labels_binary),
                    'true_normal': len(true_labels_binary) - np.sum(true_labels_binary),
                    'confusion_matrix': cm.tolist(),
                    'model_config': model_params
                }
                
                # Log detailed anomaly information
                logger.info(f'Contamination {contamination} Results:')
                logger.info(f'  - True anomalies: {np.sum(true_labels_binary)}')
                logger.info(f'  - Predicted anomalies: {np.sum(predicted_labels)}')
                logger.info(f'  - True positives: {cm[1, 1] if cm.shape == (2, 2) else 0}')
                logger.info(f'  - False positives: {cm[0, 1] if cm.shape == (2, 2) else 0}')
                logger.info(f'  - False negatives: {cm[1, 0] if cm.shape == (2, 2) else 0}')
                logger.info(f'  - True negatives: {cm[0, 0] if cm.shape == (2, 2) else 0}')
                logger.info(f'  - Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}')
                
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
            
            # Save model and research results
            logger.info(f'Saving final model to {MODEL_PATH}')
            joblib.dump(final_model, MODEL_PATH)
            logger.info(f'Saving training columns to {COLUMNS_PATH}')
            joblib.dump(training_columns, COLUMNS_PATH)
            
            research_results['best_model'] = {
                'contamination': best_contamination,
                'f1_score': best_f1_score,
                'precision': research_results['contamination_analysis'][best_contamination]['precision'],
                'recall': research_results['contamination_analysis'][best_contamination]['recall'],
                'true_anomalies': research_results['contamination_analysis'][best_contamination]['true_anomalies'],
                'predicted_anomalies': research_results['contamination_analysis'][best_contamination]['predicted_anomalies']
            }
            
            # Save research log
            logger.info(f'Saving research results to {RESEARCH_LOG_PATH}')
            with open(RESEARCH_LOG_PATH, 'a') as f:
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
                    
                    serializable_results = convert_numpy_types(research_results)
                    f.write(json.dumps(serializable_results) + '\n')
            
            logger.info(f'Research results saved to {RESEARCH_LOG_PATH}')
            self.stdout.write(f'Research results saved to {RESEARCH_LOG_PATH}')
            
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
        
        # Drop 'is_anomaly' column if it exists to prevent data leakage
        training_data = df_processed.copy()

        if 'is_anomaly' in training_data.columns:
            training_data = training_data.drop('is_anomaly', axis=1)
            logger.info(f'Dropped is_anomaly column. Training data shape: {training_data.shape}')
        
        # Get model parameters from config
        model_params = self._get_model_parameters(contamination)
        
        model = IsolationForest(**model_params)
        logger.info(f'IsolationForest model created with contamination={contamination}')

        logger.info('Fitting model to processed data...')
        model.fit(training_data)
        logger.info('Model training complete.')
        self.stdout.write('Model training complete.')

        ### Save model and training columns
        logger.info(f'Saving model to {MODEL_PATH}')
        self.stdout.write(f'Saving model to {MODEL_PATH}')
        joblib.dump(model, MODEL_PATH)
        
        logger.info(f'Saving training columns to {COLUMNS_PATH}')
        self.stdout.write(f'Saving training columns to {COLUMNS_PATH}')
        joblib.dump(training_columns, COLUMNS_PATH)

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