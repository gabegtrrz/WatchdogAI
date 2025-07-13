"""
Handles initial, generic preprocessing of transaction data before
feature engineering. Focuses on data quality and preparation rather than anomaly-specific transformations.

Designed to be generic and reusable across different
anomaly detection approaches.

Performs three main preprocessing steps:
1. Data extraction - fetching raw transaction data from the database
2. Basic cleaning - handling missing values and data type conversions
3. Data validation - ensuring data quality for downstream processing
"""
import pandas as pd
import numpy as np
from apps.core.models import Transaction

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
    return df

def clean_raw_data(df: pd.DataFrame):
    """
    Performs initial cleaning and type conversion on the raw DataFrame.
    
    Applies basic data quality improvements to prepare the dataset for feature engineering. Includes handling missing values, converting data types, and ensuring data consistency.
    
    Args:
        df (pd.DataFrame): Raw transaction data from get_transaction_dataframe()
    
    Returns:
        pd.DataFrame: Cleaned and preprocessed data ready for feature engineering
    
    Cleaning Steps:
        A. Column Renaming: Standardize column names for clarity
        B. Missing Value Imputation: Handle missing numerical values
        C. Data Type Conversion: Convert date strings to datetime objects
    """
# --- A. Column Renaming ---
    # Standardize column names for consistency across the pipeline
        # Renames the Django ORM field name to more intuitive name that matches the expected column name in feature engineering
    df.rename(columns={'procurement_method__name': 'procurement_method'}, inplace=True)

# --- B. Missing Value Imputation ---
    # Handle missing numerical values by imputing with MEDIAN values
        # Missing values in numerical features can occur due to data entry errors
        # or incomplete records. Using MEDIAN imputation preserves data distribution while ensuring all numerical features have complete values. robust to outliers.

        # This conservative approach doesn't introduce artificial patterns.

    numerical_features = ['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']
    for col in numerical_features:
        if df[col].isnull().any():
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)

# --- C. Data Type Conversion ---
    # Convert all date columns to datetime objects for analysis
        # essential for detecting timing-based anomalies such as end-of-year rush spending or suspicious procurement timing.
        # Using errors='coerce' handles invalid date formats gracefully by converting them to NaT (Not a Time) rather than failing.
    date_features = [
        'transaction_date', 'invitation_to_bid_posting_date', 'bid_submission_deadline',
        'bid_opening_date', 'notice_of_award_date', 'contract_signing_date'
    ]
    for col in date_features:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    return df