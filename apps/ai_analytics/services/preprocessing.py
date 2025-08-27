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
from django.db.models.query import QuerySet
from typing import Union, Optional
from pathlib import Path
from apps.transaction_management.services import process_transaction_csv
from .feature_engineering import INITIAL_COLUMNS_TO_USE

# Configure logging for this module
logger = logging.getLogger(__name__)

from django.db.models import F, QuerySet
from django.apps import apps
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_transaction_dataframe(transactions_qs: Optional[QuerySet] = None) -> pd.DataFrame:
    """
    Fetches transactions and converts them into a pandas DataFrame.
    If a queryset is provided, it uses it. Otherwise, it fetches all transactions.
    
    Extracts raw transaction data from the database and structures it for preprocessing.
    Serves as a data extraction layer between the database and the preprocessing pipeline.

    Args:
        transactions_qs (Optional[QuerySet]): A Django QuerySet of Transaction objects.
    
    Returns:
        pd.DataFrame: Raw transaction data with all necessary columns for preprocessing and feature engineering.
                      Indexed by transaction_id for easy identification.
    """
    logger.info("Fetching transaction data from the database...")
    
    try:
        Transaction = apps.get_model('core', 'Transaction')
        if transactions_qs is None:
            transactions_qs = Transaction.objects.all()

        if not isinstance(transactions_qs, QuerySet):
            raise TypeError("The provided transactions_qs must be a Django QuerySet.")

        # --- COLUMN GENERATION ---
        # 1. Get all concrete field  names directly from the model.
        model_fields_list = INITIAL_COLUMNS_TO_USE.copy()

        # 2 remove the foreign key field 'procurement_method' from the list.
        if 'procurement_method' in model_fields_list:
            model_fields_list.remove('procurement_method')

        # 3. Annotate (add new col) to the qs, to get the related name.
        # !! trying to get 'procurement_method' only gets procurement_method 'id'
        annotated_qs = transactions_qs.annotate(
            procurement_method_name=F('procurement_method__name') #must be diff name because we're annotating (adding new col)
            # F() expression tells Django to get the value directly from a database field rather than using a static value
        )

        # 4. 
        final_columns_list = model_fields_list + ['procurement_method_name'] #final list of columns for the .values() query.
       

        transactions_list = list(annotated_qs.values(*final_columns_list))

        if not transactions_list:
            logger.info("No transactions found to load into DataFrame.")
            return pd.DataFrame()

        df = pd.DataFrame.from_records(transactions_list)
        
        # Set index if transaction_id was fetched
        if 'transaction_id' in df.columns:
            df.set_index('transaction_id', inplace=True)
        
        # !! Rename the annotated column to its final name.
        df.rename(
            columns={'procurement_method_name': 'procurement_method'}, 
            inplace=True
        )

        logger.info(f"Successfully loaded {len(df)} transactions from the database.")
        logger.debug(f"DataFrame shape: {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching transaction data from the database: {e}", exc_info=True)
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
            # Add debugging information
            logger.debug(f"File size: {csv_path.stat().st_size} bytes")
            
            # Read the first few lines to debug column headers
            file_stream.seek(0)
            first_lines = file_stream.read(1000).decode('utf-8').split('\n')[:3]
            logger.debug(f"First few lines of CSV:")
            for i, line in enumerate(first_lines):
                logger.debug(f"Line {i+1}: {repr(line)}")
            
            # Reset file stream position
            file_stream.seek(0)
            
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
        
        # Map column names for consistency with feature engineering
        # CSV data uses procurement_method_name, but feature engineering expects procurement_method
        if 'procurement_method_name' in df.columns:
            df.rename(columns={'procurement_method_name': 'procurement_method'}, inplace=True)
        
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
                df[col] = df[col].infer_objects(copy=False)
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
                # Store original values before conversion to identify invalid dates
                original_values = df[col].copy()
                df[col] = pd.to_datetime(df[col], errors='coerce')
                invalid_dates = df[col].isna().sum()
                if invalid_dates > 0:
                    # Find the original values that became NaT
                    invalid_mask = df[col].isna()
                    invalid_original_values = original_values[invalid_mask]
                    unique_invalid_values = pd.Series(invalid_original_values).unique()
                    logger.warning(f"Found {invalid_dates} invalid dates in column {col}. Coerced to NaT.")
                    logger.warning(f"Invalid date values in {col}: {unique_invalid_values.tolist()}")

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