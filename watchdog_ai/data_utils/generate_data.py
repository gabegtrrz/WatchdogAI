# Data nad Logic Imports
import hashlib
import random
from faker import Faker
from datetime import datetime, timedelta

# File Handling Imports
import pandas as pd
import json

# Local Imports 
from watchdog_ai.data_utils.procurement_data_config import PROCUREMENT_DATA, PROCUREMENT_OFFICERS, VOLATILITY_LOW, VOLATILITY_MEDIUM, VOLATILITY_HIGH
from watchdog_ai.data_utils import scraper

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


fake = Faker()


SCRAPER_OUTPUT_FILE = scraper.OUTPUT_JSON_FULL_PATH


def load_average_prices():
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
        
def generate_transaction_data(num_transactions = 1000, procurement_data = PROCUREMENT_DATA, procurement_officers = PROCUREMENT_OFFICERS, volatility_medium = VOLATILITY_MEDIUM, volatility_high = VOLATILITY_HIGH,):
    ''' This is to generate clean or normal transaction data FOR TRAINING. '''


    ### Ensure average_price data is up-to-date ###
    scraper.check_and_run_scraper_if_needed()

    data = []
    
    # Get procurement methods and appropriate frequency from procurement_data values
    methods_and_frequencies = procurement_data.groupby('Method')['Frequency'].first() #This is a pandas series
    methods = methods_and_frequencies.index.tolist() #List of Methods
    frequencies = methods_and_frequencies.values.tolist() #List of frequencies

    for i in range(num_transactions):
        # timestamp object converted into str for immutability
        timestamp = fake.date_time_between(start_date='-1y',end_date='now').strftime('%Y-%m-%d %H:%M:%S')
        transaction_date = timestamp.split(' ')[0]

        quantity = random.randint(1000, 10000)
        supplier = fake.company()
        procurement_officer = random.choice(procurement_officers)

        procurement_method = random.choices(methods, weights=frequencies, k=1)[0]
        # methods and frequencies are aligned by position in their respective lists


        available_items = procurement_data[procurement_data['Method'] == procurement_method]
        # returns a NEW DataFrame filtered -> containing only the filtered rows


        ### This is where we pick the item row from the available items:
        # .sample(1) randomly selects one row from the available items DataFrame and outputs a DataFrame with one row
        # .iloc[0] is used to access the first row of the resulting DataFrame

        item_row = available_items.sample(1).iloc[0]
        # .sample(1) is like drawing one card from a deck of available items
        # .iloc[0] pulls out that first card from the array
        # output is a series (array)

        #average_price = 

        item_name = item_row['Item_Name']
        base_price = item_row['Base_Price'] #not the actual price

        ### Determining Volatility
        if procurement_method in ["Negotiated Procurement", "Direct Contracting"]:
            volatility = volatility_high
        else:
            volatility = volatility_medium
         
        
        ### Price based on base_prices multiplied to set volatility
        unit_price = base_price * (1 + random.uniform(-volatility, volatility))
        # random.uniform selects a float from the given range (lower bound, uper bound)
        unit_price = round(unit_price, 2)

        
        # data.append([
        #     i+1, item_name, quantity, procurement_method, 
        #     unit_price, average_price, supplier, procurement_officer, 
        #     transaction_date,
        # ])


    # !!! update columns !!!
    dataframe = pd.DataFrame(data, columns= [
        'transaction_id', 'item_name', 'quantity', 'procurement_method', 'unit_price', 'average_price', 'supplier', 'procurement_officer','transaction_date',])
    
    return dataframe
