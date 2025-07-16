"""
Handles initial, generic preprocessing of transaction data before
feature engineering. Focuses on data quality and preparation rather than anomaly-specific transformations.

Designed to be generic and reusable across different
anomaly detection approaches.

Performs three main preprocessing steps:
1. Data extraction - fetching raw transaction data from the database or CSV file
2. Basic cleaning - handling missing values and data type conversions
3. Data validation - ensuring data quality for downstream processing
"""
import pandas as pd
import numpy as np
import logging
from django.apps import apps
from typing import Union, Optional
from pathlib import Path
from apps.transaction_management.services import process_transaction_csv

# Configure logging for this module
logger = logging.getLogger(__name__)

def get_transaction_dataframe():
    """
    Fetches all transactions and converts them into a pandas DataFrame.
    
    Extracts raw transaction data from the database and structures it for preprocessing.
    Serves as data extraction layer between the database and the preprocessing pipeline.
    
    Returns:
        pd.DataFrame: Raw transaction data with all necessary columns for preprocessing and feature engineering.
                     Indexed by transaction_id for easy identification.
    
    Database Fields Extracted:
        - transaction_id: Primary key for identification
        - quantity: Number of items purchased
        - unit_purchase_price: Price per unit
        - total_purchase_price: Total transaction value
        - approved_budget: Budget limit for the transaction
        - procurement_method__name: Method used for procurement
        - supplier: Supplier name/identifier
        - transaction_date: Date of the transaction
        - invitation_to_bid_posting_date: When bidding was announced
        - bid_submission_deadline: Deadline for bid submissions
        - bid_opening_date: When bids were opened
        - notice_of_award_date: When award decision was made
        - contract_signing_date: When contract was signed
    """
    logger.info("Fetching transaction data from database...")
    try:
        # Get the Transaction model dynamically to avoid import issues
        Transaction = apps.get_model('core', 'Transaction')
        transactions = Transaction.objects.all().values(
            'transaction_id',
            'quantity',
            'unit_purchase_price',
            'total_purchase_price',
            'approved_budget',
            'procurement_method__name',
            'supplier',
            'transaction_date',
            'invitation_to_bid_posting_date',
            'bid_submission_deadline',
            'bid_opening_date',
            'notice_of_award_date',
            'contract_signing_date'
        )
        df = pd.DataFrame.from_records(transactions)
        df.set_index('transaction_id', inplace=True)
        logger.info(f"Successfully loaded {len(df)} transactions from database")
        logger.debug(f"DataFrame shape: {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error fetching transaction data from database: {e}", exc_info=True)
        raise

def get_transaction_dataframe_from_csv(csv_path: Union[str, Path]) -> pd.DataFrame:
    """
    Processes a CSV file and converts it into a pandas DataFrame for preprocessing.
    
    Uses the existing process_transaction_csv function to validate and clean the data,then converts the validated data into a DataFrame format compatible with the preprocessing pipeline.
    
    Args:
        csv_path: Path to the CSV file to process
        
    Returns:
        pd.DataFrame: Raw transaction data with all necessary columns for preprocessing and feature engineering.
                     Indexed by transaction_id for easy identification.
                     
    Raises:
        FileNotFoundError: If the CSV file doesn't exist
        ValueError: If the CSV file contains validation errors
    """
    logger.info(f"Processing CSV file: {csv_path}")
    csv_path = Path(csv_path)
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    try:
        # Read the CSV file as a file stream
        with open(csv_path, 'rb') as file_stream:
            # Use the existing CSV processing function
            valid_data, validation_errors = process_transaction_csv(file_stream)
        
        # Check for validation errors
        if validation_errors:
            error_messages = []
            for error in validation_errors:
                if 'row' in error:
                    error_messages.append(f"Row {error['row']}: {error['errors']}")
                else:
                    error_messages.append(f"{error['type']}: {error['message']}")
            logger.error(f"CSV validation failed: {error_messages}")
            raise ValueError(f"CSV validation failed:\n" + "\n".join(error_messages))
        
        if not valid_data:
            logger.error("No valid data found in CSV file")
            raise ValueError("No valid data found in CSV file")
        
        # Convert the validated data to DataFrame
        df = pd.DataFrame.from_records(valid_data)
        
        # Set transaction_id as index if it exists, otherwise create one
        df.index = range(len(df))
        
        # Ensure procurement_method is properly formatted for consistency
        if 'procurement_method' in df.columns and df['procurement_method'].dtype == 'object':
            # Convert procurement method objects to their names
            df['procurement_method__name'] = df['procurement_method'].apply(
                lambda x: x.name if hasattr(x, 'name') else str(x)
            )
            df.drop('procurement_method', axis=1, inplace=True)
        
        logger.info(f"Successfully processed CSV file. DataFrame shape: {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Error processing CSV file {csv_path}: {e}", exc_info=True)
        raise

