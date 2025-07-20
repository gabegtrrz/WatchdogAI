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
import uuid
from . import preprocessing
from . import feature_engineering
from apps.core.models import Transaction, AnalysisReport
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


def run_complete_analysis(transactions_qs: QuerySet, contamination: float = 0.05, analysis_run_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
    """
    Run the complete anomaly detection pipeline for all selected transactions.

    **Process:**
    0. Model files already loaded.

    1. Convert the transaction data to a DataFrame
    2. Extract labels and remove is_anomaly column if present
    3. Preprocesses the data
    4. Generates features (using the training columns)
    5. Aligns columns with training data
    6. Performs anomaly detection
    7. Saves the results for each transaction into an AnalysisReport

    Args:
        transactions_qs: QuerySet of transactions to analyze.
        contamination: The proportion of outliers in the data set.
        analysis_run_id: UUID for the analysis run.

    Returns:
        A dictionary containing the results of the analysis.
    """

    start_time = time.time()
    logger.info(f"Starting anomaly analysis for {transactions_qs.count()} transactions.")
    logger.debug(f"Contamination parameter: {contamination}")

    try:
        ### 1. Convert the transaction data to a DataFrame
        step_start = time.time()
        if not model_loaded:
            raise ValueError("Model files not found. Please run the training script first.")

        raw_df = preprocessing.get_transaction_dataframe(transactions_qs)
        logger.info(f"Raw data converted to DataFrame in {time.time() - step_start:.2f} seconds")
        
        ### 2. Extract labels and remove is_anomaly column if present
        # This matches the evaluate_model.py flow
        if 'is_anomaly' in raw_df.columns:
            logger.info("Removing is_anomaly column from raw data for inference")
            raw_df = raw_df.drop('is_anomaly', axis=1)
        
        ### 3. Preprocess the data
        cleaned_df = preprocessing.clean_raw_data(raw_df)
        
        step_start = time.time()
        logger.info(f"Preprocessing completed in {time.time() - step_start:.2f} seconds")

        ### 4. Generate features
        featured_df, _ = feature_engineering.create_features(cleaned_df)

        ### 5. Align columns with the model's training columns (IMPROVED)
        training_columns_copy = training_columns.copy()
        final_df = _prepare_features_for_prediction(featured_df, training_columns_copy)
        del training_columns_copy  # Clean up the copy after use
        

        
        # 6. Perform anomaly detection with sophisticated contamination handling
        prediction_results = _get_predictions_and_scores(final_df, contamination)
        
        if prediction_results is None:
            raise ValueError("Anomaly detection failed, received no results (None).")
        
        predicted_labels, anomaly_scores, threshold = prediction_results

        # Step 7: SHAP Analysis - Generate explainability
        logger.debug("Generating SHAP values for explainability...")
        step_start = time.time()
        
        shap_values = generate_shap_values(model, final_df)
        # shape: (n_samples, n_features)

        logger.debug("SHAP values generated successfully")
        logger.info(f"SHAP values generated in {time.time() - step_start:.2f} seconds")

        
        # 8. Unpack SHAP and Save to Database
        if not analysis_run_id:
            raise ValueError("Analysis run ID is required")

        transactions_list = list(transactions_qs)
        reports_to_create = []

        for i, transaction in enumerate(transactions_list):
            step_start = time.time()
            
            if shap_values is not None:
                shap_values_for_transaction = dict(zip(final_df.columns, shap_values[i].tolist()))
                # shap_values[i] gets the SHAP values for the i-th transaction
                # .tolist() converts the numpy array to a Python list
                # zip() pairs each column name with its corresponding SHAP value
                # dict() creates a dictionary from these pairs
            else:
                shap_values_for_transaction = {}

            reports_to_create.append(
                AnalysisReport(
                    transaction=transaction,
                    analysis_run_id=analysis_run_id,
                    is_anomaly=bool(predicted_labels[i]),
                    anomaly_score=anomaly_scores[i],
                    shap_values=shap_values_for_transaction,
                    contamination_param=contamination,
                )
            )

        # Use Django's bulk_create method
        AnalysisReport.objects.bulk_create(reports_to_create)  # type: ignore
        logger.info(f"Successfully saved {len(reports_to_create)} analysis reports.")

        # Compile final results
        results = {
            "status": "success",
            "analysis_run_id": str(analysis_run_id),
            "transactions_analyzed": len(transactions_list),
            "anomalies_found": int(np.sum(predicted_labels)),
            "threshold_used": float(threshold),
            "contamination_rate": float(contamination)
        }

        # Log successful completion
        total_time = time.time() - start_time
        logger.info(f"Analysis completed successfully in {total_time:.3f}s")
        return results

    except Exception as e:
        # Comprehensive error handling with timing information
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }

