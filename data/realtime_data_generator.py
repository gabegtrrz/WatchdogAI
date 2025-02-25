import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from data.procurement_data import ITEMS, BASE_PRICES, VOLATILITY_LOW



def generate_realtime_price_data (items = ITEMS, numdays=365, volatility = VOLATILITY_LOW, base_prices = BASE_PRICES):
    
    ### Here is where the data will be stored ###

    price_data = []
    start_date = datetime.now() - timedelta(days=numdays)


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


