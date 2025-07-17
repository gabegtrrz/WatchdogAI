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

def run_complete_analysis(, contamination_param: float = 0.05) -> Dict[str, Any]:
    """
    Run the complete anomaly detection pipeline for selected transactions.

    **Process:**
    1. Loads the trained model and training columns
    2. Converts the transaction data to a DataFrame
    3. Preprocesses the data
    4. Generates features
    5. Performs anomaly detection

    Args:
        transactions to analyze: List[Transaction]
        contamination_param: float (default = 0.05) # make available to str 'auto' later

        
    Returns:
        Dict[str, Any]: Dictionary containing the results of the analysis
    """

    
    





# ============================================================================
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

