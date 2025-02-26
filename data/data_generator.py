import pandas as pd
import numpy as np
import hashlib
import random
from faker import Faker
from procurement_data_config import PROCUREMENT_DATA, PROCUREMENT_OFFICERS, VOLATILITY_MEDIUM, VOLATILITY_HIGH, BASE_PRICES

fake = Faker()

def generate_blockchain_data(num_transactions = 1000, procurement_data = PROCUREMENT_DATA, procurement_officers = PROCUREMENT_OFFICERS, volatility_medium = VOLATILITY_MEDIUM, volatility_high = VOLATILITY_HIGH, base_prices = BASE_PRICES):
    data = []
    previous_hash = '0' # Genesis Block
    
    # Get PROCUREMENT_DATA values
    methods_and_frequencies = procurement_data.groupby('Method')['Frequency'].first() #This is a pandas series
    methods = methods_and_frequencies.index.tolist()
    frequencies = methods_and_frequencies.values.tolist()

    for i in range(num_transactions):
        # timestamp object converted into str for immutability
        timestamp = fake.date_time_between(start_date='-1y',end_date='now').strftime('%Y-%m-%d %H:%M:%S')
        transaction_date = timestamp.split(' ')[0]

        quantity = random.randint(1000, 10000)
        supplier = fake.company()
        procurement_officer = random.choice(PROCUREMENT_OFFICERS)

        procurement_method = random.choices(methods, weights=frequencies, k=1)[0]
        # methods and frequencies are aligned by position in their respective lists


        available_items = procurement_data[procurement_data['Method'] == procurement_method]
        # returns a NEW DataFrame filtered -> containing only the filtered rows


        item_row = available_items.sample(1).iloc[0]
        # .sample(1) is like drawing one card from a deck of available items
        # .iloc[0] pulls out that first card from the array
        # output is a series (array)

        item_name = item_row['Item_Name']
        base_price = item_row['Base_Price']


        ### Determining Volatility
        if procurement_method in ["Negotiated Procurement", "Direct Contracting"]:
            volatility = VOLATILITY_HIGH
        else:
            volatility = VOLATILITY_MEDIUM
         
        
        ### Price based on base_prices multiplied to set volatility
        unit_price = base_prices[item_name] * (1 + random.uniform(-volatility, volatility))
        # random.uniform selects a float from the given range (lower bound, uper bound)
        unit_price = round(unit_price, 2)


        ### HASHING
        hash_string = f"{timestamp}{item_name}{quantity}{unit_price}{procurement_method}{supplier}{procurement_officer}{transaction_date}"
        

        block_hash = hashlib.sha256(hash_string.encode()).hexdigest()
        # block_hash is made into the hexadecimal hash from the hash_string

        
        data.append([
            i+1, item_name, quantity, 
            unit_price, procurement_method, supplier, procurement_officer, 
            transaction_date, previous_hash, block_hash,
        ])

        # setting up the previous hash for next iteration
        previous_hash = block_hash

    # !!! update columns !!!
    dataframe = pd.DataFrame(data, columns= [
        'transaction_id', 'item_name', 'quantity', 'unit_price', 'procurement_method', 'supplier', 'procurement_officer','transaction_date', 'previous_hash', 'block_hash'])
    
    return dataframe