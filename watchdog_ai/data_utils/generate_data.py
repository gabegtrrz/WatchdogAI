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
from procurement_data_config import PROCUREMENT_DATA, BASE_PRICES, PROCUREMENT_OFFICERS, VOLATILITY_LOW, VOLATILITY_MEDIUM, VOLATILITY_HIGH
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

    for i in range(num_transactions):
        # datetime object converted into str for immutability
        transaction_date = fake.date_time_between(start_date='-1y',end_date='now').strftime('%Y-%m-%d')

        quantity = random.randint(1000, 10000)
        supplier = fake.company()
        procurement_officer = random.choice(procurement_officers)

        procurement_method = random.choices(methods, weights=frequencies, k=1)[0]
        # methods and frequencies are aligned by position in their respective lists


        ### Retrieving available_items from procurement_data based on the procurement method ###

        # procurement_data is a pandas DataFrame containing procurement data
        # returns a NEW DataFrame filtered -> containing only the filtered rows
        available_items = procurement_data[procurement_data['Method'] == procurement_method]
        
        ### ---------


        ### This is where we pick the item row from the available items ###

        # .sample(1) randomly selects one row from the available items DataFrame
        # returns a DataFrame with 1 row
        # .iloc[0] is used to access the first row of the resulting DataFrame

        # .sample(1) is like drawing one card from a deck of available items
        # .iloc[0] pulls out that first card from the array
        # output is a series (array)

        item_row = available_items.sample(1).iloc[0]
        
        ### ---------


         

        item_name = item_row['Item_Name']
        item_avg_price_info = average_price_data.get(item_name)
        average_price = item_row['Base_Price'] # Default if not found
        if item_avg_price_info:
            average_price = item_avg_price_info.get('average_price', average_price)
        else: 
            logger.warning(f"Average price for {item_name} not found in the data. Using default base price.")
            # This is to avoid crashing if the item is not found in the average price data


        ### Determining Volatility
        if procurement_method in ["Negotiated Procurement", "Direct Contracting"]:
            volatility = volatility_high
        else:
            volatility = volatility_medium
         
        
        ### Price based on average_price multiplied to set volatility
        unit_price = average_price * (1 + random.uniform(-volatility, volatility))
        # random.uniform selects a float from the given range (lower bound, uper bound)
        unit_price = round(unit_price, 2)

         # !!! Make columns match with dataframe variable !!!
        data.append([
            i+1, item_name, quantity, procurement_method, 
            unit_price, average_price, supplier, procurement_officer, 
            transaction_date
        ])


    # !!! Make columns match with data variable !!!
    dataframe = pd.DataFrame(data, columns= [
        'transaction_id', 'item_name', 'quantity', 'procurement_method', 'unit_price', 'average_price', 'supplier', 'procurement_officer','transaction_date'])
    
    ### Exporting dataframe to CSV ###
    save_dir = os.path.join(os.getcwd(), 'transactions_folder')
    os.makedirs(save_dir, exist_ok=True)  # Create directory if it doesn't exist

    csv_filename = f"simulated_transactions_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
    csv_file_path = os.path.join(save_dir, csv_filename)
    
    dataframe.to_csv(csv_file_path, index=False)

    logger.info(f"Transaction data {csv_filename} generated successfully with {num_transactions} records.")
    logger.info(f"Transaction data saved to {csv_file_path}.")

    return


if __name__ == "__main__":
    # Example usage
    generate_transaction_data(scrape_num=10, num_transactions=1000)
    # The scrape_num is the number of items to scrape from the web.
    # The num_transactions is the number of transactions to generate.