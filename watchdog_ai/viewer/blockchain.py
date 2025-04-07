import json
import hashlib
from datetime import datetime
from decimal import Decimal

class Block:
    ''' represents a single block in the simulated blockchain '''
    def __init__(self, index, timestamp, transaction_data, previous_hash):

        self.index = index
        self.timestamp = timestamp
        self.transaction_data = transaction_data
        # This will store the procurement transaction details
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    # def prepare_transaction_data(self,data):
        ''' ensures transaction data is in correct format '''
    
    def calculate_hash(self):
        
        #sort_keys=True to ensure hash consistency regardless of dictionary order
        block_string = json.dumps({
            "index": self.index,
            "timestamp": str(self.timestamp), # Convrt timestamp to string
            "transaction_data": self.transaction_data,
            "previous_hash": self.previous_hash
        }, sort_keys=True).encode() # Encode the string to bytes
        
        # Use SHA-256 for hashing
        return hashlib.sha256(block_string).hexdigest()


### Helper function for creating block instances before saving to DB###

def create_new_block(validated_transaction_data, last_block_index, last_block_hash):
    """
    Creates a new Block instance (not yet saved, but) ready to be added to the simulated blockchain

    Args:
        validated_transaction_data (dict)
        last_block_index (int)
        last_block_hash (str)

    """

    timestamp = datetime.now()
    new_index = last_block_index + 1

    # Create the block instance
    block = Block(index=new_index, 
                  timestamp=timestamp, 
                  transaction_data=validated_transaction_data, 
                  previous_hash=last_block_hash)
    # The hash is calculated within the Block's __init__

    return block




# class Blockchain:
#     def __init__(self):

#         self.chain = [] #Squence of blcoks in memory

#     ### Genesis block if the first block in the blockchain ###

#     def create_genesis_block(self):
#         if not self.chain:
#             genesis_block = Block(0, datetime.now(), "Genesis Block", "0")
#             self.chain.append(genesis_block)
    
#     def get_latest_block(self):
#         if not self.chain:
#             self.create_genesis_block()
#         return self.chain[-1]
    
#     def add_block(self, new_block):
#         latest_block = self.get_latest_block()
        
#         new_block.previous_hash = latest_block.hash
#         new_block.index = latest_block.index + 1
#         new_block.blockhash = new_block.calculate_hash()
#         self.chain.append(new_block)
    
#     def is_chain_valid(self):
#         ''' checking in memory chain. MUST BE EXISTING'''
#         for i in range(1, len(self.chain)):
#             current_block = self.chain[i]
#             previous_block  = self.chain[i-1]

#             # recalculate hashes
#             if current_block.hash != current_block.calculate_hash():
#                 print(f"Data Tampering Detected: Block {current_block} hash mismatch")
#                 return False
#             if current_block.previous_hash != previous_block.hash:
#                 print(f"Chain Corrupted: {current_block} previous hash mismatch")
        
#         print("Chain Verification Succesful: No tampering detected")
#         return True




        