import pandas as pd
import random
from faker import Faker
import datetime
import os
import sys


# Add the project root directory to the Python path
# Adjust the path ('..') if generate_data.py is deeper than one level
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import and run the scraper function
try:
    # Assuming Scraper.py is in data_utils and has the function
    from data_utils.scraper import run_scraper
    print("Running scraper to ensure prices are up-to-date...")
    run_scraper()
    print("Scraper check complete.")
except ImportError:
    print("Error: Could not import the scraper function. Make sure Scraper.py is in the data_utils directory and contains run_scraper().")
    sys.exit(1)
except Exception as e:
    print(f"Error running scraper: {e}")
    # Decide if you want to exit or continue with potentially stale prices
    # sys.exit(1)


# --- Step 2: Load configuration *after* scraper runs ---
try:
    # Assuming procurement_data_config.py is in the same directory (data_utils)
    from data_utils.procurement_data_config import PROCUREMENT_DATA, AVERAGE_PRICES, PROCUREMENT_OFFICERS
    print("Configuration loaded successfully.")
    # Basic check if average prices were loaded
    if not AVERAGE_PRICES:
        print("Warning: AVERAGE_PRICES dictionary is empty. Check item_average_prices.json.")

    # --- Helper: Create Method Name to ID mapping ---
    # We need IDs for the database schema, but config uses names.
    # Let's create a simple mapping assuming IDs are sequential (1, 2, 3...)
    # or load them if they exist elsewhere (e.g., a database table later)
    unique_methods = PROCUREMENT_DATA['Method'].unique()
    PROCUREMENT_METHOD_MAP = {name: i+1 for i, name in enumerate(unique_methods)}
    print("Procurement Method Map:", PROCUREMENT_METHOD_MAP)

except ImportError:
    print("Error: Could not import configuration. Make sure procurement_data_config.py is in the data_utils directory.")
    sys.exit(1)
except KeyError as e:
    print(f"Error: Missing expected key in configuration data: {e}")
    sys.exit(1)


# --- Step 3: Initialize Faker ---
fake = Faker()

# --- Step 4: Define Generation Function ---
def generate_transactions(num_transactions):
    """Generates a DataFrame of normal procurement transactions."""
    transactions = []
    if PROCUREMENT_DATA.empty or not AVERAGE_PRICES:
        print("Error: Cannot generate transactions. Procurement data or average prices are missing.")
        return pd.DataFrame(transactions)

    print(f"Generating {num_transactions} normal transactions...")
    for i in range(num_transactions):
        # Select Method based on Frequency
        # Ensure 'Frequency' column sums to 1 or adjust weights
        # Using dropna() in case of issues with frequency calculation in config
        valid_methods_df = PROCUREMENT_DATA[['Method', 'Frequency']].drop_duplicates().dropna()
        if valid_methods_df.empty:
             print(f"Warning: No valid methods with frequencies found in PROCUREMENT_DATA. Skipping transaction {i+1}.")
             continue
        # Normalize frequencies if they don't sum to 1
        weights = valid_methods_df['Frequency'] / valid_methods_df['Frequency'].sum()
        selected_method_name = random.choices(
            valid_methods_df['Method'].tolist(),
            weights=weights.tolist(),
            k=1
        )[0]

        # Select Item appropriate for the Method
        possible_items = PROCUREMENT_DATA[PROCUREMENT_DATA['Method'] == selected_method_name]['Item_Name'].tolist()
        if not possible_items:
            print(f"Warning: No items found for method '{selected_method_name}'. Skipping transaction {i+1}.")
            continue
        selected_item_name = random.choice(possible_items)

        # Get Average Price (handle missing items)
        avg_price = AVERAGE_PRICES.get(selected_item_name, 0.0)
        if avg_price == 0.0:
             print(f"Warning: Average price not found for '{selected_item_name}'. Using 0.0.")

        # Generate Normal Unit Price (e.g., +/- 5% of average)
        # Avoid division by zero if avg_price is 0
        price_multiplier = random.uniform(0.95, 1.05) if avg_price > 0 else 1.0
        unit_price = round(avg_price * price_multiplier, 2)

        # Generate other fields
        quantity = random.randint(1, 100)
        supplier = fake.company()
        # Generate a date within the last year for realism
        transaction_date = fake.date_between(start_date='-1y', end_date='today')
        # Use the mapping to get method ID
        procurement_method_id = PROCUREMENT_METHOD_MAP.get(selected_method_name, None) # Handle if method somehow not in map

        transaction = {
            'transaction_id': i + 1, # Simple sequential ID for now
            # 'item_id': None, # We need item_id, not just name, for DB. Need mapping.
            'item_name': selected_item_name, # Keep name for now
            'quantity': quantity,
            'unit_price': unit_price,
            'average_price': round(avg_price, 2),
            'procurement_method_id': procurement_method_id,
            'procurement_method_name': selected_method_name, # Keep name for reference
            'supplier': supplier,
            'transaction_date': transaction_date
            # Add other fields if needed (e.g., procurement officer)
            # 'procurement_officer': random.choice(PROCUREMENT_OFFICERS)
        }
        transactions.append(transaction)

    print("Generation loop finished.")
    return pd.DataFrame(transactions)

# --- Step 5: Main Execution ---
if __name__ == "__main__":
    NUM_TRANSACTIONS = 1000 # Or get from command line args
    OUTPUT_CSV = 'normal_transactions.csv' # Save in the same directory as script

    # Define the full path for the output CSV
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_CSV)


    df_transactions = generate_transactions(NUM_TRANSACTIONS)

    if not df_transactions.empty:
        try:
            df_transactions.to_csv(output_path, index=False, encoding='utf-8')
            print(f"Successfully generated {len(df_transactions)} transactions and saved to {output_path}")
        except Exception as e:
            print(f"Error saving DataFrame to CSV: {e}")
    else:
        print("No transactions were generated.")