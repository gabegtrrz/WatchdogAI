import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from realtime_data import generate_realtime_price_data

class TestRealtimePriceData(unittest.TestCase):
    
    def setUp(self):
        self.test_items = [
            'Compound Microscope (1000x)',
            'Beaker (50ml)', "Bunsen Burner"
        ]
        self.num_days = '5'
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
    def test_item_present(self):
        var= self.df['item']
        print(var)


    def test_date_range(self):
        # Test that the date range is correct
        return None