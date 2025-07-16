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
    model = joblib.load(MODEL_PATH)
    training_columns = joblib.load(COLUMNS_PATH)
    model_loaded = True
    logger.info(f"Model loaded successfully. Training columns: {len(training_columns)}")
except (FileNotFoundError, Exception) as e:
    logger.warning(f"Model files not found. Using fallback. Error: {e}")
    model_loaded = False
    model = None
    training_columns = []

def run_complete_analysis(transaction: Transaction, contamination_param: float) -> Dict[str, Any]:
    """
    Orchestrates the full data pipeline for a single transaction.
    
    Args:
        transaction (Transaction): The Django model instance.
        contamination_param (float): The contamination parameter for the model.

    Returns:
        dict: A dictionary containing the analysis results.
    """
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
        transaction_df = model_to_dataframe(transaction)
        logger.debug(f"DataFrame shape: {transaction_df.shape}")

        # 2. Preprocessing
        logger.debug("Starting preprocessing...")
        preprocessed_df = preprocessing.clean_raw_data(transaction_df)
        logger.debug(f"Preprocessed DataFrame shape: {preprocessed_df.shape}")

        # 3. Feature Engineering
        logger.debug("Starting feature engineering...")
        features_df, feature_columns = feature_engineering.create_model_features(preprocessed_df)
        logger.debug(f"Feature engineering complete. Features shape: {features_df.shape}, Feature columns: {len(feature_columns)}")

        # 4. Align columns with model's training columns
        logger.debug("Aligning columns with training data...")
        final_df = align_columns(features_df, training_columns)
        logger.debug(f"Final DataFrame shape: {final_df.shape}")

        # 5. Run Inference
        # The contamination of an Isolation Forest is set at training time.
        # The `contamination_param` is stored for record-keeping, but the model's
        # original behavior is used for prediction.
        logger.debug("Running model inference...")
        
        anomaly_score = model.decision_function(final_df)[0]
        is_anomaly = model.predict(final_df)[0] == -1 # -1 means anomaly
        logger.info(f"Anomaly detection complete. Score: {anomaly_score:.4f}, Is anomaly: {is_anomaly}")

        # 6. Generate SHAP values for explainability
        logger.debug("Generating SHAP values for explainability...")
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(final_df)
        
        # Convert shap values to a JSON serializable format
        shap_values_json = json.dumps({
            'values': shap_values[0].tolist(),
            'base_values': explainer.expected_value.tolist() if hasattr(explainer.expected_value, 'tolist') else explainer.expected_value,
            'feature_names': final_df.columns.tolist()
        })
        logger.debug("SHAP values generated successfully")

        result = {
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': float(anomaly_score),
            'shap_values_json': shap_values_json
        }
        
        logger.info(f"Analysis completed successfully for transaction {transaction.transaction_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error in anomaly detection for transaction {transaction.transaction_id}: {e}", exc_info=True)
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
            'unit_purchase_price': [float(transaction.unit_purchase_price)],
            'total_purchase_price': [float(transaction.total_purchase_price) if transaction.total_purchase_price else 0],
            'average_price': [float(transaction.average_price) if transaction.average_price else 0],
            'supplier': [transaction.supplier],
            'procurement_method': [transaction.procurement_method.name],
            'procurement_officer': [transaction.procurement_officer or ''],
            'invoice_number': [transaction.invoice_number],
            'payment_receipt_number': [transaction.payment_receipt_number],
            'transaction_date': [pd.to_datetime(transaction.transaction_date)],
            'approved_budget': [float(transaction.approved_budget) if transaction.approved_budget else 0],
            # Add timeline fields
            'invitation_to_bid_posting_date': [pd.to_datetime(transaction.invitation_to_bid_posting_date) if transaction.invitation_to_bid_posting_date else None],
            'bid_submission_deadline': [pd.to_datetime(transaction.bid_submission_deadline) if transaction.bid_submission_deadline else None],
            'bid_opening_date': [pd.to_datetime(transaction.bid_opening_date) if transaction.bid_opening_date else None],
            'notice_of_award_date': [pd.to_datetime(transaction.notice_of_award_date) if transaction.notice_of_award_date else None],
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
    logger.debug(f"Aligning columns. Input shape: {df.shape}, Training columns: {len(training_columns)}")
    
    if not training_columns:
        logger.warning("No training columns provided, returning original dataframe")
        # If no training columns, return the original dataframe
        return df
    
    try:
        # Add missing columns with a default value of 0
        missing_columns = []
        for col in training_columns:
            if col not in df.columns:
                df[col] = 0
                missing_columns.append(col)
        
        if missing_columns:
            logger.debug(f"Added missing columns: {missing_columns}")
        
        # Return the dataframe with columns in the same order as training
        aligned_df = df[training_columns]
        logger.debug(f"Column alignment complete. Output shape: {aligned_df.shape}")
        return aligned_df
        
    except Exception as e:
        logger.error(f"Error aligning columns: {e}", exc_info=True)
        raise 