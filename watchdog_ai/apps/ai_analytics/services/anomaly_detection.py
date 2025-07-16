"""
This service orchestrates the anomaly detection pipeline using the separated
preprocessing and feature engineering services.
"""
import joblib
import json
import pandas as pd
import shap
import os
import logging
import time
from typing import Dict, Any, Optional
from . import preprocessing
from . import feature_engineering
from apps.core.models import Transaction

# Configure logging for this module
logger = logging.getLogger(__name__)

# Load model and columns at module level for efficiency
MODEL_PATH = 'watchdog_ai/apps/ai_analytics/model_files/isolation_forest.joblib'
COLUMNS_PATH = 'watchdog_ai/apps/ai_analytics/model_files/training_columns.joblib'

# Check if model files exist, if not create a simple fallback
try:
    logger.info("Loading model files...")
    
    if not os.path.exists(MODEL_PATH) or not os.path.exists(COLUMNS_PATH):
        raise FileNotFoundError("Model files not found")
    model = joblib.load(MODEL_PATH)
    training_columns = joblib.load(COLUMNS_PATH)
    model_loaded = True
    logger.info(f"Model loaded successfully. Training columns: {len(training_columns)}")
except (FileNotFoundError, Exception) as e:
    logger.warning(f"Model files not found. Using fallback. Error: {e}")
    model_loaded = False
    model = None
    training_columns = []

def test_logging():
    """Test function to verify logging is working correctly."""
    logger.debug("Debug message from anomaly detection service")
    logger.info("Info message from anomaly detection service")
    logger.warning("Warning message from anomaly detection service")
    logger.error("Error message from anomaly detection service")
    return "Logging test completed"

