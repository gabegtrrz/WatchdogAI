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
import warnings

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

    Note: We append to the original dataframe, df, and return the final dataframe, df_final, and the list of final feature column names, final_feature_columns.
    """
    # Convert decimal columns to float for calculation
    # This prevents 'unsupported operand' errors when dividing Decimal types by floats
    decimal_columns = ['approved_budget', 'total_purchase_price', 'unit_purchase_price']
    for col in decimal_columns:
        if col in df.columns:
            df[col] = df[col].astype(float)
            
# --- A. Date-Based Features ---
    # Targets: 'EndOfYearRush', 'WeekendActivity', 'CompressedTimeline', 'BackdatedDocuments'

    # Day of week features
        # Help detect suspicious timing patterns in procurement activities.
    df['contract_signing_dayofweek'] = df['contract_signing_date'].dt.dayofweek
    df['bid_opening_dayofweek'] = df['bid_opening_date'].dt.dayofweek
    
    # Month feature
        # Identifies seasonal patterns and end-of-year rush spending.
        # High activity in December (month 12) might indicate budget exhaustion,
        # while unusual activity in off-peak months could suggest irregular procurement timing.
    df['transaction_month'] = df['transaction_date'].dt.month
    
    # Timeline duration features
        # I observed procurement processes are defined with procurement guidlines such as those in GPPB IRR. The same principles apply to public and private procurement and can be reafactored to appropriate procurement guidelines but this should be robust enough to handle different procurement guidelines.
        
        # These features measure the efficiency and transparency of procurement processes.
        # Unusually short timelines might indicate rushed or non-competitive processes,
        # while excessively long timelines could suggest bureaucratic delays or manipulation.
    df['bidding_period_days'] = (df['bid_submission_deadline'] - df['invitation_to_bid_posting_date']).dt.days
    df['award_decision_days'] = (df['notice_of_award_date'] - df['bid_opening_date']).dt.days
    df['contract_signing_days'] = (df['contract_signing_date'] - df['notice_of_award_date']).dt.days
    df['total_procurement_cycle_days'] = (df['contract_signing_date'] - df['invitation_to_bid_posting_date']).dt.days

# --- B. Price & Budget Features ---
    # Targets: 'BidCeilingCollusion', 'PriceExceedsBudget'

    # Budget utilization ratio
        # This feature measures how much of the approved budget is actually spent.
        # Values > 1 indicate budget overruns, which could signal poor planning,
        # scope creep, or intentional budget manipulation. Values close to 1 suggest
        # efficient budget utilization, while very low values might indicate
        # conservative estimates or last-minute changes.
    safe_budget = df['approved_budget'].replace(0, np.nan) # Avoid division by zero
    df['budget_utilization_ratio'] = df['total_purchase_price'] / safe_budget

# --- C. Categorical & Interaction Features ---
    # Features help detect 'FictitiousWinner', 'FavoredSupplier', and 'SuspiciousOverpricing'
    
    # Supplier frequency
        # Direct measure of how often an organization engages with a particular supplier, normalized across the entire dataset. 
        # This is useful for understanding supplier relationships and detecting potential collusion or favoritism.
        # High frequency suppliers might indicate legitimate preferred partnerships, but could also signal collusion if combined with suspicious pricing patterns.
    supplier_freq_map = df['supplier'].value_counts(normalize=True).to_dict()
        # .value_counts() counts the occurrences of each unique value in the 'supplier' column.
        # normalize=True: returns the frequency of each supplier as a percentage of the total number of suppliers.
        # to_dict(): converts the Series to a dictionary (key: supplier, value: frequency)

        # Map the supplier frequency to each transaction
    df['supplier_frequency'] = df['supplier'].map(supplier_freq_map)
        
    
    # Price per supplier frequency
        # Combines pricing with supplier relationship strengt.
        # A high value indicates that the unit_purchase_price is 
        # high relative to how frequently that supplier is used.
        # This is a red flag: if an organization repeatedly buys from a supplier (high frequency) but consistently pays high prices, it might suggest a lack of competitive bidding, a sole-source situation with unfavorable terms, or potential collusion where frequent suppliers exploit their relationship. 
        
        # A low value would suggest either a low unit_purchase_price or a very high supplier_frequency (or both), which would generally be a good sign (e.g., getting good deals from preferred suppliers)
    epsilon = 1e-6  # Small value to prevent division by zero
    df['price_per_supplier_freq'] = df['unit_purchase_price'] / (df['supplier_frequency'] + epsilon)

# --- D. Drop Transformed Source Columns ---
    # To keep the final feature set clean and relevant for the model, we drop the original
    # columns that have already been transformed into engineered features. This prevents
    # data leakage and reduces the dimensionality of the input data.
    columns_to_drop = [
        # Raw date columns are converted into duration and cyclical features.
        'transaction_date', 'invitation_to_bid_posting_date', 'bid_submission_deadline',
        'bid_opening_date', 'notice_of_award_date', 'contract_signing_date',
        
        # Raw categorical columns are encoded into numerical representations.
        'supplier'
    ]
    df.drop(columns=columns_to_drop, inplace=True, errors='ignore')


# --- Final Imputation & Cleanup ---
    # Handle missing values in engineered features by imputing with median values
        # Missing values in engineered features can occur due to data quality issues
        # or edge cases in the feature engineering process. Using median imputation
        # preserves the distribution of the data while ensuring all features have
        # complete values for model training.
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
    # get_dummies() converts categorical procurement methods to numerical features
    df_processed = pd.get_dummies(
        df,
        columns=['procurement_method'], # specifies which column(s) to encode, if False: all columns with object or category dtype will be converted. Other dtypes will be left as is.
        prefix=['procurement_method'],
        dummy_na=True # include columns for missing values
    )

    # after one-hot encoding, each unique value in procurement_method becomes a new column named like procurement_method_<value> (e.g., procurement_method_Open_Bidding).

# --- Final Feature Set ---
    # Combine base numerical features with engineered features and one-hot encoded columns
    base_numerical_features = ['quantity', 'unit_purchase_price', 'total_purchase_price', 'approved_budget']
    one_hot_cols = [col for col in df_processed.columns if 'procurement_method_' in col]
    # e.g.:
        # one_hot_cols = [
        #     'procurement_method_Open_Bidding',
        #     'procurement_method_Direct_Contracting', 
        #     'procurement_method_Limited_Source',
        #     'procurement_method_Negotiated_Procurement',
        #     'procurement_method_nan'
        # ]
        
    expected_feature_columns = base_numerical_features + engineered_features + one_hot_cols

    # Filter expected features to only those present in the dataframe
    present_expected_features = [col for col in expected_feature_columns if col in df_processed.columns]

    # Identify all numeric columns in the processed dataframe
    all_numeric_features = df_processed.select_dtypes(include=np.number).columns.tolist()

    # Find new, unexpected numeric columns
    unexpected_new_features = sorted(list(set(all_numeric_features) - set(present_expected_features)))

    if unexpected_new_features:
        warnings.warn(
            f"Unexpected numeric columns were found and will be included as features: {unexpected_new_features}. "
            "This may be due to an updated data structure. Please verify these columns are suitable for the model.",
            UserWarning
        )

    # Combine expected and unexpected features for the final feature set
    final_feature_columns = present_expected_features + unexpected_new_features

    # Safety check to ensure all columns exist, creating the final DataFrame
    df_final = df_processed[final_feature_columns].copy()

    return df_final, final_feature_columns