def get_dataframe(source: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """
    Unified function to get transaction data from either database or CSV file.
    
    Args:
        source: Optional path to CSV file. If None, fetches from database.
        
    Returns:
        pd.DataFrame: Raw transaction data ready for preprocessing
    """
    if source is None:
        logger.debug("No source specified, fetching from database")
        return get_transaction_dataframe()
    else:
        logger.debug(f"Source specified: {source}, fetching from CSV")
        return get_transaction_dataframe_from_csv(source)

def clean_raw_data(df: pd.DataFrame):
    """
    Performs initial cleaning and type conversion on the raw DataFrame.
    
    Applies basic data quality improvements to prepare the dataset for feature engineering. 
    Drops the 'is_anomaly' column if present to prevent data leakage.
    Includes handling missing values, converting data types, and ensuring data consistency.
    
    Args:
        df (pd.DataFrame): Raw transaction data from get_dataframe()
    
    Returns:
        pd.DataFrame: Cleaned and preprocessed data ready for feature engineering
    
    Cleaning Steps:
        A. Drop 'is_anomaly' column: Prevents data leakage in model training
        B. Column Renaming: Standardize column names for clarity
        C. Missing Value Imputation: Handle missing numerical values
        D. Data Type Conversion: Convert date strings to datetime objects
    """
    logger.info("Starting data cleaning process...")
    logger.debug(f"Input DataFrame shape: {df.shape}")
    
    try:
        # --- A. Drop 'is_anomaly' column to prevent data leakage ---
        # The 'is_anomaly' column should be extracted before preprocessing to avoid data leakage
        # This ensures the model doesn't see the target variable during training
        if 'is_anomaly' in df.columns:
            logger.info("Dropping 'is_anomaly' column to prevent data leakage")
            df = df.drop('is_anomaly', axis=1)
            logger.debug(f"DataFrame shape after dropping 'is_anomaly': {df.shape}")
        
        # --- B. Column Renaming ---
        # Standardize column names for consistency across the pipeline
        # Renames the Django ORM field name to more intuitive name that matches the expected column name in feature engineering
        logger.debug("Renaming columns for consistency...")
        df.rename(columns={'procurement_method__name': 'procurement_method'}, inplace=True)

        # --- C. Missing Value Imputation ---
        # Handle missing numerical values by imputing with MEDIAN values
        # Missing values in numerical features can occur due to data entry errors
        # or incomplete records. Using MEDIAN imputation preserves data distribution while ensuring all numerical features have complete values. robust to outliers.
        # This conservative approach doesn't introduce artificial patterns.
        logger.debug("Handling missing values in numerical features...")
        numerical_features = ['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']
        for col in numerical_features:
            if col in df.columns and df[col].isnull().sum() > 0:
                missing_count = df[col].isnull().sum()
                median_val = df[col].median()
                df[col].fillna(median_val, inplace=True)
                logger.debug(f"Imputed {missing_count} missing values in {col} with median: {median_val}")

        # --- D. Data Type Conversion ---
        # Convert all date columns to datetime objects for analysis
        # essential for detecting timing-based anomalies such as end-of-year rush spending or suspicious procurement timing.
        # Using errors='coerce' handles invalid date formats gracefully by converting them to NaT (Not a Time) rather than failing.
        logger.debug("Converting date columns to datetime...")
        date_features = [
            'transaction_date', 'invitation_to_bid_posting_date', 'bid_submission_deadline',
            'bid_opening_date', 'notice_of_award_date', 'contract_signing_date'
        ]
        for col in date_features:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                invalid_dates = df[col].isna().sum()
                if invalid_dates > 0:
                    logger.warning(f"Found {invalid_dates} invalid dates in column {col}")

        logger.info("Data cleaning completed successfully")
        logger.debug(f"Output DataFrame shape: {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Error during data cleaning: {e}", exc_info=True)
        raise

def extract_labels(df: pd.DataFrame):
        """
        Extract labels
        
        Args:
            df: DataFrame that may contain 'is_anomaly' column
            
        Returns:
            true_labels: numpy array of binary labels (1 for anomaly, 0 for normal) or None
        """
        df_copy = df.copy()
        true_labels = None
        
        # Check if 'is_anomaly' column exists
        if 'is_anomaly' in df_copy.columns:
            logger.info("'is_anomaly' column found in dataset")
            
            # Extract true labels before dropping the column
            true_labels_raw = df_copy['is_anomaly'].values
            # Convert to binary: 1 for anomaly, 0 for normal
            true_labels = (true_labels_raw == 1).astype(int)
            
            # Log label distribution
            if true_labels is not None:
                label_counts = np.bincount(true_labels)
                logger.info(f"True labels distribution: Normal={label_counts[0]}, Anomalies={label_counts[1] if len(label_counts) > 1 else 0}")
        else:
            logger.info("'is_anomaly' column not found in dataset - proceeding with  training")
            training_data = df_copy
            true_labels = None
        
        return true_labels