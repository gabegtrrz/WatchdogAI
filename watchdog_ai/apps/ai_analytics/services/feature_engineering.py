"""
Feature Engineering Service for Anomaly Detection

This service engineers features for the anomaly detection model by transforming
raw procurement data into meaningful features that help identify specific irregularities.

The service creates three main categories of features:
1. Date-based features - to detect timing anomalies
2. Price & budget features - to detect financial irregularities and budget violations
3. Categorical & interaction features - to detect supplier-related anomalies

Each feature is designed to target specific anomaly types in procurement data.
"""
import pandas as pd
import numpy as np
import warnings
import logging
from typing import Tuple, List

# Configure logging for this module
logger = logging.getLogger(__name__)

def safe_date_diff(d1: pd.Timestamp, d2: pd.Timestamp) -> float:
    """Safely calculates the difference in days between two dates, handling NaT."""
    if pd.isna(d1) or pd.isna(d2):
        return np.nan
    return (d1 - d2).days

def _convert_decimal_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert decimal columns to float for calculation.

    This prevents 'unsupported operand' errors when dividing Decimal types by floats.

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with decimal columns converted to float
    """
    logger.debug("Converting decimal columns to float...")
    decimal_columns = ['approved_budget', 'total_purchase_price', 'unit_purchase_price']
    for col in decimal_columns:
        if col in df.columns:
            df[col] = df[col].astype(float)
    return df

def _create_date_based_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create date-based features to detect timing anomalies.

    Targets: 'EndOfYearRush', 'WeekendActivity', 'CompressedTimeline', 'BackdatedDocuments'

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with date-based features added
    """
    logger.debug("Creating date-based features...")

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
    # I observed procurement processes are defined with procurement guidelines such as those in GPPB IRR.
    # The same principles apply to public and private procurement and can be refactored to appropriate
    # procurement guidelines but this should be robust enough to handle different procurement guidelines.

    # These features measure the efficiency and transparency of procurement processes.
    # Unusually short timelines might indicate rushed or non-competitive processes,
    # while excessively long timelines could suggest bureaucratic delays or manipulation.
    df['bidding_period_days'] = df.apply(
        lambda r: safe_date_diff(r['bid_submission_deadline'], r['invitation_to_bid_posting_date']),
        axis=1
    )
    df['award_decision_days'] = df.apply(
        lambda r: safe_date_diff(r['notice_of_award_date'], r['bid_opening_date']),
        axis=1
    )
    df['contract_signing_days'] = df.apply(
        lambda r: safe_date_diff(r['contract_signing_date'],r['notice_of_award_date']),
        axis=1
    )
    df['total_procurement_cycle_days'] = df.apply(
        lambda r: safe_date_diff(r['contract_signing_date'], r['invitation_to_bid_posting_date']),
        axis=1
    )

    return df

