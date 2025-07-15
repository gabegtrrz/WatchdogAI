"""
Management command to train the Isolation Forest model with research evaluation.
"""
import os
import joblib
import json
from datetime import datetime
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


class Command(BaseCommand):
    help = 'Trains the Isolation Forest model for anomaly detection with research-grade evaluation.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--contamination',
            type=str,
            default='auto',
            help='Contamination parameter for Isolation Forest (float or "auto")'
        )
        parser.add_argument(
            '--research-mode',
            action='store_true',
            help='Enable research mode with cross-validation and detailed logging'
        )
        parser.add_argument(
            '--contamination-range',
            nargs='+',
            type=float,
            default=[0.01, 0.05, 0.10, 0.15],
            help='Range of contamination values to test in research mode'
        )
        parser.add_argument(
            '--csv',
            type=str,
            help='Path to CSV file to use for training instead of database data'
        )
        parser.add_argument(
            '--labeled-data-path',
            type=str,
            default='data/training_data/training_1/transactions_with_labels.csv',
            help='Path to labeled data CSV file for research mode evaluation'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting model training...')

        

        # Ensure the model directory exists
        os.makedirs(MODEL_DIR, exist_ok=True)

        # 1. Get and preprocess data
        self.stdout.write('Fetching and preprocessing transaction data...')
            # Step 1: Get raw data and clean it

            # Determine if getting data from CSV or Database

        try:
            csv_source = options.get('csv')
            if csv_source:
                self.stdout.write(f'Using CSV source: {csv_source}')
                df = preprocessing.get_dataframe(csv_source)
            else:
                self.stdout.write('Using database as data source')
                df = preprocessing.get_dataframe()
                
            if df.empty:
                self.stdout.write('No transaction data found to train the model.')
                return
        except Exception as e:
            self.stderr.write(f'Error during data fetching: {e}')
            return
        
        try:
            cleaned_df = preprocessing.clean_raw_data(df)
        except Exception as e:
            self.stderr.write(f'Error during data preprocessing: {e}')
            return

        
        # Step 2: Engineer features

        try:
            df_processed, training_columns = feature_engineering.create_model_features(cleaned_df)
        except Exception as e:
            self.stderr.write(f'Error during feature engineering: {e}')
            return

        self.stdout.write(f'Successfully processed {df_processed.shape[0]} transactions with {df_processed.shape[1]} features.')


        # Research mode: Test multiple contamination values
        if options['research_mode']:
            labeled_data_path = options['labeled_data_path']
            self._research_mode_training(df_processed, training_columns, options['contamination_range'], labeled_data_path)
        else:
            # Standard training
            self._standard_training(df_processed, training_columns, contamination= options['contamination'])

    # def _research_mode_training(self, df_processed, training_columns, contamination_range, labeled_data_path):
    def _research_mode_training(self, df_processed, training_columns, contamination_range, labeled_data_path):
        """Research mode with cross-validation and multiple contamination values."""
        self.stdout.write('Running research mode with cross-validation...')
        
        if not os.path.exists(labeled_data_path):
            self.stderr.write(f'Labeled data not found at {labeled_data_path}')
            return
            
        try:
            labeled_df = preprocessing.get_dataframe(labeled_data_path)
            # Get true labels (1 for anomaly, 0 for normal)
            true_labels = labeled_df['is_anomaly'].values
            # Convert to binary: 1 for anomaly, 0 for normal (applying for robustness)
            true_labels_binary = (true_labels == 1).astype(int)

        except Exception as e:
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

        best_f1_score = -1
        best_contamination = None

        for contamination in contamination_range:
            self.stdout.write(f'Testing contamination={contamination}...')
            
            model = IsolationForest(
                contamination=contamination, 
                random_state=42,
                n_estimators=100 # Number of base estimators (or "itrees") in the ensemble
            )
            
            try:
                # Get anomaly predictions for evaluation
                scores = model.fit_predict(df_processed)
                # returns an array where:
                # -1 indicates an anomaly (outlier)
                # 1 indicates normal data (inlier)


                # Convert scores to binary predictions: -1 (anomaly) -> 1, 1 (normal) -> 0
                predicted_labels = (scores == -1).astype(int) #  returns a new numpy.ndarray filled with True or False values -> int (1 or 0)
                
                # Calculate metrics using true labels
                
                # Handle case where no anomalies are predicted
                if np.sum(predicted_labels) == 0:
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
                
                # Calculate confusion matrix
                cm = confusion_matrix(true_labels_binary, predicted_labels)
                
                # Store results
                research_results['contamination_analysis'][contamination] = {
                    'precision': precision,
                    'recall': recall,
                    'f1_score': f1,
                    'predicted_anomalies': np.sum(predicted_labels),
                    'predicted_normal': len(predicted_labels) - np.sum(predicted_labels),
                    'confusion_matrix': cm.tolist(),
                    'model_config': {
                        'contamination': contamination,
                        'n_estimators': 100,
                        'random_state': 42
                    }
                }
                
                # Track best performing model based on F1-score
                if f1 > best_f1_score:
                    best_f1_score = f1
                    best_contamination = contamination
                    
            except Exception as e:
                self.stderr.write(f'Error testing contamination={contamination}: {e}')

        # Train final model with best contamination
        if best_contamination:
            self.stdout.write(f'Best contamination value: {best_contamination} (F1-score: {best_f1_score:.4f})')
            final_model = IsolationForest(
                contamination=best_contamination,
                random_state=42,
                n_estimators=100
            )
            final_model.fit(df_processed)
            
            # Save model and research results
            joblib.dump(final_model, MODEL_PATH)
            joblib.dump(training_columns, COLUMNS_PATH)
            
            research_results['best_model'] = {
                'contamination': best_contamination,
                'f1_score': best_f1_score,
                'precision': research_results['contamination_analysis'][best_contamination]['precision'],
                'recall': research_results['contamination_analysis'][best_contamination]['recall']
            }
            
            # Save research log
            with open(RESEARCH_LOG_PATH, 'w') as f:
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
                    json.dump(serializable_results, f, indent=2)
            
            self.stdout.write(f'Research results saved to {RESEARCH_LOG_PATH}')
            self.stdout.write('Research mode training complete.')

    def _standard_training(self, df_processed, training_columns, contamination):
        """Standard training mode."""
        self.stdout.write('Training Isolation Forest model...')
        
        # Convert contamination to float if it's a numeric string, otherwise keep as 'auto'
        if contamination == 'auto':
            contamination_param = 'auto'
        else:
            try:
                contamination_param = float(contamination)
            except ValueError:
                self.stderr.write(f'Invalid contamination value: {contamination}. Using "auto".')
                contamination_param = 'auto'

        
        model = IsolationForest(
            contamination=str(contamination_param), 
            random_state=42,
            n_estimators=100
        )

        model.fit(df_processed)
        self.stdout.write('Model training complete.')

        ### Save model and training columns
        self.stdout.write(f'Saving model to {MODEL_PATH}')
        joblib.dump(model, MODEL_PATH)
        
        self.stdout.write(f'Saving training columns to {COLUMNS_PATH}')
        joblib.dump(training_columns, COLUMNS_PATH)

        self.stdout.write('Successfully trained and saved the model and column list.') 