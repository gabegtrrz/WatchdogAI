import pandas as pd
import numpy as np
import hashlib
import random
from faker import Faker

fake = Faker()

def generate_blockchain_data(num_transactions = 1000):
    data = []
    previous_hash = '0' # Genesis Block

    item_list = [
        'Physics: Student book', 'Acer Aspire 5 A515-56G-551P', 'Casio fx-991EX Scientific Calculator', 'Canon PIXMA G3010 Printer',
        'Magnifying Glass with LED Light (3X & 10X Zoom)', 'Modern Periodic Table Of The Elements (Size 12X17.5 Inches)', 'Magnetic Whiteboard 30 x 40cm',
        'VEVOR Rotating World Globe with Stand 13 in/330.2 mm Diameter', 'Exam Gloves Box/100',
        'Uvex Ultravision Goggles'
        ]
    
    base_prices = {
        'Physics:Student book': 11393.02,
        'Acer Aspire 5 A515-56G-551P': 36997,
        'Casio fx-991EX Scientific Calculator': 1259.46,
        'Canon PIXMA G3010 Printer': 8795,
        'Magnifying Glass with LED Light (3X & 10X Zoom)': 556.86,
        'Modern Periodic Table Of The Elements (Size 12X17.5 Inches)': 38,
        'Magnetic Whiteboard 30 x 40cm': 149,
        'VEVOR Rotating World Globe with Stand 13 in/330.2 mm Diameter': 2757.58,
        'Exam Gloves Box/100': 571.96,
        'Uvex Ultravision Goggles': 41794.49
    }

    volatility = 0.10

    procurement_officers = [
        # input 12 procurement officer names as list
        # e.g.
        # John Dela Cruz,
        ]

    # for training data, procurement methods shall be a dictionary that applies common procurement methods
    # appropriately for each item. item_list must be done first
    procurement_methods = [
        'Competitive Bidding', 'Limited Source Bidding', 
        'Negotiated Procurement', 'Direct Contracting'
    ]

    for i in range(num_transactions):
        # timestamp object converted into str for immutability
        timestamp = fake.date_time_between(start_date='-1y',end_date='now').strftime('%Y-%m-%d %H:%M:%S')
        transaction_date = timestamp.split(' ')[0]
        item_name = random.choice(item_list)

        # price based on base_prices multiplied to set volatility
        unit_price = base_prices[item_name] * (1 + random.uniform(-volatility, volatility))
        unit_price = round(unit_price, 2)

        quantity = random.randint(1000, 10000)
        supplier = fake.company()
        procurement_officer = random.choice(procurement_officers)



        # procurement_method =
        # for training data, procurement methods shall be a dictionary that applies common procurement methods
        # appropriately for each item. item_list must be done first
        # don't forget to add procurement_method to hash string and data.append()


        # HASHING

        # don't forget to add procurement_method to hash string
        hash_string = f"{timestamp}{item_name}{quantity}
        {unit_price}{supplier}{procurement_officer}
        {transaction_date}"
        

        current_hash = hashlib.sha256(hash_string.encode()).hexdigest
        # current_hash is made into the hexadecimal hash from the hash_string

        # don't forget to add procurement_method
        data.append([
            i+1, item_name, quantity, 
            unit_price, supplier, procurement_officer, 
            transaction_date, previous_hash, current_hash,
        ])

        # setting up the previous hash for next iteration
        previous_hash = current_hash

    dataframe = pd.DataFrame(data, columns= [
        'transaction id', 'item_name', 'quantity', 'unit_price', 'supplier', ' procurement_officer','transaction_date', 'previous_hash', 'current_hash'])
    
    return dataframe







