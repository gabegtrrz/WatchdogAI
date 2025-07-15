"""
This service orchestrates the anomaly detection pipeline using the separated
preprocessing and feature engineering services.
"""
import pandas as pd
from typing import Optional, Union
from pathlib import Path
from .preprocessing import get_dataframe, clean_raw_data
from .feature_engineering import create_model_features

def prepare_data_for_anomaly_detection(source: Optional[Union[str, Path]] = None):
    """
    Complete pipeline that combines preprocessing and feature engineering.
    
    Args:
        source: Optional path to CSV file. If None, fetches from database.
        
    Returns:
    - DataFrame ready for anomaly detection
    - List of feature column names
    """
    # Step 1: Get and preprocess raw data
    raw_df = get_dataframe(source)
        # get_dataframe() is in preprocessing.py
        # if source == None, then it will fetch from database
        # if source == path, then it will fetch from csv

    if raw_df.empty:
        raise ValueError("No data found to prepare for anomaly detection")
    cleaned_df = clean_raw_data(raw_df)
    
    # Step 2: Engineer advanced features
    final_df, feature_columns = create_model_features(cleaned_df)
    
    return final_df, feature_columns

def detect_anomalies(df: pd.DataFrame, feature_columns: list):
    """
    Placeholder for anomaly detection logic.
    This would use the prepared DataFrame and feature columns.
    """
    # This is where your anomaly detection model would be applied
    # For now, just return the prepared data
    return df[feature_columns] 