def safe_float_conversion(value, field_name=""):
    """Safely converts a value to a float, with logging for errors."""
    try:
        if value is None:
            return 0.0
        return float(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert {field_name} value '{value}' to float: {e}")
        return 0.0

def generate_shap_values(model, final_df):
    """Generate SHAP values for model explainability."""
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(final_df)
        
        # Handle different types of expected values
        base_values = explainer.expected_value
        if base_values is None:
            base_values = 0.5
        elif hasattr(base_values, 'tolist') and callable(getattr(base_values, 'tolist', None)):
            try:
                base_values = base_values.tolist()
            except (AttributeError, TypeError):
                base_values = 0.5
        elif isinstance(base_values, (list, tuple)):
            base_values = list(base_values)
        else:
            try:
                base_values = float(base_values)
            except (ValueError, TypeError):
                base_values = 0.5
        
        return json.dumps({
            'values': shap_values[0].tolist(),
            'base_values': base_values,
            'feature_names': final_df.columns.tolist(),
            'error': 'SHAP calculation failed'
        })
    except Exception as e:
        logger.error(f"Error generating SHAP values: {e}", exc_info=True)
        return json.dumps({
            'values': [],
            'base_values': 0.5,
            'feature_names': final_df.columns.tolist(),
            'error': 'SHAP calculation failed'
        })

def run_complete_analysis(transaction: Transaction, contamination_param: float) -> Dict[str, Any]:
    """
    Orchestrates the full data pipeline for a single transaction.
    
    Args:
        transaction (Transaction): The Django model instance.
        contamination_param (float): The contamination parameter for the model.

    Returns:
        dict: A dictionary containing the analysis results.
    """
    start_time = time.time()
    logger.info(f"Starting anomaly analysis for transaction ID: {transaction.transaction_id}")
    logger.debug(f"Contamination parameter: {contamination_param}")
    
    if not model_loaded:
        logger.warning("Model not loaded, returning fallback result")
        # Return a fallback result if model is not available
        return {
            'is_anomaly': False,
            'anomaly_score': 0.5,
            'shap_values_json': json.dumps({
                'values': [],
                'base_values': 0.5,
                'feature_names': []
            })
        }
    
    try:
        # 1. Convert Django model to DataFrame
        logger.debug("Converting transaction to DataFrame...")
        step_start = time.time()
        transaction_df = model_to_dataframe(transaction)
        logger.debug(f"DataFrame shape: {transaction_df.shape}")
        logger.debug(f"DataFrame conversion completed in {time.time() - step_start:.3f}s")

        # 2. Preprocessing
        logger.debug("Starting preprocessing...")
        step_start = time.time()
        preprocessed_df = preprocessing.clean_raw_data(transaction_df)
        logger.debug(f"Preprocessed DataFrame shape: {preprocessed_df.shape}")
        logger.debug(f"Preprocessing completed in {time.time() - step_start:.3f}s")

        # 3. Feature Engineering
        logger.debug("Starting feature engineering...")
        step_start = time.time()
        features_df, feature_columns = feature_engineering.create_model_features(preprocessed_df)
        logger.debug(f"Feature engineering complete.Feature columns: {len(feature_columns)}")
        logger.debug(f"Feature engineering completed in {time.time() - step_start:.3f}s")

        # 4. Align columns with model's training columns
        logger.debug("Aligning columns with training data...")
        step_start = time.time()
        final_df = align_columns(features_df, training_columns)
        logger.debug(f"Final DataFrame shape: {final_df.shape}")
        logger.debug(f"Column alignment completed in {time.time() - step_start:.3f}s")

        # 5. Run Inference
        # The contamination of an Isolation Forest is set at training time.
        # The `contamination_param` is stored for record-keeping, but the model's
        # original behavior is used for prediction.
        logger.debug("Running model inference...")
        step_start = time.time()
        
        if model is not None:
            anomaly_score = model.decision_function(final_df)[0]
            is_anomaly = model.predict(final_df)[0] == -1 # -1 means anomaly
            logger.info(f"Anomaly detection complete. Score: {anomaly_score:.4f}, Is anomaly: {is_anomaly}")
            logger.debug(f"Model inference completed in {time.time() - step_start:.3f}s")

            # 6. Generate SHAP values for explainability
            logger.debug("Generating SHAP values for explainability...")
            step_start = time.time()
            shap_values_json = generate_shap_values(model, final_df)
            logger.debug("SHAP values generated successfully")
            logger.debug(f"SHAP analysis completed in {time.time() - step_start:.3f}s")

            result = {
                'is_anomaly': bool(is_anomaly),
                'anomaly_score': float(anomaly_score),
                'shap_values_json': shap_values_json
            }
        else:
            logger.error("Model is None, cannot perform inference")
            result = {
                'is_anomaly': False,
                'anomaly_score': 0.5,
                'shap_values_json': json.dumps({
                    'values': [],
                    'base_values': 0.5,
                    'feature_names': []
                })
            }
        
        total_time = time.time() - start_time
        logger.info(f"Analysis completed successfully for transaction {transaction.transaction_id} in {total_time:.3f}s")
        return result
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Error in anomaly detection for transaction {transaction.transaction_id} after {total_time:.3f}s: {e}", exc_info=True)
        # Return a fallback result
        return {
            'is_anomaly': False,
            'anomaly_score': 0.5,
            'shap_values_json': json.dumps({
                'values': [],
                'base_values': 0.5,
                'feature_names': []
            })
        }

def model_to_dataframe(transaction: Transaction) -> pd.DataFrame:
    """Converts a Transaction model instance to a pandas DataFrame."""
    logger.debug(f"Converting transaction {transaction.transaction_id} to DataFrame")
    
    try:
        # Use the actual Transaction model fields
        data = {
            'transaction_id': [transaction.transaction_id],
            'project_name': [transaction.project_name or ''],
            'end_user_unit': [transaction.end_user_unit or ''],
            'item_name': [transaction.item_name],
            'quantity': [transaction.quantity],
            'unit_purchase_price': [safe_float_conversion(transaction.unit_purchase_price, 'unit_purchase_price')],
            'total_purchase_price': [safe_float_conversion(transaction.total_purchase_price, 'total_purchase_price')],
            'average_price': [safe_float_conversion(transaction.average_price, 'average_price')],
            'supplier': [transaction.supplier],
            'procurement_method': [transaction.procurement_method.name],
            'procurement_officer': [transaction.procurement_officer or ''],
            'invoice_number': [transaction.invoice_number],
            'payment_receipt_number': [transaction.payment_receipt_number],
            'transaction_date': [pd.to_datetime(str(transaction.transaction_date))],
            'approved_budget': [safe_float_conversion(transaction.approved_budget, 'approved_budget')],
            # Add timeline fields
            'invitation_to_bid_posting_date': [pd.to_datetime(str(transaction.invitation_to_bid_posting_date)) if transaction.invitation_to_bid_posting_date else None],
            'bid_submission_deadline': [pd.to_datetime(str(transaction.bid_submission_deadline)) if transaction.bid_submission_deadline else None],
            'bid_opening_date': [pd.to_datetime(str(transaction.bid_opening_date)) if transaction.bid_opening_date else None],
            'notice_of_award_date': [pd.to_datetime(str(transaction.notice_of_award_date)) if transaction.notice_of_award_date else None],
            'contract_signing_date': [pd.to_datetime(transaction.contract_signing_date) if transaction.contract_signing_date else None],
        }
        
        df = pd.DataFrame(data)
        logger.debug(f"DataFrame created successfully with shape: {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Error converting transaction {transaction.transaction_id} to DataFrame: {e}", exc_info=True)
        raise

def align_columns(df: pd.DataFrame, training_columns: list) -> pd.DataFrame:
    """Aligns DataFrame columns to match the model's training columns."""
    logger.debug(f"Aligning columns. Training columns: {len(training_columns)}")
    
    if not training_columns:
        logger.warning("No training columns provided, returning original dataframe")
        # If no training columns, return the original dataframe
        return df
    
    try:
        # Log current columns for debugging
        current_columns = df.columns.tolist()
        logger.debug(f"Current DataFrame columns: {current_columns}")
        logger.debug(f"Expected training columns: {training_columns}")
        
        # Find columns that exist in current data but not in training data
        extra_columns = set(current_columns) - set(training_columns)
        if extra_columns:
            logger.warning(f"Removing extra columns not in training data: {extra_columns}")
            df = df.drop(columns=list(extra_columns))
        
        # Add missing columns with a default value of 0
        missing_columns = []
        for col in training_columns:
            if col not in df.columns:
                df[col] = 0
                missing_columns.append(col)
        
        if missing_columns:
            logger.debug(f"Added missing columns: {missing_columns}")
        
        # Ensure columns are in the same order as training data
        aligned_df = df[training_columns]
        logger.debug(f"Column alignment complete. Output shape: {aligned_df.shape}")
        return aligned_df
        
    except Exception as e:
        logger.error(f"Error aligning columns: {e}", exc_info=True)
        raise 