def _create_price_budget_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create price and budget features to detect financial irregularities.

    Targets: 'BidCeilingCollusion', 'PriceExceedsBudget'

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with price and budget features added
    """
    logger.debug("Creating price and budget features...")

    # Budget utilization ratio
    # This feature measures how much of the approved budget is actually spent.
    # Values > 1 indicate budget overruns, which could signal poor planning,
    # scope creep, or intentional budget manipulation. Values close to 1 suggest
    # efficient budget utilization, while very low values might indicate
    # conservative estimates or last-minute changes.
    safe_budget = df['approved_budget'].replace(0, np.nan)  # Avoid division by zero
    df['budget_utilization_ratio'] = df['total_purchase_price'] / safe_budget

    return df

def _create_supplier_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create supplier-related features to detect favoritism and collusion.

    Features help detect 'FictitiousWinner', 'FavoredSupplier', and 'SuspiciousOverpricing'

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with supplier features added
    """
    logger.debug("Creating categorical and interaction features...")

    # Supplier frequency
    # Direct measure of how often an organization engages with a particular supplier,
    # normalized across the entire dataset.
    # This is useful for understanding supplier relationships and detecting potential
    # collusion or favoritism.
    # High frequency suppliers might indicate legitimate preferred partnerships,
    # but could also signal collusion if combined with suspicious pricing patterns.
    supplier_freq_map = df['supplier'].value_counts(normalize=True).to_dict()
    # .value_counts() counts the occurrences of each unique value in the 'supplier' column.
    # normalize=True: returns the frequency of each supplier as a percentage of the total number of suppliers.
    # to_dict(): converts the Series to a dictionary (key: supplier, value: frequency)

    # Map the supplier frequency to each transaction
    df['supplier_frequency'] = df['supplier'].map(supplier_freq_map)

    # Price per supplier frequency
    # Combines pricing with supplier relationship strength.
    # A high value indicates that the unit_purchase_price is
    # high relative to how frequently that supplier is used.
    # This is a red flag: if an organization repeatedly buys from a supplier (high frequency)
    # but consistently pays high prices, it might suggest a lack of competitive bidding,
    # a sole-source situation with unfavorable terms, or potential collusion where frequent
    # suppliers exploit their relationship.

    # A low value would suggest either a low unit_purchase_price or a very high supplier_frequency
    # (or both), which would generally be a good sign (e.g., getting good deals from preferred suppliers)
    epsilon = 1e-6  # Small value to prevent division by zero
    df['price_per_supplier_freq'] = df['unit_purchase_price'] / (df['supplier_frequency'] + epsilon)

    # Price variance by supplier
    # Measures how much the unit price varies for each supplier across transactions.
    # High variance might indicate inconsistent pricing or potential price manipulation.
    # Handle empty groups by filtering out suppliers with no valid price data
    valid_supplier_prices = df[df['unit_purchase_price'].notna()].groupby('supplier')['unit_purchase_price']
    supplier_price_stats = valid_supplier_prices.agg(['mean', 'std']).fillna(0)

    # Average price deviation
    # Measures how much each transaction's unit price deviates from the average price for that supplier.
    # Large deviations might indicate price manipulation or quality differences.
    # Use safe mapping to handle suppliers not in the stats
    supplier_mean_prices = supplier_price_stats['mean'].to_dict()
    df['price_deviation_from_supplier_avg'] = df['unit_purchase_price'] - df['supplier'].map(supplier_mean_prices).fillna(0)
    return df

def _create_efficiency_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create efficiency and composite features.

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with efficiency features added
    """
    # Budget efficiency score
    # Combines budget utilization with price efficiency.
    # Values close to 1 indicate good budget utilization, while very high or low values might indicate issues.
    df['budget_efficiency_score'] = (
        df['total_purchase_price'] / df['approved_budget']
    ) * (1 / (1 + df['price_deviation_from_supplier_avg'].abs()))

    # Timeline efficiency
    # Measures how efficiently the procurement timeline is used.
    # Very short timelines might indicate rushed processes, while very long ones might indicate delays.
    epsilon = 1e-6  # Small value to prevent division by zero
    df['timeline_efficiency'] = df['total_procurement_cycle_days'] / (
        df['bidding_period_days'] + df['award_decision_days'] + df['contract_signing_days'] + epsilon
    )

    # Weekend activity indicator
    # Binary feature indicating if any key procurement activity occurred on weekends.
    # Weekend activity might indicate irregular or rushed processes.
    df['weekend_activity'] = (
        (df['contract_signing_dayofweek'] >= 5) |
        (df['bid_opening_dayofweek'] >= 5)
    ).astype(int)

    return df

def _drop_transformed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop original columns that have been transformed into engineered features.

    To keep the final feature set clean and relevant for the model, we drop the original
    columns that have already been transformed into engineered features. This prevents
    data leakage and reduces the dimensionality of the input data.

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with transformed columns removed
    """
    logger.debug("Dropping transformed source columns...")
    columns_to_drop = [
        # Raw date columns are converted into duration and cyclical features.
        'transaction_date', 'invitation_to_bid_posting_date', 'bid_submission_deadline',
        'bid_opening_date', 'notice_of_award_date', 'contract_signing_date',

        # Raw categorical columns are encoded into numerical representations.
        'supplier'
    ]
    df.drop(columns=columns_to_drop, inplace=True, errors='ignore')
    return df

