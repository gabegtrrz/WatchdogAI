"""
This service orchestrates the anomaly detection pipeline using the separated
preprocessing and feature engineering services.
"""
import joblib
import json
import pandas as pd
import shap
from . import preprocessing
from . import feature_engineering
from apps.core.models import Transaction

# Load model and columns at module level for efficiency
MODEL_PATH = 'watchdog_ai/apps/ai_analytics/model_files/isolation_forest.joblib'
COLUMNS_PATH = 'watchdog_ai/apps/ai_analytics/model_files/training_columns.joblib'
model = joblib.load(MODEL_PATH)
training_columns = joblib.load(COLUMNS_PATH)

def run_complete_analysis(transaction: Transaction, contamination_param: float):
    """
    Orchestrates the full data pipeline for a single transaction.
    
    Args:
        transaction (Transaction): The Django model instance.
        contamination_param (float): The contamination parameter for the model.

    Returns:
        dict: A dictionary containing the analysis results.
    """
    # 1. Convert Django model to DataFrame
    transaction_df = model_to_dataframe(transaction)

    # 2. Preprocessing
    # Assuming preprocessing steps are adapted for a single transaction row
    preprocessed_df = preprocessing.clean_raw_data(transaction_df)

    # 3. Feature Engineering
    features_df, feature_columns = feature_engineering.create_model_features(preprocessed_df)

    # 4. Align columns with model's training columns
    final_df = align_columns(features_df, training_columns)

    # 5. Run Inference
    # The contamination of an Isolation Forest is set at training time.
    # The `contamination_param` is stored for record-keeping, but the model's
    # original behavior is used for prediction.
    
    anomaly_score = model.decision_function(final_df)[0]
    is_anomaly = model.predict(final_df)[0] == -1 # -1 means anomaly

    # 6. Generate SHAP values for explainability
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(final_df)
    
    # Convert shap values to a JSON serializable format
    shap_values_json = json.dumps({
        'values': shap_values[0].tolist(),
        'base_values': explainer.expected_value.tolist() if hasattr(explainer.expected_value, 'tolist') else explainer.expected_value,
        'feature_names': final_df.columns.tolist()
    })

    return {
        'is_anomaly': bool(is_anomaly),
        'anomaly_score': float(anomaly_score),
        'shap_values_json': shap_values_json
    }

def model_to_dataframe(transaction: Transaction) -> pd.DataFrame:
    """Converts a Transaction model instance to a pandas DataFrame."""
    # This dictionary must be comprehensive to match the columns
    # expected by the preprocessing and feature engineering steps.
    data = {
        'Description': [transaction.description],
        'Quantity': [transaction.quantity],
        'Unit Price': [transaction.unit_price],
        'Total Purchase Price': [transaction.total_purchase_price],
        'Supplier Name': [transaction.supplier_name],
        'Procurement Method': [transaction.procurement_method.name],
        'Contract Date': [pd.to_datetime(transaction.contract_date)],
        'Delivery Date': [pd.to_datetime(transaction.delivery_date)],
        # Add other relevant fields...
    }
    return pd.DataFrame(data)

def align_columns(df: pd.DataFrame, training_columns: list) -> pd.DataFrame:
    """Aligns DataFrame columns to match the model's training columns."""
    # Add missing columns with a default value of 0
    for col in training_columns:
        if col not in df.columns:
            df[col] = 0
    # Return the dataframe with columns in the same order as training
    return df[training_columns] 