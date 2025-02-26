import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from realtime_data_generator import generate_realtime_price_data
from procurement_data_config import ITEMS, BASE_PRICES, VOLATILITY_LOW

class TestRealtimePriceData(unittest.TestCase):
    
    def setUp(self):
        self.test_items = ITEMS[:3]
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
        # we want that item_prices does not exceed specified volatility which
        # in this case is VOLATILITY_LOW

        for item in self.test_items:
            item_prices = self.df[self.df['item'] == item]['price']
            base_price = BASE_PRICES[item]

            ### check Lower & upper bound

            #     This is a pandas Series comparison:
            #     item_prices is a Sries (e.g. [340.12, 338.00, 332.89]).
            #     base_price * (1 - volstility) is a scalar (e.g., 317.89).
            #     Pandas “broadcasts” the scalar across the Series, checking each element.

            #     Result: A boolean Series:
            #     [340.12 >= 317.89, 338.00 >= 317.89, 332.89 >= 317.89]
            #     = [True, True, True]
             
            # check lower bound:
            self.assertTrue((item_prices >= (base_price * (1-volatility))).all) 
            # .all() checks if all values in the series are True

            #check upper bound:
            self.assertTrue((item_prices <= (base_price * (1+volatility))).all)

    def test_price_rounding (self):
         prices = self.df['prices']
         self.assertTrue(all(prices == round(price,2) for price in prices))
         # generator experession generates booleans (true or false if rounded in 2 decimals)
         #  .all() function takes an iterable (here, the generator expression)
         # and returns true if every value is true, False if any are false

    def test_invalid_items(self):
         #tests if an item is not in base_prices -> error

         invalid_items = ['Non-existent Item 1', 'Non-existent Item 2']

         try:
              generate_realtime_price_data(invalid_items, numdays=5)
              # if we get here, no error happened, which is bad bruhhh
              self.fail("expected KeyError, but no error occured")
         except KeyError:
              # if KeyError arose, test passes bc this is what we want
              pass


if __name__ == '__main__':
        unittest.main()