def _impute_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values in engineered features by imputing with median values.

    Missing values in engineered features can occur due to data quality issues
    or edge cases in the feature engineering process. Using median imputation
    preserves the distribution of the data while ensuring all features have
    complete values for model training.

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with missing values imputed
    """
    logger.debug("Handling missing values in engineered features...")
    engineered_features = [
        'contract_signing_dayofweek', 'bid_opening_dayofweek', 'transaction_month',
        'bidding_period_days', 'award_decision_days', 'contract_signing_days', 'total_procurement_cycle_days',
        'budget_utilization_ratio',
        'supplier_frequency',
        'price_per_supplier_freq',
        'price_deviation_from_supplier_avg', 'budget_efficiency_score', 'timeline_efficiency', 'weekend_activity'
    ]

    # Impute missing values with median for each engineered feature
    for col in engineered_features:
        if col in df.columns and df[col].isnull().sum() > 0:
            missing_count = df[col].isnull().sum()
            median_val = df[col].median()
            df.fillna({col: median_val}, inplace=True)
            logger.debug(f"Imputed {missing_count} missing values in {col} with median: {median_val}")
    return df

def _perform_one_hot_encoding(df: pd.DataFrame) -> pd.DataFrame:
    """Perform one-hot encoding on categorical columns.

    get_dummies() converts categorical procurement methods to numerical features.
    After one-hot encoding, each unique value in procurement_method becomes a new column
    named like procurement_method_<value> (e.g., procurement_method_Open_Bidding).

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with one-hot encoded columns
    """
    logger.debug("Performing one-hot encoding...")
    df_processed = pd.get_dummies(
        df,
        columns=['procurement_method'],  # specifies which column(s) to encode
        prefix=['procurement_method'],
        dummy_na=True  # include columns for missing values
    )
    return df_processed

def _get_final_feature_columns(df_processed: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Determine the final feature columns and create the final DataFrame.

    Args:
        df_processed: Processed DataFrame with all features

    Returns:
        Tuple[pd.DataFrame, List[str]]: Final DataFrame and list of feature column names
    """
    # Define expected engineered features
    engineered_features = [
        'contract_signing_dayofweek', 'bid_opening_dayofweek', 'transaction_month',
        'bidding_period_days', 'award_decision_days', 'contract_signing_days', 'total_procurement_cycle_days',
        'budget_utilization_ratio',
        'supplier_frequency',
        'price_per_supplier_freq',
        'price_deviation_from_supplier_avg', 'budget_efficiency_score', 'timeline_efficiency', 'weekend_activity'
    ]

    # Get one-hot encoded columns
    one_hot_cols = [col for col in df_processed.columns if 'procurement_method_' in col]
    # e.g.:
    # one_hot_cols = [
    #     'procurement_method_Open_Bidding',
    #     'procurement_method_Direct_Contracting',
    #     'procurement_method_Limited_Source',
    #     'procurement_method_Negotiated_Procurement',
    #     'procurement_method_nan'
    # ]

    # Combine expected features
    expected_feature_columns = engineered_features + one_hot_cols

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

def create_model_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    '''
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

    Note: We append to the original dataframe, df, and return the final dataframe, df_final,
    and the list of final feature column names, final_feature_columns.
    '''

    try:
        logger.info("Starting feature engineering process...")
        logger.debug(f"Input DataFrame shape: {df.shape}")

        # Step 1: Convert decimal columns to float
        df = _convert_decimal_columns(df)

        # Step 2: Create date-based features
        df = _create_date_based_features(df)

        # Step 3: Create price and budget features
        df = _create_price_budget_features(df)

        # Step 4: Create supplier-related features
        df = _create_supplier_features(df)

        # Step 5: Create efficiency features
        df = _create_efficiency_features(df)

        # Step 6: Drop transformed source columns
        df = _drop_transformed_columns(df)

        # Step 7: Impute missing values
        df = _impute_missing_values(df)

        # Step 8: Perform one-hot encoding
        df_processed = _perform_one_hot_encoding(df)

        # Step 9: Get final feature columns and create final DataFrame
        df_final, final_feature_columns = _get_final_feature_columns(df_processed)

        logger.info("Feature engineering process completed successfully.")
        return df_final, final_feature_columns

    except Exception as e:
        logger.error(f"An error occurred during feature engineering: {e}", exc_info=True)
        raise