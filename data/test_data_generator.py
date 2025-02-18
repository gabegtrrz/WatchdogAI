import unittest
import pandas as pd
from data_generator import generate_blockchain_data


class TestDataGen(unittest.TestCase):

    def test_blockchain_data_basic(self):
        df = generate_blockchain_data(100)
        self.assertIsInstance(df, pd.DataFrame)  # Check if it's a DataFrame
        self.assertEqual(len(df), 100)  # Check number of rows
        self.assertListEqual(
            list(df.columns),
            [
                "transaction id",
                "item_name",
                "quantity",
                "unit_price",
                "supplier",
                " procurement_officer",
                "transaction_date",
                "previous_hash",
                "current_hash",
            ],
        )  # Check column names
        self.assertEqual(df["previous_hash"][0], "0")  # Check genesis block
