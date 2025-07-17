"""
This service orchestrates the anomaly detection pipeline using the separated
preprocessing and feature engineering services.

**Main Components:**
- Model loading and validation
- Transaction data conversion to DataFrame
- Complete anomaly detection workflow
- SHAP explainability generation
- Error handling and fallback mechanisms
"""
import joblib
import json
import pandas as pd
import shap
import os
import logging
import time
from typing import Dict, Any, Optional, List, Union
from . import preprocessing
from . import feature_engineering
from apps.core.models import Transaction
import numpy as np

# Configure logging for this module
logger = logging.getLogger(__name__)

# Model is loaded at module import

# =============================================================================
# MODEL CONFIGURATION AND LOADING
# =============================================================================

# Model file paths - centralized configuration for easy maintenance
MODEL_PATH = 'watchdog_ai/apps/ai_analytics/model_files/iforest.joblib'
COLUMNS_PATH = 'watchdog_ai/apps/ai_analytics/model_files/columns.joblib'

# Global model state variables
model_loaded: bool = False
model: Optional[Any] = None
training_columns: List[str] = []

def _load_model_files() -> None:
    """Loads the trained Isolation Forest model and training columns.
    
    **Process:**
    1. Checks if model files exist on disk
    2. Loads the trained model using joblib
    3. Loads the training column specifications
    4. Sets global state variables for model availability
    
    **Error Handling:** Sets fallback state if files are missing or corrupted.
    """

    global model_loaded, model, training_columns
    
    try:
        logger.info("Loading model files...")
        
        # Validate file existence
        if not os.path.exists(MODEL_PATH) or not os.path.exists(COLUMNS_PATH):
            raise FileNotFoundError("Model files not found")
        
        # Load model and training columns
        model = joblib.load(MODEL_PATH)
        training_columns = joblib.load(COLUMNS_PATH)
        model_loaded = True
        
        logger.info(f"Model loaded successfully. Training columns: {len(training_columns)}")
        
    except (FileNotFoundError, Exception) as e:
        logger.warning(f"Model files not found. Using fallback. Error: {e}")
        model_loaded = False
        model = None
        training_columns = []

# Initialize model loading at module import
_load_model_files()

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def test_logging() -> str:
    """
    Test function to verify logging is working correctly.
    
    **Purpose:** Diagnostic function for troubleshooting logging configuration.
    
    Returns:
        str: Confirmation message that logging test completed.
    """
    logger.debug("Debug message from anomaly detection service")
    logger.info("Info message from anomaly detection service")
    logger.warning("Warning message from anomaly detection service")
    logger.error("Error message from anomaly detection service")
    return "Logging test completed"

