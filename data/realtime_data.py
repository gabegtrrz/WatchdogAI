import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_realtime_price_data (items, numdays=365):
    price_data = []
    start_date = datetime.now() - timedelta(days=numdays)

    base_prices = {
        # base prices per item
        # BELOW ARE ONLY EXAMPLES 
        'Laptop': 800,
        'Projector': 300,
        'Books': 20,
        'Software License': 150,
        'Printer': 200
    }

    # Volatility factor (adjust for overall price fluctuation)
    volatility = 0.05  # 5% volatility

    for item in items:
        # output:
        # columns = items
        # rows = daily price data with volatility

        current_price = base_prices[item] * (1+random.uniform(-volatility, volatility))
        price_history = [current_price]
        
        for i in range(numdays):
            date= start_date + timedelta(days=i)

            price_change = price_history[-1] * random.uniform(-volatility/2, volatility/2)
            current_price = price_history[-1] + price_change
            
            # ensure current_price is non-zero and non-negative
            if current_price <=0:
                current_price = price_history[-1]

            #add to price_history
            price_history.append(current_price)
            price_data.append([item, date.strftime('%Y-%m-%d'), round(current_price,2)])

    df = pd.DataFrame(price_data, columns= ['item', 'date', 'price'])
    return df


