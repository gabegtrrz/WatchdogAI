"""
Feature Engineering Service for Anomaly Detection

This service engineers features for the anomaly detection model by transforming
raw procurement data into meaningful features that help identify specific irregularities.

The service creates three main categories of features:
1. Date-based features - to detect timing anomalies
2. Price & budget features - to detect financial irregularities  
3. Categorical & interaction features - to detect supplier-related anomalies

Each feature is designed to target specific anomaly types in procurement data.
"""
import pandas as pd
import numpy as np

def create_model_features(df: pd.DataFrame):
    """
    Engineers features from the preprocessed DataFrame for anomaly detection.
    
    Transforms raw procurement data into engineered features that
    help the anomaly detection model identify specific types of irregularities.
    
    Args:
        df (pd.DataFrame): Preprocessed DataFrame containing procurement transaction data.
                          Must include columns for dates, prices, suppliers, and methods as specified in preprocess.py.
    
    Returns:
        tuple: (pd.DataFrame, list)
            - pd.DataFrame: The final DataFrame with all engineered features
            - list: List of final feature column names used for model training
    
    Feature Categories:
        A. Date-Based Features: Detect timing anomalies
        B. Price & Budget Features: Detect financial irregularities and budget violations
        C. Categorical & Interaction Features: Detect supplier favoritism and collusion
    """
# --- A. Date-Based Features ---
    # Targets: 'EndOfYearRush', 'WeekendActivity', 'CompressedTimeline', 'BackdatedDocuments'

    # Day of week features
    df['contract_signing_dayofweek'] = df['contract_signing_date'].dt.dayofweek
    df['bid_opening_dayofweek'] = df['bid_opening_date'].dt.dayofweek
    
    # Month feature
    df['transaction_month'] = df['transaction_date'].dt.month
    
    # Timeline duration features
    df['bidding_period_days'] = (df['bid_submission_deadline'] - df['invitation_to_bid_posting_date']).dt.days
    df['award_decision_days'] = (df['notice_of_award_date'] - df['bid_opening_date']).dt.days
    df['contract_signing_days'] = (df['contract_signing_date'] - df['notice_of_award_date']).dt.days
    df['total_procurement_cycle_days'] = (df['contract_signing_date'] - df['invitation_to_bid_posting_date']).dt.days

# --- B. Price & Budget Features ---
    # Targets: 'BidCeilingCollusion', 'PriceExceedsBudget'

    # Budget utilization ratio: values > 1 indicate budget overruns
   
    safe_budget = df['approved_budget'].replace(0, np.nan) # Avoid division by zero
    df['budget_utilization_ratio'] = df['total_purchase_price'] / safe_budget

# --- C. Categorical & Interaction Features ---
    # Features help detect 'FictitiousWinner', 'FavoredSupplier', and 'SuspiciousOverpricing'
    
    # Supplier frequency
        # direct measure of how often an organization engages with a particular supplier, normalized across the entire dataset -- useful for understanding supplier relationships and collusion
    supplier_freq_map = df['supplier'].value_counts(normalize=True).to_dict()
        # .value_counts() counts the occurrences of each unique value in the 'supplier' column.
        # normalize=True: returns the frequency of each supplier as a percentage of the total number of suppliers.
        # to_dict(): converts the Series to a dictionary (key: supplier, value: frequency)

        # Supplier frequency: map the supplier frequency to the supplier column
    df['supplier_frequency'] = df['supplier'].map(supplier_freq_map)
        
    
    # Price per supplier frequency:
        # A high value in price_per_supplier_freq indicates that the unit_purchase_price is high relative to how frequently that supplier is used. 
        # This is the red flag: if an organization repeatedly buys from a supplier (high frequency) but consistently pays high prices, it might suggest a lack of competitive bidding, a sole-source situation with unfavorable terms, or potential collusion where frequent suppliers exploit their relationship.

        # A low value would suggest either a low unit_purchase_price or a very high supplier_frequency (or both), which would generally be a good sign (e.g., getting good deals from preferred supplers)
    epsilon = 1e-6  # small value to prevent division by zero
    df['price_per_supplier_freq'] = df['unit_purchase_price'] / (df['supplier_frequency'] + epsilon)

# --- Final Imputation & Cleanup ---
    # Handle missing values in engineered features by imputing with median values
    engineered_features = [
        'contract_signing_dayofweek', 'bid_opening_dayofweek', 'transaction_month',
        'bidding_period_days', 'award_decision_days', 'contract_signing_days', 'total_procurement_cycle_days',
        'budget_utilization_ratio', 'supplier_frequency', 'price_per_supplier_freq'
    ]
    
    # Impute missing values with median for each engineered feature
    for col in engineered_features:
        if df[col].isnull().any():
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)

    # --- One-Hot Encoding ---
    # Convert categorical procurement methods to numerical features
    df_processed = pd.get_dummies(df, columns=['procurement_method'], prefix=['procurement_method'], dummy_na=True)

    # --- Final Feature Set ---
    # Combine base numerical features with engineered features and one-hot encoded columns
    base_numerical_features = ['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']
    one_hot_cols = [col for col in df_processed.columns if 'procurement_method_' in col]
    final_feature_columns = base_numerical_features + engineered_features + one_hot_cols
    
    # Ensure all columns exist in the final DataFrame
    final_feature_columns = [col for col in final_feature_columns if col in df_processed.columns]
    df_final = df_processed[final_feature_columns].copy()

    return df_final, final_feature_columns