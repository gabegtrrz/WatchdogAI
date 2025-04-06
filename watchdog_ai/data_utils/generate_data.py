# Data nad Logic Imports
import hashlib
import random
from faker import Faker
from datetime import datetime, timedelta

# File Handling Imports
import pandas as pd
import json
import os

# Local Imports 
from procurement_data_config import METHODS_DATA, PROCUREMENT_DATA, BASE_PRICES, PROCUREMENT_OFFICERS, VOLATILITY_LOW, VOLATILITY_MEDIUM, VOLATILITY_HIGH
import scraper

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


fake = Faker()


SCRAPER_OUTPUT_FILE = scraper.OUTPUT_JSON_FULL_PATH


def load_average_price_data():
    ''' Load average prices from the JSON file. '''
    try:
        with open(SCRAPER_OUTPUT_FILE, 'r', encoding='utf-8') as file:
            logger.info(f"Loading average prices from {SCRAPER_OUTPUT_FILE}")
            # Load the JSON data from the file
            return json.load(file)

    except FileNotFoundError:
        logger.info(f"File {SCRAPER_OUTPUT_FILE} not found. Running scraper...")
        scraper.run_scraper() 
        # Retry loading the average prices after running the scraper
        try:
            with open(SCRAPER_OUTPUT_FILE, 'r', encoding='utf-8') as file:
                logger.info(f"Loading average prices from {SCRAPER_OUTPUT_FILE} after running scraper")
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading average prices after running scraper: {e}", exc_info=True)
            return {}
    
    except Exception as e:
        logger.error(f"Error loading average prices: {e}", exc_info=True)
        return {}
        
def generate_transaction_data(scrape_num: int, num_transactions = 1000, procurement_data = PROCUREMENT_DATA, procurement_officers = PROCUREMENT_OFFICERS, volatility_medium = VOLATILITY_MEDIUM, volatility_high = VOLATILITY_HIGH,):
    ''' This is to generate clean or normal transaction data FOR TRAINING. '''


    ### Ensure average_price data is up-to-date ###
    scraper.check_and_run_scraper_if_needed(limit_items=scrape_num) # scrape_num is the number of items variation to scrape

    ### Load average prices from the JSON file ###
    average_price_data = load_average_price_data()
    if not average_price_data:
        pass
        # Backup to avoid crashing if scraper requires maintenance



    data = []
    
    # Get procurement methods and appropriate frequency from procurement_data values
    methods_and_frequencies = procurement_data.groupby('Method')['Frequency'].first() #This is a pandas series
    methods = methods_and_frequencies.index.tolist() #List of Methods
    frequencies = methods_and_frequencies.values.tolist() #List of frequencies

    if not methods:
        logger.error("No procurement methods found in PROCUREMENT_DATA. Exiting.")
        return
    
    ### Get available items that have average_price_data ###
    # This is to ensure that we only select items that have average price data
    
    items_in_average_price_data = set(average_price_data.keys())
    # This is a set of item names that are available in the average price data
    if not items_in_average_price_data:
        logger.error("Average price data loaded, but no items here. Exiting.")
        return

    ### Initialize ###
    logger.info(f"Generating {num_transactions} transactions...")
    generated_count = 0
    attempts = 0
    max_attempts = num_transactions * 5 # To avoid infinite loop in case of no valid items

    while generated_count < num_transactions and attempts < max_attempts:
        attempts += 1
        procurement_method = random.choices(methods, weights=frequencies, k=1)[0]
        # methods and frequencies are aligned by position in their respective lists

        ### Retrieving valid_items_for_transaction from procurement_data based on the procurement method ###

        # Filter 1
        items_for_method_df = procurement_data[procurement_data['Method'] == procurement_method]

        # Filter 2: Get the items that are available in the average price data
        items_list_for_method = procurement_data['Item_Name'].tolist() # Need to turn to list to apply filter
        valid_items_for_transaction = list(items_list_for_method & items_in_average_price_data)

        if not valid_items_for_transaction:
            # This might happen if the scraper didn't find prices for items listed
            # under this procurement method in the config.py
            logger.error(f"No valid items found for procurement method: {procurement_method}. Skipping this attempt.")
            continue # Try generating another transaction with potentially a different method
        
        ### ---------

        ### This is where we pick the item_name from valid_items_for_transaction ###

        item_name = random.choice(valid_items_for_transaction)
        item_avg_price_info = average_price_data[item_name]
        average_price = item_avg_price_info.get('average_price') # Default if not found
        if average_price is None or average_price <= 0:
             logger.warning(f"Average price for '{item_name}' from loaded data is invalid ({average_price}). Skipping this transaction attempt.")
             continue # Skip if price is missing or zero/negative
        
        ### Other Transaction Data ###

        # datetime object converted into str for immutability
        transaction_date = fake.date_time_between(start_date='-1y',end_date='now').strftime('%Y-%m-%d')

        quantity = random.randint(1000, 10000)
        supplier = fake.company()
        procurement_officer = random.choice(procurement_officers)



        ### Determining Volatility
        if procurement_method in ["Negotiated Procurement", "Direct Contracting"]:
            volatility = volatility_high
        else:
            volatility = volatility_medium
         
        
        ### Price based on average_price multiplied to set volatility ###

        unit_price = average_price * (1 + random.uniform(-volatility, volatility))
        # random.uniform selects a float from the given range (lower bound, uper bound)
        unit_price = round(unit_price, 2)
        unit_price = max(0.01, unit_price) # to ensure unit price is not negative or zero



        ### Append Data ###

         # !!! Make columns match with dataframe variable !!!
        data.append([
            generated_count+1, item_name, quantity, procurement_method, 
            unit_price, average_price, supplier, procurement_officer, 
            transaction_date
        ])

        generated_count += 1
        ### Logging ###
        if generated_count % 100 == 0:
            logger.info(f"Generated {generated_count}/{num_transactions} transactions...")


    # --- END OF WHILE LOOP --- #
    if generated_count < num_transactions:
         logger.warning(f"Could only generate {generated_count}/{num_transactions} transactions after {attempts} attempts. Check item availability and scraper data.")

    if not data:
        logger.error("No transaction data was generated.")
        return None # Return None or empty DataFrame if nothing generated

    ### Creating DataFrame ###
    # !!! Make columns match with data variable !!!
    dataframe = pd.DataFrame(data, columns= [
        'transaction_id', 'item_name', 'quantity', 'procurement_method', 'unit_price', 'average_price', 'supplier', 'procurement_officer','transaction_date'])
    
    ### Exporting dataframe to CSV ###
    save_dir = os.path.join(os.getcwd(), 'transactions_folder')
    os.makedirs(save_dir, exist_ok=True)  # Create directory if it doesn't exist

    csv_filename = f"simulated_transactions_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
    csv_file_path = os.path.join(save_dir, csv_filename)
    
    dataframe.to_csv(csv_file_path, index=False)

    logger.info(f"Transaction data {csv_filename} generated successfully with {generated_count} records.")
    logger.info(f"Transaction data saved to {csv_file_path}.")

    return


if __name__ == "__main__":
    # Example usage
    generate_transaction_data(scrape_num=10, num_transactions=1000)
    # The scrape_num is the number of items to scrape from the web.
    # Set scrape_num=0 if you don't want the check_and_run function to limit the scraper run.
    # The num_transactions is the number of transactions to generate.