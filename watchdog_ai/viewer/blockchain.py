import json
import hashlib
from datetime import datetime

class Block:
    def __init__(self, blocknum, timestamp, transaction_data, previous_hash):
        self.blocknum = blocknum
        self.timestamp = timestamp
        self.transaction_data = transaction_data # This will store the procurement transaction details
        self.previous_hash = previous_hash
        self.block_hash = self.calculate_hash()

    def calculate_hash(self):
        #Sort keys to ensure hash consistency regardless of dictionary order
        block_string = json.dumps({
            "blocknum": self.blocknum,
            "timestamp": str(self.timestamp), # Convrt timestamp to string
            "transaction_data": self.transaction_data,
            "previous_hash": self.previous_hash
        }, sort_keys=True).encode() # Encode the string to bytes
        
        # Use SHA-256 for hashing
        return hashlib.sha256(block_string).hexdigest()

class Blockchain:
    def __init__(self):

        self.chain = [] #Squence of blcoks in memory

    ### Genesis block if the first block in the blockchain ###

    def create_genesis_block(self):
        if not self.chain:
            genesis_block = Block(0, datetime.now(), "Genesis Block", "0")
            self.chain.append(genesis_block)
    
    def get_latest_block(self):
        if not self.chain:
            self.create_genesis_block()
        return self.chain[-1]
    
    def add_block(self, new_block):
        latest_block = self.get_latest_block()
        
        new_block.previous_hash = latest_block.block_hash
        new_block.blocknum = latest_block.blocknum + 1
        new_block.blockhash = new_block.calculate_hash()
        self.chain.append(new_block)
    
    def is_chain_valid(self):
        ''' checking in memory chain'''
        