def _prepare_features_for_prediction(featured_df: pd.DataFrame, feature_columns_list: List[str]) -> pd.DataFrame:
    """
    Prepare features for model prediction with proper column handling.
    
    **Process:**
    1. Removes extra columns not in training data
    2. Adds missing columns with default values
    3. Ensures exact column match with training data in correct order
    4. Validates DataFrame type safety
    
    Args:
        featured_df: DataFrame with engineered features
        feature_columns_list: List of feature columns from feature engineering
        
    Returns:
        pd.DataFrame: Properly aligned DataFrame for model prediction
    """
    features_df = featured_df.copy()
    
    # Store original index information for restoration
    original_index = features_df.index.copy()
    original_index_name = features_df.index.name
    
    # Debug column information
    logger.info(f'Columns after feature engineering: {list(features_df.columns)}')
    logger.info(f'Training columns: {list(feature_columns_list)}')
    
    # Safety check: Ensure is_anomaly is not in features
    if 'is_anomaly' in features_df.columns:
        logger.error('is_anomaly column still present in features! Removing it...')
        features_df = features_df.drop('is_anomaly', axis=1)
    
    # Handle column mismatches - FIXED: Remove redundant logic
    missing_columns = set(feature_columns_list) - set(features_df.columns)
    extra_columns = set(features_df.columns) - set(feature_columns_list)
    
    logger.info(f'Missing columns: {missing_columns}')
    logger.info(f'Extra columns: {extra_columns}')
    
    # Remove extra columns first
    if extra_columns:
        logger.info(f'Removing extra columns: {extra_columns}')
        features_df = features_df.drop(columns=list(extra_columns))
    
    # Add missing columns with default value
    if missing_columns:
        logger.warning(f'Missing columns in prediction data: {missing_columns}')
        for col in missing_columns:
            features_df[col] = 0.0  # Default value for missing features
    
    # Final reordering to match training order exactly
    features_df = features_df[feature_columns_list]
    
    logger.info(f'Features shape for prediction: {features_df.shape}')
    logger.info(f'Final feature columns (in training order): {list(features_df.columns)}')
    
    # Ensure we return a DataFrame, not a Series
    if isinstance(features_df, pd.Series):
        features_df = features_df.to_frame().T
        # Restore index for Series case
        if features_df.index.name != original_index_name:
            features_df.index = original_index
            features_df.index.name = original_index_name
            logger.info("Restored original index after converting to DataFrame")
    
    return features_df

# ============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _get_predictions_and_scores(final_df: pd.DataFrame, contamination: float = 0.05) -> Optional[tuple[np.ndarray, np.ndarray, float]]:
    """
    Performs anomaly detection on the final DataFrame using the trained Isolation Forest model.
    
    **Process:**
    1. Uses the loaded model to calculate anomaly scores for each transaction
    2. Determines threshold based on contamination rate (percentage of outliers)
    3. Classifies transactions as anomalous (1) or normal (0) based on threshold
    
    Args:
        final_df: The final DataFrame with all features aligned to training columns.
        contamination: The proportion of outliers expected in the dataset (default: 0.05).
        
    Returns:
        Optional[tuple]: (predicted_labels, anomaly_scores, threshold)
            - predicted_labels: np.ndarray of 1s (anomaly) and 0s (normal)
            - anomaly_scores: np.ndarray of raw anomaly scores (lower = more anomalous)
            - threshold: float of the calculated threshold value
    """

    try:
        if model is not None:
            logger.info('Getting predictions and anomaly scores from trained model...')
            
            # Get raw anomaly scores (lower score means more anomalous)
            anomaly_scores = model.score_samples(final_df)
            
            # Determine contamination rate for thresholding
            
            try:
                # Use the provided contamination parameter if it's valid
                if 0.01 <= contamination <= 0.5:
                    logger.info(f"Using provided contamination rate: {contamination}")
                else:
                    # If invalid, fall back to model's default
                    contamination = model.contamination
                    logger.warning(f"Invalid contamination parameter '{contamination}'. "
                                f"Falling back to model's default.")
                
            except (ValueError, TypeError):
                logger.warning(f"Invalid contamination parameter '{contamination}'. "
                                f"Falling back to model's default.")
                
                # Fallback to model's default contamination rate
                contamination = model.contamination

            
            # Calculate threshold based on contamination rate
            threshold = np.percentile(anomaly_scores, contamination * 100)

            # Classify samples as anomalies (1) or normal (0)
            predicted_labels = (anomaly_scores <= threshold).astype(int)

            logger.info(f'Predicted anomalies: {np.sum(predicted_labels)} out of {len(predicted_labels)}')
            logger.info(f'Contamination rate: {contamination:.4f}')
            logger.info(f'Threshold: {threshold:.4f}')

            return predicted_labels, anomaly_scores, threshold

        else:
            logger.error("Model is None, cannot perform inference")
            return None
    
    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}", exc_info=True)
        return None


def generate_shap_values(model: Any, final_df: pd.DataFrame) -> Optional[np.ndarray]:
    """
    Generate SHAP values for model explainability and feature importance analysis.
    
    **Process:**
    1. Creates TreeExplainer for the Isolation Forest model.
    2. Calculates SHAP values for the input data.
    3. Returns numpy array with SHAP values for each sample-feature combination.
    
    **Error Handling:** Returns None if SHAP calculation fails.
    
    Args:
        model: The trained Isolation Forest model.
        final_df: Preprocessed DataFrame ready for model inference.
        
    Returns:
        Optional[np.ndarray]: SHAP values array with shape (n_samples, n_features),
            where shap_values[i, j] is the SHAP value for the i-th sample and j-th feature.
            Returns None if calculation fails.
    """
    try:
        # Create SHAP explainer for tree-based model
        explainer = shap.TreeExplainer(model)
        df_copy = final_df.copy()
        shap_values = explainer.shap_values(df_copy) 
        # produces a NumPy array with the same shape as the input data
        # shap_values[i, j] is the SHAP value for the i-th sample and the j-th feature.

        # Interpretation:
        # A negative SHAP value indicates that the feature's value for that sample pushed the prediction score down, making the sample seem more anomalous.
        # A positive SHAP value indicates that the feature's value pushed the prediction score up, making the sample seem more normal.

        # Return structured SHAP explanation data
        return shap_values
        
    except Exception as e:
        logger.error(f"Error generating SHAP values: {e}", exc_info=True)
        return None


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
