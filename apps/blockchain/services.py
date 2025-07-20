'''
Contains the functions that manage the blockchain.
'''

from .models import Block
from apps.core.models import Transaction
from django.utils import timezone
import hashlib
import json
from django.db import transaction as db_transaction # For atomic operations
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

def get_latest_block():
    """
    Returns the most recent block in the chain.

    Returns:
        Block or None: The latest Block object if it exists, otherwise None.
    """
    try:
        return Block.objects.order_by('-index').first()
    except Exception as e:
        logger.error(f"Error retrieving latest block: {e}")
        return None

def create_genesis_block():
    """
    Creates the very first block in the chain if it doesn't already exist.

    Returns:
        Block or None: The created genesis block, or the existing one if it already
                       was created, or None if an error occurred.
    """
    try:
        if not Block.objects.exists():
            genesis_block = Block(
                index=0,
                previous_hash="0",
                timestamp=timezone.now() # Set timestamp for genesis block
            )
            genesis_block.hash = genesis_block.calculate_hash()
            genesis_block.save()
            logger.info("Genesis block created successfully.")
            return genesis_block
        else:
            logger.info("Genesis block already exists.")
            return Block.objects.get(index=0)
    except Exception as e:
        logger.critical(f"Critical error creating genesis block: {e}")
        return None

def create_new_block(transactions):
    """
    Creates a new block, assigns the provided transactions to it, and adds it to the chain.

    Args:
        transactions (list): A list of Transaction objects to be included in the new block.

    Returns:
        Block or None: The newly created Block object if successful, None otherwise.
    """
    latest_block = get_latest_block()
    if not latest_block:
        logger.warning("No latest block found. Attempting to create genesis block.")
        latest_block = create_genesis_block()
        if not latest_block:
            logger.error("Failed to create genesis block, cannot create new block.")
            return None

    # Database transaction .atomic() ensurs this whole process succeeds or fails together
    try:
        with db_transaction.atomic():
            ### 1. Create the new block instance.
            new_block = Block.objects.create(
                index=latest_block.index + 1,
                previous_hash=latest_block.hash,
                timestamp=timezone.now() # Set timestamp for the new block
            )

            ### 2. Update all the provided transactions to link them to the new block.
            # Validate transactions before linking
            for tx in transactions:
                if not isinstance(tx, Transaction):
                    raise TypeError(f"Invalid transaction type provided: {type(tx)}. Expected Transaction object.")
                if tx.block is not None:
                    logger.warning(f"Transaction {tx.transaction_id} is already associated with a block. Skipping.")
                    continue # Skip transactions already linked to a block
                tx.block = new_block
                tx.save()

            # NEXT step must only happen AFTER transactions are linked and saved, as block hash depends on them.

            ### 3. Now that the transactions are linked, calculate the block's final hash.
          
            new_block.hash = new_block.calculate_hash()
            new_block.save()

        logger.info(f"New block with index {new_block.index} created successfully.")
        return new_block
    except TypeError as e:
        logger.error(f"Error creating new block due to invalid transaction type: {e}")
        return None
    except Exception as e:
        logger.error(f"Error creating new block: {e}")
        return None


def verify_blockchain_integrity():
    """
    Verifies the integrity of the entire blockchain by checking hash links and recalculated hashes.

    Returns:
        bool: True if the chain is valid, False otherwise.
    """
    try:
        logger.info("Initiating blockchain integrity check")

        # Get all blocks in the chain and order them by index.
        logger.info("Getting all blocks in the chain and ordering them by index.")
        blocks = Block.objects.order_by('index')
        if not blocks.exists():
            logger.warning("No blocks found in the blockchain to verify integrity. Creating genesis block.")
            create_genesis_block()

        logger.info("Starting blockchain integrity verification.")

        previous_block = None

        for block in blocks:

            ### if Genesis block
            if block.index == 0:  
                # For the genesis block, only check its own hash if it exists.
                # No previous hash to compare against.
                recalculated_hash = block.calculate_hash()
                if block.hash != recalculated_hash:
                    logger.error(f"Genesis block (index 0) hash mismatch. Stored: {block.hash}, Recalculated: {recalculated_hash}")
                    return False
                previous_block = block
                continue

            # 1. Check if the previous_hash of the current block matches the hash of the previous block.
            if previous_block and block.previous_hash != previous_block.hash:
                logger.error(f"Block {block.index}: Previous hash mismatch. Expected {previous_block.hash}, Got {block.previous_hash}")
                return False

            # 2. Recalculate the hash of the current block and see if it matches the stored hash.
            recalculated_hash = block.calculate_hash()
            if block.hash != recalculated_hash:
                logger.error(f"Block {block.index}: Hash mismatch. Stored: {block.hash}, Recalculated: {recalculated_hash}")
                return False

            previous_block = block
        
        logger.info("Blockchain integrity verified successfully. The chain is valid.")
        return True
        
    except Exception as e:
        logger.critical(f"An unexpected error occurred during blockchain integrity verification: {e}")
        return False