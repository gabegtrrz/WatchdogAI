"""
Management command to perform grid search optimization for Isolation Forest models.
Exhaustively tests all hyperparameter combinations to find optimal configurations.
"""
import os
import joblib
import json
import logging
import yaml
from datetime import datetime
from typing import Union, List, Optional, Dict, Any, Tuple
from itertools import product
from django.core.management.base import BaseCommand
from django.conf import settings
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score
import numpy as np
import pandas as pd

from apps.ai_analytics.services import preprocessing, feature_engineering

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Performs grid search optimization for Isolation Forest models to find optimal hyperparameters.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            required=True,
            help='Path to YAML configuration file for grid search'
        )

    def handle(self, *args, **options):
        """Main entry point for the command."""
        logger.info('Starting grid search optimization...')
        self.stdout.write('Starting grid search optimization...')

        try:
            # Load configuration
            config = self._load_configuration(options['config'])
            if not config:
                return

            # Store config for later use
            self._current_config = config

            # Get output paths
            results_dir = self._get_results_dir(config)
            os.makedirs(results_dir, exist_ok=True)

            # Process data
            training_data, training_columns = self._process_training_data(config)
            if training_data is None:
                return

            validation_data, true_labels = self._process_validation_data(config)
            if validation_data is None:
                return

            # Perform grid search
            results = self._perform_grid_search(
                training_data, training_columns, validation_data, true_labels, 
                results_dir, config
            )
            if results:
                self._save_results(results, results_dir)
                self._print_summary(results)

            logger.info('Grid search optimization complete.')
            self.stdout.write('Grid search optimization complete.')

        except Exception as e:
            logger.error(f'Error during grid search: {e}', exc_info=True)
            self.stderr.write(f'Error during grid search: {e}')

    def _load_configuration(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f'Loaded configuration from {config_path}')
            return config
            
        except FileNotFoundError:
            self.stderr.write(f'Configuration file not found: {config_path}')
            return None
        except yaml.YAMLError as e:
            self.stderr.write(f'Invalid YAML in configuration file: {e}')
            return None
        except Exception as e:
            self.stderr.write(f'Error loading configuration: {e}')
            return None

    def _get_results_dir(self, config: Dict[str, Any]) -> str:
        """Get results directory from config or use default."""
        results_dir = config.get('output', {}).get('results_dir', 'data/grid_search/results')
        if not os.path.isabs(results_dir):
            results_dir = os.path.join(settings.BASE_DIR, results_dir)
        return results_dir

    def _process_training_data(self, config: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Optional[List[str]]]:
        """Process training data."""
        try:
            training_path = config.get('data_source', {}).get('training_csv_path')
            if not training_path:
                self.stderr.write('Training CSV path not specified')
                return None, None
            
            df = preprocessing.get_dataframe(training_path)
            if df is None or df.empty:
                self.stderr.write('No training data found')
                return None, None
            
            # Clean and process data
            cleaned_df = preprocessing.clean_raw_data(df)
            df_processed, training_columns = feature_engineering.create_features(cleaned_df)
            
            return df_processed, training_columns
            
        except Exception as e:
            self.stderr.write(f'Error processing training data: {e}')
            return None, None

    def _process_validation_data(self, config: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Optional[np.ndarray]]:
        """Process validation data."""
        try:
            validation_path = config.get('data_source', {}).get('validation_csv_path')
            if not validation_path:
                self.stderr.write('Validation CSV path not specified')
                return None, None
            
            df = preprocessing.get_dataframe(validation_path)
            if df is None or df.empty:
                self.stderr.write('No validation data found')
                return None, None
            
            # Extract labels
            true_labels = preprocessing.extract_labels(df)
            if true_labels is None:
                self.stderr.write('No anomaly labels found in validation data')
                return None, None
            
            # Clean and process data
            cleaned_df = preprocessing.clean_raw_data(df)
            df_processed, _ = feature_engineering.create_features(cleaned_df)
            
            return df_processed, true_labels
            
        except Exception as e:
            self.stderr.write(f'Error processing validation data: {e}')
            return None, None

    def _perform_grid_search(self, training_data: pd.DataFrame, training_columns: List[str],
                           validation_data: pd.DataFrame, true_labels: np.ndarray,
                           results_dir: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform grid search over hyperparameters."""
        hyperparameters = config.get('grid_search', {}).get('hyperparameters', {})
        
        # Generate parameter combinations
        param_names = list(hyperparameters.keys())
        param_values = list(hyperparameters.values())
        param_combinations = list(product(*param_values))
        
        total_combinations = len(param_combinations)
        self.stdout.write(f'Testing {total_combinations} hyperparameter combinations...')
        
        results = {
            'grid_search_date': datetime.now().isoformat(),
            'total_combinations': total_combinations,
            'all_results': [],
            'best_models': {
                'best_f1_score': None,
                'best_precision': None,
                'best_recall': None,
                'best_auc': None
            }
        }
        
        best_f1 = best_precision = best_recall = best_auc = -1
        
        # Test each combination
        for i, param_combination in enumerate(param_combinations):
            param_dict = dict(zip(param_names, param_combination))
            
            self.stdout.write(f'Testing combination {i+1}/{total_combinations}: {param_dict}')
            
            try:
                # Train model
                model = IsolationForest(**param_dict)
                model.fit(training_data)
                
                # Evaluate model
                trial_result = self._evaluate_model(
                    model, validation_data, training_columns, true_labels, param_dict, config
                )
                
                if trial_result:
                    results['all_results'].append(trial_result)
                    
                    # Track best models
                    f1 = trial_result['f1_score']
                    precision = trial_result['precision']
                    recall = trial_result['recall']
                    auc = trial_result.get('auc_score', 0)
                    
                    if f1 > best_f1:
                        best_f1 = f1
                        results['best_models']['best_f1_score'] = trial_result
                    
                    if precision > best_precision:
                        best_precision = precision
                        results['best_models']['best_precision'] = trial_result
                    
                    if recall > best_recall:
                        best_recall = recall
                        results['best_models']['best_recall'] = trial_result
                    
                    if auc > best_auc:
                        best_auc = auc
                        results['best_models']['best_auc'] = trial_result
                
            except Exception as e:
                logger.error(f'Error testing combination {param_dict}: {e}')
                continue
        
        return results

    def _evaluate_model(self, model, validation_data: pd.DataFrame, training_columns: List[str],
                       true_labels: np.ndarray, param_dict: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate a trained model."""
        try:
            # Prepare features
            features_df = validation_data.copy()
            
            # Handle column mismatches
            missing_columns = set(training_columns) - set(features_df.columns)
            for col in missing_columns:
                features_df[col] = 0
            
            extra_columns = set(features_df.columns) - set(training_columns)
            if extra_columns:
                features_df = features_df[training_columns]
            
            # Remove label column if present
            if 'is_anomaly' in features_df.columns:
                features_df = features_df.drop('is_anomaly', axis=1)
            
            # Get predictions
            anomaly_scores = model.score_samples(features_df)
            contamination = param_dict.get('contamination', 0.1)
            threshold = np.percentile(anomaly_scores, contamination * 100)
            predicted_labels = (anomaly_scores <= threshold).astype(int)
            
            # Calculate metrics
            if np.sum(predicted_labels) == 0:
                precision = recall = f1 = 0.0
            else:
                precision = precision_score(true_labels, predicted_labels, zero_division=0)
                recall = recall_score(true_labels, predicted_labels, zero_division=0)
                f1 = f1_score(true_labels, predicted_labels, zero_division=0)
            
            # Calculate AUC if AUC calculation is enabled in config
            auc_enabled = config.get('grid_search', {}).get('calculate_auc', True)
            if auc_enabled:
                auc = roc_auc_score(true_labels, -anomaly_scores)
            else:
                auc = 0.0 # AUC is not calculated

            return {
                'parameters': param_dict,
                'f1_score': float(f1),
                'precision': float(precision),
                'recall': float(recall),
                'predicted_anomalies': int(np.sum(predicted_labels)),
                'true_anomalies': int(np.sum(true_labels)),
                'auc_score': float(auc) # Add AUC to the result
            }
            
        except Exception as e:
            logger.error(f'Error evaluating model: {e}')
            return None

    def _save_results(self, results: Dict[str, Any], results_dir: str):
        """Save results to JSON file."""
        try:
            # Get configurable filename from config or use default
            config = getattr(self, '_current_config', {})
            output_config = config.get('output', {})
            
            # Use custom filename if specified, otherwise use timestamp
            custom_filename = output_config.get('results_filename')
            if custom_filename:
                # Replace {timestamp} placeholder if present
                if '{timestamp}' in custom_filename:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = custom_filename.replace('{timestamp}', timestamp)
                else:
                    filename = custom_filename
            else:
                # Default filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'grid_search_results_{timestamp}.json'
            
            results_file = os.path.join(results_dir, filename)
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.stdout.write(f'Results saved to: {results_file}')
            
        except Exception as e:
            self.stderr.write(f'Error saving results: {e}')

    def _print_summary(self, results: Dict[str, Any]):
        """Print summary of results."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('GRID SEARCH RESULTS SUMMARY')
        self.stdout.write('='*60)
        
        # Best F1 Score
        best_f1 = results['best_models']['best_f1_score']
        if best_f1:
            self.stdout.write(f'\nBest F1-Score Model:')
            self.stdout.write(f'  F1-Score: {best_f1["f1_score"]:.4f}')
            self.stdout.write(f'  Precision: {best_f1["precision"]:.4f}')
            self.stdout.write(f'  Recall: {best_f1["recall"]:.4f}')
            if 'auc_score' in best_f1:
                self.stdout.write(f'  AUC: {best_f1["auc_score"]:.4f}')
            self.stdout.write(f'  Parameters: {best_f1["parameters"]}')
        
        # Best Precision
        best_precision = results['best_models']['best_precision']
        if best_precision:
            self.stdout.write(f'\nBest Precision Model:')
            self.stdout.write(f'  Precision: {best_precision["precision"]:.4f}')
            self.stdout.write(f'  F1-Score: {best_precision["f1_score"]:.4f}')
            self.stdout.write(f'  Recall: {best_precision["recall"]:.4f}')
            if 'auc_score' in best_precision:
                self.stdout.write(f'  AUC: {best_precision["auc_score"]:.4f}')
            self.stdout.write(f'  Parameters: {best_precision["parameters"]}')
        
        # Best Recall
        best_recall = results['best_models']['best_recall']
        if best_recall:
            self.stdout.write(f'\nBest Recall Model:')
            self.stdout.write(f'  Recall: {best_recall["recall"]:.4f}')
            self.stdout.write(f'  F1-Score: {best_recall["f1_score"]:.4f}')
            self.stdout.write(f'  Precision: {best_recall["precision"]:.4f}')
            if 'auc_score' in best_recall:
                self.stdout.write(f'  AUC: {best_recall["auc_score"]:.4f}')
            self.stdout.write(f'  Parameters: {best_recall["parameters"]}')
        
        # Best AUC
        best_auc = results['best_models']['best_auc']
        if best_auc and best_auc.get('auc_score', 0) > 0:
            self.stdout.write(f'\nBest AUC Model:')
            self.stdout.write(f'  AUC: {best_auc["auc_score"]:.4f}')
            self.stdout.write(f'  F1-Score: {best_auc["f1_score"]:.4f}')
            self.stdout.write(f'  Precision: {best_auc["precision"]:.4f}')
            self.stdout.write(f'  Recall: {best_auc["recall"]:.4f}')
            self.stdout.write(f'  Parameters: {best_auc["parameters"]}')
        
        self.stdout.write(f'\nTotal combinations tested: {results["total_combinations"]}')
        self.stdout.write(f'Successful evaluations: {len(results["all_results"])}')
        self.stdout.write('='*60) 