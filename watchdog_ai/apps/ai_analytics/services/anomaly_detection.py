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
from django.db.models.query import QuerySet

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

def _load_model_files():
    """Loads the trained Isolation Forest model and training columns.
    
    **Process:**
    1. Checks if model files exist on disk
    2. Loads the trained model using joblib
    3. Loads the training column specifications
    4. Sets global state variables for model availability
    
    Error Handling: Sets fallback state if files are missing or corrupted.
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


def run_complete_analysis(transactions_qs: QuerySet, contamination: float = 0.05) -> Dict[str, Any]:
    """
    Run the complete anomaly detection pipeline for all selected transactions.

    **Process:**
    0. Model files already loaded.

    1. Convert the transaction data to a DataFrame
    2. Preprocesses the data
    3. Generates features (using the training columns)
    5. Performs anomaly detection

    Args:
        transactions_qs: QuerySet of transactions to analyze.
        contamination: float (default = 0.05) # make available to str 'auto' later

        
    Returns:
    """

    start_time = time.time()
    logger.info(f"Starting anomaly analysis for {len(transactions_qs)} transactions.")
    logger.info(f"Contamination parameter: {contamination}")

    try:
        # 1. Convert the transaction data to a DataFrame
        raw_df = preprocessing.get_transaction_dataframe(transactions_qs)
        step_start = time.time()
        if not model_loaded:
            raise ValueError("Model files not found. Please run the training script first.")
        
        # 2. Preprocess the data
        cleaned_df = preprocessing.clean_raw_data(raw_df)
        step_start = time.time()
        logger.info(f"Preprocessing completed in {step_end - step_start:.2f} seconds")

        # 3. Generate features
        featured_df, feature_columns_list = feature_engineering.create_features(cleaned_df)

        # 4. Align columns with the model's training columns
        final_df = featured_df[feature_columns_list] #reorders columns to match the order of the training columns and discards columns that are no longer needed.

        # 5. Perform anomaly detection
        anomaly_labels, anomaly_scores = analyze_anomalies(final_df, contamination)
        step_start = time.time()

        # Step 6: SHAP Analysis - Generate explainability
        logger.debug("Generating SHAP values for explainability...")
        step_start = time.time()

        shap_values_json = generate_shap_values(model, final_df)

        

        logger.debug("SHAP values generated successfully")
        logger.debug(f"SHAP analysis completed in {time.time() - step_start:.3f}s")


        # Compile final results
        results = {
            
        }

        # Log successful completion
        total_time = time.time() - start_time
        logger.info(f"Analysis completed successfully in {total_time:.3f}s")
        return results

    except Exception as e:
        # Comprehensive error handling with timing information
        total_time = time.time() - start_time
        return

# ============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def analyze_anomalies(final_df: pd.DataFrame, contamination: float=0.05):
    """
    Performs anomaly detection on the final DataFrame.
    
    Args:
        final_df: The final DataFrame with all features.
        
    Returns:
        np.ndarray: Array of 1s and 0s indicating anomalies.
    """

    try:
        if model is not None:
        # Get raw anomaly scores. Lower score means more anomalous.
            anomaly_scores = model.score_samples(final_df)
            
            # Calculate the threshold based on the contamination rate
            # This determines the cutoff for what is considered an anomaly.
            threshold = np.percentile(anomaly_scores, contamination * 100)
            
            # Classify the transaction as anomaly (True) or normal (False) based on the threshold
            predicted_labels = (anomaly_scores <= threshold).astype(int)

            
            logger.info(f'Predicted anomalies: {np.sum(predicted_labels)} out of {len(predicted_labels)} '
                   f'using contamination rate of {contamination:.4f} and threshold of {threshold:.4f}'
                   )

            return predicted_labels, anomaly_scores

        else:
            logger.error("Model is None, cannot perform inference")
            return None, None
    
    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}", exc_info=True)
        return None, None



def generate_shap_values(model: Any, final_df: pd.DataFrame):
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
        # produces a NumPy array with the same shape as the input data
        # shap_values[i, j] is the SHAP value for the i-th sample and the j-th feature.

        # Interpretation:
        # A negative SHAP value indicates that the feature's value for that sample pushed the prediction score down, making the sample seem more anomalous.
        # A positive SHAP value indicates that the feature's value pushed the prediction score up, making the sample seem more normal.

        # Return structured SHAP explanation data
        return shap_values
        
    except Exception as e:
        logger.error(f"Error generating SHAP values: {e}", exc_info=True)
        return


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
