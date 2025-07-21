"""
Engineers features for the anomaly detection model

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
# ===========================
# REQUIRED DATABASE COLUMNS
# ============================

# List of raw database columns required for feature engineering
# This list is imported by the preprocessing service to dynamically fetch
# the necessary data from the database.
REQUIRED_COLUMNS = []
FINANCE_COLUMNS = [ # Implement later, just use for preprocessing for now.
    'quantity',
    'unit_purchase_price',
    'total_purchase_price',
    'average_price',
    'approved_budget',
] 
ONE_HOT_COLUMNS = [
    'supplier',
    'procurement_method',
] # implement later
DATE_COLUMNS = [
    'transaction_date',
    'invitation_to_bid_posting_date',
    'bid_submission_deadline',
    'bid_opening_date',
    'notice_of_award_date',
    'contract_signing_date',
]
INITIAL_COLUMNS_TO_USE = (
    FINANCE_COLUMNS + 
    DATE_COLUMNS + 
    ONE_HOT_COLUMNS
)

COLUMNS_TO_DROP_FROM_FINAL = [
    # Raw date columns are converted into duration and cyclical features.
        'transaction_date', 
        'invitation_to_bid_posting_date',
        'bid_submission_deadline',
        'bid_opening_date', 'notice_of_award_date', 'contract_signing_date',

        # Text columns
        'project_name', 'end_user_unit', 'project_description',

        # Raw categorical columns are encoded into numerical representations.
        'supplier', 'procurement_method', 'procurement_officer',
        
        # Base numerical columns that have been transformed into engineered features
        'unit_purchase_price', 'total_purchase_price', 'approved_budget', 'average_price',

        # blockchain and database columns:
        'id', 'transaction_id', 'block_id', 'blockchain_retry_count', 'procurement_method_id',
   
]
PROCUREMENT_METHODS = [
    'Competitive Bidding',
    'Direct Contracting',
    # 'Limited Source Bidding',
    # 'Negotiated Procurement',
    'Negotiated Procurement (Agency-to-Agency)',
    'Negotiated Procurement (Small Value Procurement)',
    'Negotiated Procurement (Two Failed Biddings)',
    'Repeat Order',
    'nan',
]
REQUIRED_COLUMNS.extend(PROCUREMENT_METHODS)

#===============================================
# ONE-HOT ENCODING
#===============================================

# Map to configure columns for one-hot encoding and their categories
ONE_HOT_ENCODING_MAP = {
    'procurement_method': PROCUREMENT_METHODS,
    # To encode other columns, add here

}

# =============================================================================
# FEATURE CREATION ORCHESTRATION
# =============================================================================
def create_features(df: pd.DataFrame, is_training: bool = False) -> Tuple[pd.DataFrame, List[str]]:
    """
    Orchestrates the creation of all features for the anomaly detection model.

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

    Note: We append to 
    the original dataframe == df, and 
    return the final dataframe == df_final,
    and the list of final feature column names == final_feature_columns.
    """

    try:
        logger.info("Starting feature engineering process...")
        logger.debug(f"Input DataFrame shape: {df.shape}")

        # Step 1: Convert decimal columns to float
        df = _convert_decimal_columns(df)

        # Step 2: Create financial features
        df = _create_finance_features(df)

        # Step 3: Create date-based features
        df = _create_date_based_features(df)

        # Step 4: Create supplier-related features
        df = _create_supplier_features(df)

        # Step 5: Create efficiency features
        df = _create_efficiency_features(df)

        # Step 6: Perform one-hot encoding (before dropping columns)
        df_processed = df.copy()
        for column, categories in ONE_HOT_ENCODING_MAP.items():
            df_processed = _perform_one_hot_encoding(df_processed, column, categories)


        # Step 7: Impute missing values
        df_processed = _impute_missing_values(df_processed)

        # Step 8: Drop transformed unnecessary columns
        logger.debug("Dropping transformed source columns...")
        df_processed.drop(columns=COLUMNS_TO_DROP_FROM_FINAL, inplace=True, errors='ignore')

        # Step 9: Get final feature columns and create final DataFrame
        df_final, final_feature_columns = _get_final_feature_columns(df_processed)

        logger.info("Feature engineering process completed successfully.")
        return df_final, final_feature_columns

    except Exception as e:
        logger.error(f"An error occurred during feature engineering: {e}", exc_info=True)
        raise

def safe_date_diff(d1, d2) -> float:
    """Safely calculates the difference in days between two dates, handling NaT and type conversion."""
    # Handle None/NaN values
    if pd.isna(d1) or pd.isna(d2):
        return np.nan
    
    # Convert to datetime if needed (handles decimal.Decimal types)
    try:
        if not isinstance(d1, pd.Timestamp):
            d1 = pd.to_datetime(d1, errors='coerce')
        if not isinstance(d2, pd.Timestamp):
            d2 = pd.to_datetime(d2, errors='coerce')
        
        # Check if conversion was successful
        if pd.isna(d1) or pd.isna(d2):
            return np.nan
            
        return (d1 - d2).days
    except Exception as e:
        logger.warning(f"Error calculating date difference: {e}")
        return np.nan

def _convert_decimal_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert decimal columns to float for calculation.

    This prevents 'unsupported operand' errors when dividing Decimal types by floats.
    Excludes date columns to preserve their datetime type.

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: DataFrame with decimal columns converted to float
    """
    logger.debug("Converting decimal columns to float...")
    decimal_columns = ['approved_budget', 'total_purchase_price', 'unit_purchase_price', 'average_price']
    date_columns = [
        'transaction_date', 'invitation_to_bid_posting_date', 'bid_submission_deadline',
        'bid_opening_date', 'notice_of_award_date', 'contract_signing_date'
    ]
    
    for col in decimal_columns:
        if col in df.columns:
            df[col] = df[col].astype(float)
    
    # Ensure date columns are properly converted to datetime
    for col in date_columns:
        if col in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col], errors='coerce')
    
    return df

