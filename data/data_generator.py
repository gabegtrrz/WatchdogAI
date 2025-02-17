import pandas as pd
import numpy as np
import hashlib
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

def generate_blockchain_data(num_transactions = 1000):
    data = []
    previous_hash = '0' # Genesis Block

    item_list = ['Science Textbook for Grade 10', 'Acer Aspire 5 A515-56G-551P', ]
    base_prices = {
        'item 1': 12345,
        'item 2': 123
    }
    volatility = 0.10

    procurement_officers = [
        # input 12 procurement officer names as list
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






