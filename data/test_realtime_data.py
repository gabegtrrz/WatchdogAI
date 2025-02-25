import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.realtime_data_generator import generate_realtime_price_data
from data.item_list import ITEMS, BASE_PRICES, VOLATILITY_LOW

class TestRealtimePriceData(unittest.TestCase):
    
    def setUp(self):
        self.test_items = [
            'Compound Microscope (1000x)',
            'Beaker (50ml)', "Bunsen Burner"
        ]
        self.num_days = 5
        self.df = generate_realtime_price_data(self.test_items, numdays=self.num_days)

    def test_structure(self):
        self.assertIsInstance(self.df, pd.DataFrame)
        self.assertEqual(list(self.df.columns), ['item', 'date', 'price'])
        
        expected_rows = len(self.test_items) * self.num_days
        self.assertEqual(expected_rows, len(self.df))
        # len(self.df) returns the number of rows.

    # Test that all input items are found in the outputted dataframe.
    # input: items
    # output: unique items
    # success = all input items are found in output 
    def test_items_present(self):
        unique_items = self.df['item'].unique() # .unique() is more efficient utilizing pandas internal DS
        self.assertEqual (set(unique_items), set(self.test_items))
        # made them sets so they don't fail equality due to difference in order

    def test_date_range(self):
        # Test that the date range is correct

        start_date = (datetime.now() - timedelta(days = self.num_days)).strftime('%Y-%m-%d')

        # end_date = (datetime.now() - timedelta(days = 1)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        dates = self.df['date'].unique()
        # .unique() returns sorted array by retrieved arrangement
        # therefore accessible via first and last index
        self.assertEqual(dates[0], start_date)
        self.assertEqual(dates[-1],end_date)
    
    def test_price_greater_than_zero(self):
         self.assertTrue((self.df['price'] > 0).all())

    def test_price_volatility(self, base_prices = BASE_PRICES, volatility = VOLATILITY_LOW):
         # To test that price volatilty is within reasonable bounds




if __name__ == '__main__':
        unittest.main()