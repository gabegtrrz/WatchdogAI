import pandas as pd
import numpy as np
import hashlib
import random
from faker import Faker
from data.procurement_data import BASE_PRICES

fake = Faker()

def generate_blockchain_data(num_transactions = 1000, base_prices = BASE_PRICES):
    data = []
    previous_hash = '0' # Genesis Block


    volatility = 0.10

    procurement_officers = [
        'Casey Hernandez',
        'Alex Rivera',
        'James Patrick Mendoza',
        'Morgan Cruz',
        'Angela Ramirez',
        'Taylor Martinez',
        'Sophia Christine Navarro',
        'Angela Renee Mendoza',
        'Luke Andrew Navarro',
        'Jamie Thompson',
        'Christine Bautista',
        ]

    # for training data, procurement methods shall be a dictionary that applies common procurement methods
    # appropriately for each item.

    # need to edit this below: update the item values accordingly
    
    ''' WE NEED TO PUT THIS IN PROCUREMENT_DATA.PY
    procurement_methods = {
    "Competitive Bidding": {
        "items": ["Compound Microscope (1000x)", "Refracting Telescope (70mm)", "Beaker (50ml)", "Beaker (100ml)", "Beaker (250ml)", "Beaker (500ml)", "Test Tube (10ml)", "Test Tube (20ml)", "Bunsen Burner", "Triple Beam Balance", "Microscope Slides (box of 50)", "Microscope Coverslips (box of 100)", "Dissecting Kit (basic)", "Sodium Chloride (NaCl) - Solid (1kg)", "Hydrochloric Acid (HCl) - 1M (1L)", "Lab Manual - Grade 10 Science"],
        "frequency": 0.5
    },
    "Limited Source Bidding": {
        "items": ["Reflecting Telescope (150mm)", "Digital Spectrophotometer", "Data Analysis Software (Logger Pro)", "High-Precision Balance"],
        "frequency": 0.2
    },
    "Negotiated Procurement": {
        "items": ["Potassium Iodide (KI) - Solid (500g)", "AmScope M150B-LED Replacement LED Bulb", "Beaker (1000ml)"],
        "frequency": 0.2
    },
    "Direct Contracting": {
        "items": ['Calibration Service (for high-precision balance)', "Replacement Xenon Flash Lamp for Do PerkinElmer", "Sulfuric Acid (H2SO4) - 1M (1L)"], 
        "frequency": 0.1
    }
    }
    '''

    for i in range(num_transactions):
        # timestamp object converted into str for immutability
        timestamp = fake.date_time_between(start_date='-1y',end_date='now').strftime('%Y-%m-%d %H:%M:%S')
        transaction_date = timestamp.split(' ')[0]

        quantity = random.randint(1000, 10000)
        supplier = fake.company()
        procurement_officer = random.choice(procurement_officers)



        ### Procurement_method
        
        # Procurement Method selection
        methods = list(procurement_methods.keys())
        frequencies = [procurement_methods[method]['frequency'] for method in methods]
        procurement_method = random.choices(methods, weights=frequencies)[0]

        ### Item selection
        available_items = procurement_methods[procurement_method]["items"]
        item_name = random.choice(available_items)

        ### Volatility based on procurement method
        if procurement_method == "Negotiated Procurement" or procurement_method == "Direct Contracting":
            volatility = 0.15 # Higher Volatility for these methods
        else:
            volatility = 0.10 #Standard Volatility
        
        ### Price based on base_prices multiplied to set volatility
        unit_price = base_prices[item_name] * (1 + random.uniform(-volatility, volatility))
        unit_price = round(unit_price, 2)


        ### HASHING
        hash_string = f"{timestamp}{item_name}{quantity}
        {unit_price}{procurement_method}{supplier}{procurement_officer}
        {transaction_date}"
        

        block_hash = hashlib.sha256(hash_string.encode()).hexdigest
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
        'transaction id', 'item_name', 'quantity', 'unit_price', 'procurement_method', 'supplier', 'procurement_officer','transaction_date', 'previous_hash', 'block_hash'])
    
    return dataframe