def _perform_one_hot_encoding(df: pd.DataFrame, column_name: str, categories: list) -> pd.DataFrame:
    """Performs generic one-hot encoding on specified categorical column.
    
    Args:
        df: Input DataFrame
        column_name: Name of the categorical column to encode
        categories: List of categories to encode

    Returns:
        pd.DataFrame: DataFrame with one-hot encoded columns added
    """
    if column_name not in df.columns:
        # If the column to be encoded is missing, create empty columns for its categories to ensure a consistent DataFrame schema for the model.
        for category in categories:
            df[f'{column_name}_{category}'] = 0
        return df
    else:
        # Convert column to a categorical type to ensure all predefined categories are included.
        df[column_name] = pd.Categorical(df[column_name], categories=categories)

        # Create the one-hot encoded dummy variables.
        dummies = pd.get_dummies(df[column_name], prefix=column_name)

        # Combine the new dummy columns with the original DataFrame.
        return pd.concat([df, dummies], axis=1)


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
    df['contract_signing_day_of_week'] = df['contract_signing_date'].dt.dayofweek
    df['bid_opening_day_of_week'] = df['bid_opening_date'].dt.dayofweek

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
    df['bidding_period_number_of_days'] = df.apply(
        lambda r: safe_date_diff(r['bid_submission_deadline'], r['invitation_to_bid_posting_date']),
        axis=1
    )
    df['award_decision_duration'] = df.apply(
        lambda r: safe_date_diff(r['notice_of_award_date'], r['bid_opening_date']),
        axis=1
    )
    df['contract_signing_number_of_days'] = df.apply(
        lambda r: safe_date_diff(r['contract_signing_date'],r['notice_of_award_date']),
        axis=1
    )
    df['total_procurement_duration'] = df.apply(
        lambda r: safe_date_diff(r['contract_signing_date'], r['invitation_to_bid_posting_date']),
        axis=1
    )

    return df

