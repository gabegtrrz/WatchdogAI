import unittest
import pandas as pd
from data_generator import generate_blockchain_data


class TestDataGen(unittest.TestCase):


    def setUp(self):
        # This runs before every test to create some test data
        self.num_transactions = 5  # Small number for quick tests
        self.df = generate_blockchain_data(num_transactions=self.num_transactions)
    
    def test_blockchain_data_basic(self):
        self.assertIsInstance(self.df, pd.DataFrame)  # Check if it's a DataFrame
        self.assertEqual(len(self.df), self.num_transactions)  # Check number of rows

        expected_columns = [
            'transaction_id', 'item_name', 'quantity', 'unit_price',
            'procurement_method', 'supplier', 'procurement_officer',
            'transaction_date', 'previous_hash', 'block_hash'
        ]

        actual_columns = list(self.df.columns)
        self.assertListEqual(actual_columns, expected_columns)  # Check column names

        self.assertEqual(self.df["previous_hash"][0], "0")  # Check genesis block
    
    def test_blockchain_data_types(self):
        self.assertEqual(self.df['quanitity'].dtype, 'int64')  # Check if quantity is integer
        self.assertEqual(self.df['unit_price'].dtype, 'float64')   # Check if quantity is float
        self.df['transaction_date'] =pd.to_datetime(self.df['transaction_date'], format='%Y-%m-%d') # Converts the column to datetime64
        self.assertEqual(self.df['transaction_date'].dtype, 'datetime64[ns]')
    
    def test_transaction_ids_are_unique(self):
        #Makes sure every transaction has a unique ID
        # Get all transaction_IDs from the 'transaction_id' column
        ids = self.df['transaction_id']
        #turning them into a set to remove duplicates
        unique_ids = set(ids)
        self.assertEqual(len(unique_ids), len(ids))

    def test_hash_chain_connects(self):
        # check that each block’s previous_hash matches the last block’s block_hash.
        # Get the previous_hash and block_hash columns
        previous_hashes = self.df['previous_hash']
        block_hashes = self.df['block_hash']
        # Loop through all rows except the first (since it uses '0' as previous_hash)
        for i in range(1, len(previous_hashes)):
            # The previous_hash of this row should match the block_hash of the row before it
            self.assertEqual(previous_hashes[i], block_hashes[i - 1])

if __name__ == '__main__': unittest.main()