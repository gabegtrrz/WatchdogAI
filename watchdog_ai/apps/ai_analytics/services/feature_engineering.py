"""
This service engineers advanced features for the anomaly detection model.

It takes a preprocessed DataFrame and creates features engineered to help
detect 'specific' irregularities in procurement data.
"""
import pandas as pd
import numpy as np

def create_model_features(df: pd.DataFrame):
    """
    Engineers features from the preprocessed DataFrame.

    Returns a tuple of:
    - The final DataFrame with all engineered features.
    - A list of the final feature column names.
    """
    # --- A. Date-Based Features ---
    # Targets: 'EndOfYearRush', 'WeekendActivity', 'CompressedTimeline', 'BackdatedDocuments'
    df['contract_signing_dayofweek'] = df['contract_signing_date'].dt.dayofweek
    df['bid_opening_dayofweek'] = df['bid_opening_date'].dt.dayofweek
    df['transaction_month'] = df['transaction_date'].dt.month
    df['bidding_period_days'] = (df['bid_submission_deadline'] - df['invitation_to_bid_posting_date']).dt.days
    df['award_decision_days'] = (df['notice_of_award_date'] - df['bid_opening_date']).dt.days
    df['contract_signing_days'] = (df['contract_signing_date'] - df['notice_of_award_date']).dt.days
    df['total_procurement_cycle_days'] = (df['contract_signing_date'] - df['invitation_to_bid_posting_date']).dt.days

    # --- B. Price & Budget Features ---
    # Targets: 'BidCeilingCollusion', 'PriceExceedsBudget'
    safe_budget = df['approved_budget'].replace(0, np.nan)
    df['budget_utilization_ratio'] = df['total_purchase_price'] / safe_budget

    # --- C. Categorical & Interaction Features ---
    # Targets: 'FictitiousWinner', 'FavoredSupplier', 'SuspiciousOverpricing'
    supplier_freq_map = df['supplier'].value_counts(normalize=True).to_dict()
    df['supplier_frequency'] = df['supplier'].map(supplier_freq_map)
    epsilon = 1e-6
    df['price_per_supplier_freq'] = df['unit_purchase_price'] / (df['supplier_frequency'] + epsilon)

    # --- Final Imputation & Cleanup ---
    engineered_features = [
        'contract_signing_dayofweek', 'bid_opening_dayofweek', 'transaction_month',
        'bidding_period_days', 'award_decision_days', 'contract_signing_days', 'total_procurement_cycle_days',
        'budget_utilization_ratio', 'supplier_frequency', 'price_per_supplier_freq'
    ]
    for col in engineered_features:
        if df[col].isnull().any():
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)

    # --- One-Hot Encoding ---
    df_processed = pd.get_dummies(df, columns=['procurement_method'], prefix=['procurement_method'], dummy_na=True)

    # --- Final Feature Set ---
    base_numerical_features = ['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']
    one_hot_cols = [col for col in df_processed.columns if 'procurement_method_' in col]
    final_feature_columns = base_numerical_features + engineered_features + one_hot_cols
    
    # Ensure all columns exist in the final DataFrame
    final_feature_columns = [col for col in final_feature_columns if col in df_processed.columns]
    df_final = df_processed[final_feature_columns].copy()

    return df_final, final_feature_columns