def _create_finance_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create financial features from base numerical columns for anomaly detection.
    
    Transforms raw numerical procurement data into engineered features that help
    identify specific types of financial irregularities, budget violations, and pricing anomalies.
    
    Targets: 'BidCeilingCollusion', 'PriceExceedsBudget', 'SuspiciousOverpricing'
    
    Args:
        df: Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with financial features added
    """
    logger.debug("Creating financial features...")
    
    # Price per unit efficiency
    # Measures how efficiently the budget is used per unit purchased.
    # High values might indicate overpricing or low quantity purchases.
    # This helps detect suspicious pricing patterns where unit costs are inflated.
    epsilon = 1e-6  # Small value to prevent division by zero
    df['price_per_unit_efficiency'] = df['unit_purchase_price'] / (df['total_purchase_price'] / df['quantity'] + epsilon)
    
    # Quantity efficiency ratio
    # Measures the relationship between quantity purchased and total price.
    # Unusual ratios might indicate bulk purchase anomalies or pricing irregularities.
    df['quantity_per_peso_ratio'] = df['quantity'] / (df['total_purchase_price'] + epsilon)

    
    # Unit price deviation from average
    # Measures how much each transaction's unit price deviates from the overall average.
    # Large deviations might indicate price manipulation or quality differences.
    overall_avg_unit_price = df['unit_purchase_price'].mean()
    df['unit_price_vs_market_average'] = df['unit_purchase_price'] - overall_avg_unit_price
    
    # Budget utilization ratio
    # This feature measures how much of the approved budget is actually spent.
    # Values > 1 indicate budget overruns, which could signal poor planning,
    # scope creep, or intentional budget manipulation. Values close to 1 suggest
    # efficient budget utilization, while very low values might indicate
    # conservative estimates or last-minute changes.
    safe_budget = df['approved_budget'].replace(0, np.nan)  # Avoid division by zero
    df['budget_utilization_ratio'] = df['total_purchase_price'] / safe_budget
    
    # Budget efficiency score
    # Combines budget utilization with price efficiency.
    # Values close to 1 indicate good budget utilization, while very high or low values might indicate issues.
    df['budget_efficiency_score'] = (df['total_purchase_price'] / safe_budget) * (1 / (1 + abs(df['unit_price_vs_market_average'])))
    
    # Price variance indicator
    # Measures the coefficient of variation for unit prices across the dataset.
    # High variance might indicate inconsistent pricing or potential manipulation.
    unit_price_std = df['unit_purchase_price'].std()
    unit_price_mean = df['unit_purchase_price'].mean()
    df['price_volatility_index'] = unit_price_std / (unit_price_mean + epsilon)
    
    # Total transaction value
    # Measures the total monetary value of each transaction (quantity × unit price).
    # This helps identify unusually large or small transactions that might indicate
    # bulk purchase anomalies, pricing irregularities, or procurement scale issues.
    df['total_transaction_value'] = df['quantity'] * df['unit_purchase_price']
    
    # Average price deviation (if average_price column exists)
    # Measures how much each transaction's total price deviates from the average price for similar items.
    if 'average_price' in df.columns:
        # Impute missing average_price with unit_purchase_price plus random variation (±20%)
        # This creates more realistic imputed values while maintaining neutral baseline
        random_variation_arr = np.random.uniform(0.8, 1.2, size=len(df))  # +/- 20% variation

        imputed_average_price = df['unit_purchase_price'] * random_variation_arr

        # Convert average_price to float to prevent decimal.Decimal type errors
        average_price = df['average_price'].fillna(imputed_average_price).astype(float)
        
        df['price_vs_market_average'] = df['unit_purchase_price'] - average_price

        df['price_competitiveness_score'] = df['unit_purchase_price'] / (average_price + epsilon)
        
    else:
        # If 'average_price' column is missing entirely, create neutral features
        df['price_vs_market_average'] = 0
        df['price_competitiveness_score'] = 1.0
    
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
    valid_prices_df = df[df['unit_purchase_price'].notna()]
    if not valid_prices_df.empty:
        valid_supplier_prices = valid_prices_df.groupby('supplier')['unit_purchase_price']
        supplier_price_stats = valid_supplier_prices.agg(['mean', 'std']).fillna(0).infer_objects(copy=False) 
        # .infer_objects(copy=False) converts the data type to float64.

    else:
        # If no valid prices exist, create an empty DataFrame with the expected columns
        # to avoid errors in subsequent steps.
        supplier_price_stats = pd.DataFrame(columns=['mean', 'std'])


    # Average price deviation
    # Measures how much each transaction's unit price deviates from the average price for that supplier.
    # Large deviations might indicate price manipulation or quality differences.
    # Use safe mapping to handle suppliers not in the stats
    supplier_mean_prices = supplier_price_stats['mean'].to_dict()
    df['price_vs_supplier_average'] = df['unit_purchase_price'] - df['supplier'].map(supplier_mean_prices).fillna(0).infer_objects(copy=False)
    # .infer_objects(copy=False) converts the data type to float64.

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
    ) * (1 / (1 + df['price_vs_supplier_average'].abs()))

    # Timeline efficiency
    # Measures how efficiently the procurement timeline is used.
    # Very short timelines might indicate rushed processes, while very long ones might indicate delays.
    epsilon = 1e-6  # Small value to prevent division by zero
    df['procurement_timeline_speed_ratio'] = df['total_procurement_duration'] / (
        df['bidding_period_number_of_days'] + df['award_decision_duration'] + df['contract_signing_number_of_days'] + epsilon
    )

    # Weekend activity indicator
    # Binary feature indicating if any key procurement activity occurred on weekends.
    # Weekend activity might indicate irregular or rushed processes.
    df['transaction_on_a_weekend'] = (
        (df['contract_signing_day_of_week'] >= 5) |
        (df['bid_opening_day_of_week'] >= 5)
    ).astype(int)

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
        # Base numerical features
        'price_per_unit_efficiency',
        'quantity_per_peso_ratio',
        'unit_price_vs_market_average',
        'budget_efficiency_score', 'price_volatility_index', 'total_transaction_value',
        'budget_utilization_ratio', 'price_vs_market_average', 'price_competitiveness_score',
        
        # Date-based features
        'contract_signing_day_of_week', 'bid_opening_day_of_week', 'transaction_month',
        'bidding_period_number_of_days', 'award_decision_duration', 'contract_signing_number_of_days', 'total_procurement_duration',
        
        # Supplier features
        'supplier_frequency',
        'price_per_supplier_freq',
        'price_vs_supplier_average',
        
        # Efficiency features
        'procurement_timeline_speed_ratio', 'transaction_on_a_weekend'
    ]

    # Impute missing values with median for each engineered feature
    for col in engineered_features:
        if col in df.columns and df[col].isnull().sum() > 0:
            missing_count = df[col].isnull().sum()
            median_val = df[col].median()
            df.fillna({col: median_val}, inplace=True)
            df.infer_objects(copy=False)
            logger.debug(f"Imputed {missing_count} missing values in {col} with median: {median_val}")
    return df



def _get_final_feature_columns(df_processed: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Determine the final feature columns and create the final DataFrame.

    Args:
        df_processed: Processed DataFrame with all features

    Returns:
        Tuple[pd.DataFrame, List[str]]: Final DataFrame and list of feature column names
    """
    # Define expected engineered features

    # Origin Features
    origin_features = [
        'quantity',
    ]

    engineered_features = [
        # Financial features
        'price_per_unit_efficiency',
        'quantity_per_peso_ratio','unit_price_vs_market_average',
        'budget_efficiency_score', 'price_volatility_index', 'total_transaction_value',
        'budget_utilization_ratio', 'price_vs_market_average', 'price_competitiveness_score',
        
        # Date-based features
        'contract_signing_day_of_week', 'bid_opening_day_of_week', 'transaction_month',
        'bidding_period_number_of_days', 'award_decision_duration', 'contract_signing_number_of_days', 'total_procurement_duration',
        
        # Supplier features
        'supplier_frequency',
        'price_per_supplier_freq', 'price_vs_supplier_average',
        
        # Efficiency features
        'procurement_timeline_speed_ratio', 'transaction_on_a_weekend'
    ]

    

    one_hot_cols = []
    for column, categories in ONE_HOT_ENCODING_MAP.items():
        for category in categories:
            one_hot_cols.append(f'{column}_{category}')

    # Combine expected features (don't modify global REQUIRED_COLUMNS)
    expected_features = (
        origin_features + 
        engineered_features + 
        one_hot_cols
    )

    # Filter expected features to only those present in the dataframe
    present_expected_features = [col for col in expected_features if col in df_processed.columns]

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
    df_final = df_processed[final_feature_columns]

    return df_final, final_feature_columns