def safe_float_conversion(value: Any, field_name: str = "") -> float:
    """Safely converts a value to a float, with comprehensive error handling.
    
    **Process:**
    1. Handles None values by returning 0.
    2. Attempts direct float conversion.
    3. Logs warnings for conversion failures.
    4. Returns 0.0s fallback for any conversion errors.
    
    Args:
        value: The value to convert to float
        field_name: Name of the field for logging purposes
        
    Returns:
        float: Converted value or 0.0 if conversion fails.
    """

    try:
        if value is None:
            return 0.0
        return float(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert {field_name} value '{value}' to float: {e}")
        return 0.0

def generate_shap_values(model: Any, final_df: pd.DataFrame) -> str:
    """
    Generate SHAP values for model explainability and feature importance analysis.
    
    **Process:**
    1. Creates TreeExplainer for the Isolation Forest model.
    2. Calculates SHAP values for the input data.
    3. Handles various expected_value formats (scalar, array, list).
    4. Returns JSON-formatted explanation data.
    
    **Error Handling:** Returns structured error response if SHAP calculation fails.
    
    Args:
        model: The trained Isolation Forest model.
        final_df: Preprocessed DataFrame ready for model inference.
        
    Returns:
        str: JSON string containing SHAP values and feature explanations.
    """
    try:
        # Create SHAP explainer for tree-based model
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(final_df)
        
        # Handle different types of expected values with robust type checking
        base_values = explainer.expected_value
        if base_values is None:
            base_values = 0.5
        # Only call .tolist() if attribute exists and is not a list already
        elif hasattr(base_values, 'tolist') and not isinstance(base_values, (list, tuple)):
            try:
                base_values = base_values.tolist()
            except (AttributeError, TypeError):
                base_values = 0.5
        elif isinstance(base_values, (list, tuple)):
            base_values = list(base_values)
        else:
            try:
                # Only call float() on convertible types
                if isinstance(base_values, (int, float, str)):
                    base_values = float(base_values)
                else:
                    base_values = 0.5
            except (ValueError, TypeError):
                base_values = 0.5
        # Return structured SHAP explanation data
        return json.dumps({
            'values': shap_values[0].tolist(),
            'base_values': base_values,
            'feature_names': final_df.columns.tolist(),
            'error': None
        })
        
    except Exception as e:
        logger.error(f"Error generating SHAP values: {e}", exc_info=True)
        return json.dumps({
            'values': [],
            'base_values': 0.5,
            'feature_names': final_df.columns.tolist(),
            'error': 'SHAP calculation failed'
        })

def debug_column_issue(df: pd.DataFrame, stage: str) -> None:
    """Debug function to identify where 'is_anomaly' column might be coming from.
    
    Args:
        df: DataFrame to check
        stage: Name of the processing stage for logging
    """
    if 'is_anomaly' in df.columns:
        logger.error(f"CRITICAL: 'is_anomaly' column found at stage: {stage}")
        logger.error(f"DataFrame columns: {list(df.columns)}")
        logger.error(f"DataFrame shape: {df.shape}")
        # Check if any other columns contain 'anomaly' in their name
        anomaly_related_cols = [col for col in df.columns if 'anomaly' in col.lower()]
        if anomaly_related_cols:
            logger.error(f"Anomaly-related columns found: {anomaly_related_cols}")
    else:
        logger.debug(f"No 'is_anomaly' column found at stage: {stage}")

# =============================================================================
# DATA CONVERSION FUNCTIONS
# =============================================================================

def model_to_dataframe(transaction: Transaction) -> pd.DataFrame:
    """Converts a Django Transaction model instance to a pandas DataFrame.
    
    **Process:**
    1. Extracts all relevant fields from the Transaction model.
    2. Handles date field conversions with proper null checking.
    3. Applies safe float conversion for numeric fields.
    4. Creates structured DataFrame with consistent data types.
    
    **Data Fields Included:**
    - Basic transaction information (ID, project, supplier)
    - Financial data (prices, budgets)
    - Procurement details (method, officer)
    - Timeline information (various dates)
    
    Args:
        transaction: The Django Transaction model instance.
        
    Returns:
        pd.DataFrame: Structured DataFrame ready for preprocessing.
        
    Raises:
        Exception: If DataFrame creation fails.
    """
    logger.debug(f"Converting transaction {transaction.transaction_id} to DataFrame")
    
    try:
        # Comprehensive data extraction with proper field mapping
        data = {
            # Basic transaction information
            'transaction_id': [transaction.transaction_id],
            'project_name': [transaction.project_name or ''],
            'end_user_unit': [transaction.end_user_unit or ''],
            'item_name': [transaction.item_name],
            
            # Quantity and pricing information
            'quantity': [transaction.quantity],
            'unit_purchase_price': [safe_float_conversion(transaction.unit_purchase_price, 'unit_purchase_price')],
            'total_purchase_price': [safe_float_conversion(transaction.total_purchase_price, 'total_purchase_price')],
            'average_price': [safe_float_conversion(transaction.average_price, 'average_price')],
            
            # Supplier and procurement details
            'supplier': [transaction.supplier],
            'procurement_method': [transaction.procurement_method.name],
            'procurement_officer': [transaction.procurement_officer or ''],
            
            # Document numbers
            'invoice_number': [transaction.invoice_number],
            'payment_receipt_number': [transaction.payment_receipt_number],
            
            # Main transaction date
            'transaction_date': [pd.to_datetime(str(transaction.transaction_date))],
            
            # Budget information
            'approved_budget': [safe_float_conversion(transaction.approved_budget, 'approved_budget')],
            
            # Timeline fields with proper null handling
            'invitation_to_bid_posting_date': [pd.to_datetime(str(transaction.invitation_to_bid_posting_date)) if transaction.invitation_to_bid_posting_date else None],
            'bid_submission_deadline': [pd.to_datetime(str(transaction.bid_submission_deadline)) if transaction.bid_submission_deadline else None],
            'bid_opening_date': [pd.to_datetime(str(transaction.bid_opening_date)) if transaction.bid_opening_date else None],
            'notice_of_award_date': [pd.to_datetime(str(transaction.notice_of_award_date)) if transaction.notice_of_award_date else None],
            'contract_signing_date': [pd.to_datetime(str(transaction.contract_signing_date)) if transaction.contract_signing_date else None],
        }
        
        df = pd.DataFrame(data)
        logger.debug(f"DataFrame created successfully with shape: {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Error converting transaction {transaction.transaction_id} to DataFrame: {e}", exc_info=True)
        raise

def align_columns(df: pd.DataFrame, training_columns: List[str]) -> pd.DataFrame:
    """Aligns DataFrame columns to match the model's training columns exactly.
    
    **Process:**
    1. Removes extra columns not present in training data.
    2. Adds missing columns with default value of 0.
    3. Ensures column order matches training data exactly.
    4. Returns DataFrame with identical structure to training data.
    
    Purpose: Ensures model input compatibility and prevents dimension mismatch errors.
    
    Args:
        df: Input DataFrame with potentially mismatched columns.
        training_columns: List of column names from model training data.
        
    Returns:
        pd.DataFrame: Aligned DataFrame matching training data structure.
    """
    logger.debug(f"Aligning columns. Training columns: {len(training_columns)}")
    
    if not training_columns:
        logger.warning("No training columns provided, returning original dataframe")
        return df
    
    try:
        # Log current columns for debugging and transparency
        current_columns = df.columns.tolist()
        logger.debug(f"Current DataFrame columns: {current_columns}")
        logger.debug(f"Expected training columns: {training_columns}")
        
        # Remove extra columns not present in training data
        extra_columns = set(current_columns) - set(training_columns)
        if extra_columns:
            logger.warning(f"Removing extra columns not in training data: {extra_columns}")
            df = df.drop(columns=list(extra_columns))
        
        # Add missing columns with default value of 0
        missing_columns = []
        for col in training_columns:
            if col not in df.columns:
                df[col] = 0
                missing_columns.append(col)
        
        if missing_columns:
            logger.debug(f"Added missing columns: {missing_columns}")
        
        # Ensure columns are in the same order as training data
        aligned_df = df[training_columns]
        # If the result is a Series (single column), convert to DataFrame
        if isinstance(aligned_df, pd.Series):
            aligned_df = aligned_df.to_frame().T
        else:
            aligned_df = aligned_df.copy()
        logger.debug(f"Column alignment complete. Output shape: {aligned_df.shape}")
        return aligned_df
        
    except Exception as e:
        logger.error(f"Error aligning columns: {e}", exc_info=True)
        raise

# =======================
# MAIN ANALYSIS WORKFLOW
# =======================

def run_complete_analysis(transaction: Transaction, contamination_param: float = 0.05) -> Dict[str, Any]:
    """Complete anomaly detection pipeline for a SINGLE transaction.
    
    Workflow Steps:
    1. Model Validation: Verifies trained Isolation Forest model is loaded.
    2. Data Conversion: Converts Django Transaction model to pandas DataFrame.
    3. Preprocessing: Cleans and validates raw transaction data.
    4. Feature Engineering: Creates derived features for anomaly detection.
    5. Column Alignment: Ensures DataFrame columns match model's training data.
    6. Model Inference: Runs Isolation Forest prediction to detect anomalies.
    7. SHAP Analysis: Generates explainable AI values for feature importance.
    8. Result Compilation: Returns comprehensive analysis results.
    
    Error Handling: Returns fallback results if any step fails, ensuring system resilience.
    
    Performance Monitoring: Tracks timing for each pipeline stage for optimization.
    
    Args:
        transaction: Transaction instance to analyze.
        contamination_param: Contamination parameter for the model (stored for record-keeping).

    Returns:
        dict: Comprehensive analysis results containing:
            - is_anomaly (bool): Whether the transaction is classified as anomalous.
            - anomaly_score (float): Raw anomaly score from the model.
            - shap_values_json (str): JSON string containing SHAP explanations.
    """
    
    start_time = time.time()
    logger.info(f"Starting anomaly analysis for transaction ID: {transaction.transaction_id}")
    logger.debug(f"Contamination parameter: {contamination_param}")
    
    # Early validation: Check if model is available
    if not model_loaded:
        logger.warning("Model not loaded, returning fallback result")
        return _get_fallback_result()
    
    try:
        # Step 1: Convert Django model to DataFrame
        logger.debug("Converting transaction to DataFrame...")
        step_start = time.time()

        transaction_df = model_to_dataframe(transaction)

        logger.debug(f"DataFrame shape: {transaction_df.shape}")
        logger.debug(f"DataFrame conversion completed in {time.time() - step_start:.3f}s")



        # Step 2: Preprocessing - Clean and validate raw data
        logger.debug("Starting preprocessing...")
        step_start = time.time()

        preprocessed_df = preprocessing.clean_raw_data(transaction_df)

        logger.debug(f"Preprocessed DataFrame shape: {preprocessed_df.shape}")
        logger.debug(f"Preprocessing completed in {time.time() - step_start:.3f}s")



        # Step 3: Feature Engineering - Create derived features
        logger.debug("Starting feature engineering...")
        step_start = time.time()

        featured_df, feature_columns = feature_engineering.create_model_features(preprocessed_df)

        logger.debug(f"Feature engineering complete. Feature columns: {len(feature_columns)}")
        logger.debug(f"Feature engineering completed in {time.time() - step_start:.3f}s")



        # Step 4: Column Alignment - Ensure model compatibility
        logger.debug("Aligning columns with training data...")
        step_start = time.time()

        # Safety check: Explicitly remove 'is_anomaly' column if present
        if 'is_anomaly' in featured_df.columns:
            logger.warning("Found 'is_anomaly' column in FEATURED DataFrame - removing to prevent data leakage")
            featured_df = featured_df.drop(columns=['is_anomaly'])

        final_df = align_columns(featured_df, training_columns)

        # Double-check that 'is_anomaly' is not in final DataFrame
        if 'is_anomaly' in final_df.columns:
            logger.error("'is_anomaly' column still present in FINAL DataFrame - removing")
            final_df = final_df.drop(columns=['is_anomaly'])

        logger.debug(f"Final DataFrame shape: {final_df.shape}")
        logger.debug(f"Final DataFrame columns: {list(final_df.columns)}")
        logger.debug(f"Column alignment completed in {time.time() - step_start:.3f}s")



        # Step 5: Model Inference - Run anomaly detection
        logger.debug("Running model inference...")
        step_start = time.time()
        
        if model is not None:
            # Get raw anomaly scores. Lower score means more anomalous.
            anomaly_scores = model.score_samples(final_df)
            anomaly_score = anomaly_scores[0]  # Get the score for this single transaction
            
            # Get the contamination rate from the model
            contamination_rate = contamination_param
            
            # Calculate the threshold based on the contamination rate
            # This determines the cutoff for what is considered an anomaly.
            threshold = np.percentile(anomaly_scores, contamination_rate * 100)
            
            # Classify the transaction as anomaly (True) or normal (False) based on the threshold
            is_anomaly = anomaly_score <= threshold
            
            logger.info(f"Anomaly detection complete. Score: {anomaly_score:.4f}, Threshold: {threshold:.4f}, Is anomaly: {is_anomaly}")
            logger.debug(f"Model inference completed in {time.time() - step_start:.3f}s")

            # Step 6: SHAP Analysis - Generate explainability
            logger.debug("Generating SHAP values for explainability...")
            step_start = time.time()
            shap_values_json = generate_shap_values(model, final_df)
            logger.debug("SHAP values generated successfully")
            logger.debug(f"SHAP analysis completed in {time.time() - step_start:.3f}s")

            # Compile final results
            result = {
                'is_anomaly': bool(is_anomaly),
                'anomaly_score': float(anomaly_score),
                'shap_values_json': shap_values_json
            }
        else:
            logger.error("Model is None, cannot perform inference")
            result = _get_fallback_result()
        
        # Log successful completion
        total_time = time.time() - start_time
        logger.info(f"Analysis completed successfully for transaction {transaction.transaction_id} in {total_time:.3f}s")
        return result
        
    except Exception as e:
        # Comprehensive error handling with timing information
        total_time = time.time() - start_time
        logger.error(f"Error in anomaly detection for transaction {transaction.transaction_id} after {total_time:.3f}s: {e}", exc_info=True)
        return _get_fallback_result()

def _get_fallback_result() -> Dict[str, Any]:
    """Returns a standardized fallback result when model analysis fails.
    
    **Purpose:** Ensures system resilience by providing consistent fallback behavior.
    
    Returns:
        dict: Standardized fallback result with safe default values.
    """
    return {
        'is_anomaly': False,
        'anomaly_score': 0.5,
        'shap_values_json': json.dumps({
            'values': [],
            'base_values': 0.5,
            'feature_names': []
        })
    } 