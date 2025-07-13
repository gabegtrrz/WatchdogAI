"""
This service handles the initial, generic preprocessing of transaction data.

Responsibilities:
- Fetching data from the database.
- Basic cleaning and renaming.
- Correcting data types (e.g., to datetime).
- Handling initial missing values in raw fields.
"""
import pandas as pd
import numpy as np
from apps.core.models import Transaction

def get_transaction_dataframe():
    """
    Fetches all transactions and converts them into a pandas DataFrame.
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
    """
    # Rename for clarity
    df.rename(columns={'procurement_method__name': 'procurement_method'}, inplace=True)

    # Fill initial missing numerical values with the median
    numerical_features = ['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']
    for col in numerical_features:
        if df[col].isnull().any():
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)

    # Convert all date columns to datetime objects, coercing errors
    date_features = [
        'transaction_date', 'invitation_to_bid_posting_date', 'bid_submission_deadline',
        'bid_opening_date', 'notice_of_award_date', 'contract_signing_date'
    ]
    for col in date_features:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    return df