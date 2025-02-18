import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_realtime_price_data (items, numdays=365):
    price_data = []
    start_date = datetime.now() - timedelta(days=numdays)

    base_prices = {
        # base prices per item
        # EXAMPLES ONLY
        'Laptop': 800,
        'Projector': 300,
        'Books': 20,
        'Software License': 150,
        'Printer': 200
    }


