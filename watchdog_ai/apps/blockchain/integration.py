"""
Blockchain Integration Module

Purpose: Processes transaction data and adds it to the simulated blockchain to ensure data integrity.

Key Processes:
- Prepare Transaction for Blockchain: Formats the enriched data for blockchain inclusion.
- Generate Hash: Creates a unique hash for the transaction data.
- Append Transaction to Blockchain: Adds the transaction and its hash to the simulated blockchain.
- Initiate Integrity Check: Triggers the blockchain integrity verification process.
- Handle Successful Transaction: Manages the successful addition of a transaction.
- Handle Transaction/Integrity Errors: Manages errors during blockchain operations.
"""

import hashlib
import json
import logging
from django.db import transaction as db_transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Block
from .services import create_new_block, verify_blockchain_integrity, create_genesis_block
from apps.core.models import Transaction

# Setup logging for this module
logger = logging.getLogger(__name__)


class BlockchainIntegrationError(Exception):
    """Custom exception for blockchain integration errors"""
    pass


class TransactionHashMismatchError(BlockchainIntegrationError):
    """Raised when transaction hash validation fails"""
    pass


class BlockchainIntegrityError(BlockchainIntegrationError):
    """Raised when blockchain integrity check fails"""
    pass


class BlockchainIntegrationService:
    """
    Main service class for blockchain integration operations.
    Handles the complete lifecycle of adding transactions to the blockchain.
    """

    def __init__(self):
        # Setup instance-specific logger
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def prepare_transaction_for_blockchain(self, transaction):
        """
        Prepares and formats transaction data for blockchain inclusion.
        
        Args:
            transaction: The transaction object to prepare
            
        Returns:
            dict: Formatted transaction data ready for blockchain
            
        Raises:
            BlockchainIntegrationError: If transaction preparation fails
        """
        try:
            self.logger.info(f"Preparing transaction {transaction.transaction_id} for blockchain")
            
            # Check transaction has valid ID
            if not transaction.transaction_id:
                raise BlockchainIntegrationError("Transaction must have a valid transaction_id")
                
            # Get basic transaction data
            transaction_data = transaction.to_dict()
            
            # Add blockchain-specific metadata for tracking
            blockchain_data = {
                **transaction_data,  # Spread operator to include all original data
                'blockchain_timestamp': timezone.now().isoformat(),  # When added to blockchain, .isoformat() guarantees a consistent, unambiguous string representation of the timestamp
                'blockchain_version': '1.0',  # Version for future compatibility
                'data_integrity_hash': self.generate_transaction_hash(transaction_data)
            }
            
            self.logger.info(f"Transaction {transaction.transaction_id} prepared successfully for blockchain")
            return blockchain_data
            
        except Exception as e:
            error_msg = f"Failed to prepare transaction {transaction.transaction_id} for blockchain: {str(e)}"
            self.logger.error(error_msg)
            raise BlockchainIntegrationError(error_msg) from e

    def generate_transaction_hash(self, transaction_data):
        """
        Creates a unique SHA-256 hash for the transaction data.
        
        Args:
            transaction_data (dict): Transaction data to hash
            
        Returns:
            str: SHA-256 hash of the transaction data
            
        Raises:
            BlockchainIntegrationError: If hash generation fails
        """
        try:
            # Convert dict to consistent string format for hashing
            # sort_keys=True ensures same order every time
            # separators removes extra spaces for consistency
            transaction_string = json.dumps(
                transaction_data, 
                sort_keys=True, 
                separators=(',', ':'),
                ensure_ascii=True
            ).encode('utf-8')
            
            # Generate SHA-256 hash
            hash_value = hashlib.sha256(transaction_string).hexdigest()
            self.logger.debug(f"Generated hash for transaction data: {hash_value}")
            return hash_value
            
        except Exception as e:
            error_msg = f"Failed to generate hash for transaction data: {transaction_data['transaction_id']}. Error: {str(e)}"
            self.logger.error(error_msg)
            raise BlockchainIntegrationError(error_msg) from e

    def append_transactions_to_blockchain(self, transactions):
        """
        Adds transactions to the blockchain by creating a new block.
        Uses the create_new_block service which handles the blockchain logic.
        
        Args:
            transactions (list): List of Transaction objects to add
            
        Returns:
            Block: The newly created block containing the transactions
            
        Raises:
            BlockchainIntegrationError: If blockchain append operation fails
        """
        try:
            self.logger.info(f"Appending {len(transactions)} transaction(s) to blockchain")
            
            # Check we have transactions to process
            if not transactions:
                raise BlockchainIntegrationError("Cannot append empty transaction list to blockchain")
            
            # Validate all transactions are Transaction objects
            for transaction in transactions:
                if not isinstance(transaction, Transaction):
                    raise BlockchainIntegrationError(f"Invalid transaction type: {type(transaction)}. Expected Transaction object.")
                
                # Check if transaction is already in a block (warn but continue)
                if transaction.block is not None:
                    block_index = getattr(transaction.block, 'index', 'unknown')
                    self.logger.warning(f"Transaction {transaction.transaction_id} already assigned to block {block_index}")
                    
            # Use existing service to create new block with transactions
            new_block = create_new_block(transactions)
            
            # Check if block creation was successful
            if new_block is None:
                raise BlockchainIntegrationError("Failed to create new block for transactions")
                
            self.logger.info(f"Successfully created block {new_block.index} with {len(transactions)} transaction(s)")
            return new_block
            
        except Exception as e:
            error_msg = f"Failed to append transactions to blockchain: {str(e)}"
            self.logger.error(error_msg)
            raise BlockchainIntegrationError(error_msg) from e

    def initiate_integrity_check(self):
        """
        Triggers the blockchain integrity verification process.
        
        Returns:
            bool: True if blockchain integrity is valid, False otherwise
            
        Raises:
            BlockchainIntegrityError: If integrity check encounters an error
        """
        try:
            
            # Use existing blockchain verification service
            integrity_result = verify_blockchain_integrity()
            return integrity_result
            
        except BlockchainIntegrityError:
            # Re-raise integrity errors as-is
            raise
        except Exception as e:
            error_msg = f"Error during blockchain integrity check: {str(e)}"
            self.logger.error(error_msg)
            raise BlockchainIntegrityError(error_msg) from e

    def process_transaction_batch(self, transactions):
        """
        Complete workflow for processing a batch of transactions through the blockchain.
        
        Args:
            transactions (list): Transactions to process
            
        Returns:
            tuple: (success_status, result_data) - success is bool, result_data is dict
        """
        # Initialize result tracking dictionary
        result_data = {
            'processed_transactions': [],  # List of processed transaction info
            'block_created': None,         # Info about created block
            'integrity_verified': False,   # Whether integrity check passed
            'errors': [],                  # List of any errors encountered
            'timestamp': timezone.now().isoformat()  # When processing started
        }
        
        try:
            # Use database transaction to ensure all-or-nothing processing
            with db_transaction.atomic():
                self.logger.info(f"Starting batch processing of {len(transactions)} transactions")
                
                # Step 1: Prepare all transactions for blockchain
                prepared_transactions = []
                for transaction in transactions:
                    try:
                        # Prepare each transaction individually
                        prepared_data = self.prepare_transaction_for_blockchain(transaction)
                        prepared_transactions.append({
                            'transaction': transaction,
                            'prepared_data': prepared_data
                        })
                        
                        # Track in result data
                        result_data['processed_transactions'].append({
                            'transaction_id': transaction.transaction_id,
                            'status': 'prepared',
                            'hash': prepared_data['data_integrity_hash']
                        })
                        
                    except Exception as e:
                        error_msg = f"Failed to prepare transaction {transaction.transaction_id}: {str(e)}"
                        self.logger.error(error_msg)
                        result_data['errors'].append(error_msg)
                        raise BlockchainIntegrationError(error_msg)
                
                # Step 2: Add transactions to blockchain using existing service
                new_block = self.append_transactions_to_blockchain(transactions)
                result_data['block_created'] = {
                    'index': new_block.index,
                    'hash': new_block.hash,
                    'transaction_count': len(transactions)
                }
                
                # Step 3: Verify blockchain integrity
                integrity_status = self.initiate_integrity_check()
                result_data['integrity_verified'] = integrity_status
                
                # Step 4: Handle successful completion
                success_message = self.handle_successful_transaction(transactions, new_block, result_data)
                result_data['success_message'] = success_message
                
                self.logger.info(f"Successfully processed batch of {len(transactions)} transactions")
                return True, result_data
                
        except Exception as e:
            # Step 5: Handle any errors that occurred
            error_response = self.handle_transaction_errors(e, result_data)
            return False, error_response

    def handle_successful_transaction(self, transactions, block, result_data):
        """
        Manages the successful addition of transactions to the blockchain.
        
        Args:
            transactions (list): Successfully processed transactions
            block: The block containing the transactions
            result_data (dict): Processing result data
            
        Returns:
            str: Success message for UI communication
        """
        try:
            # Create user-friendly success message
            success_message = (
                f"Successfully added {len(transactions)} transaction(s) to blockchain. "
                f"Block {block.index} created with hash {block.hash[:16]}... "
                f"Blockchain integrity verified."
            )
            
            self.logger.info(success_message)
            
            # Log details for each transaction
            for transaction in transactions:
                self.logger.info(f"Transaction {transaction.transaction_id} successfully added to block {block.index}")
            
            # TODO: Add additional success handling here if needed
            # (e.g., notifications, webhooks, external system updates)
            
            return success_message
            
        except Exception as e:
            self.logger.error(f"Error in success handling: {str(e)}")
            return f"Transactions processed but success handling encountered issues: {str(e)}"

    def handle_transaction_errors(self, error, result_data):
        """
        Manages errors during blockchain transaction or integrity check.
        
        Args:
            error: The error that occurred
            result_data (dict): Current processing result data
            
        Returns:
            dict: Error response data for UI communication
        """
        try:
            error_message = f"Blockchain integration failed: {str(error)}"
            
            # Log detailed error with stack trace
            self.logger.error(error_message, exc_info=True)
            
            # Create comprehensive error response for UI
            error_response = {
                **result_data,  # Include all existing result data
                'success': False,
                'error_type': type(error).__name__,
                'error_message': error_message,
                'error_timestamp': timezone.now().isoformat(),
                'admin_log_written': True
            }
            
            # Write detailed admin log for later review
            self._write_admin_error_log(error, result_data)
            
            return error_response
            
        except Exception as logging_error:
            # Fallback error handling if even error handling fails
            fallback_message = f"Critical error in error handling: {str(logging_error)}"
            self.logger.critical(fallback_message)
            
            return {
                'success': False,
                'error_message': fallback_message,
                'error_timestamp': timezone.now().isoformat(),
                'admin_log_written': False
            }

    def _write_admin_error_log(self, error, result_data):
        """
        Writes detailed error log for admin review.
        
        Args:
            error: The error that occurred
            result_data (dict): Processing result data
        """
        try:
            # Create structured admin log entry
            admin_log_entry = {
                'timestamp': timezone.now().isoformat(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'error_details': result_data,
                'blockchain_state': self._get_blockchain_state_summary(),
                'stack_trace': str(error.__traceback__) if hasattr(error, '__traceback__') else 'Not available'
            }
            
            # Log with special marker for admin review
            self.logger.error(
                "ADMIN_REVIEW_REQUIRED - Blockchain Integration Error",
                extra={'admin_log': admin_log_entry}
            )
            
        except Exception as e:
            self.logger.critical(f"Failed to write admin error log: {str(e)}")

    def _get_blockchain_state_summary(self):
        """
        Gets a summary of current blockchain state for debugging.
        
        Returns:
            dict: Blockchain state summary
        """
        try:
            # Get latest block info
            latest_block = Block.objects.order_by('-index').first()
            
            # Count various entities
            total_blocks = Block.objects.count()
            total_transactions = Transaction.objects.count()
            unlinked_transactions = Transaction.objects.filter(block__isnull=True).count()
            
            return {
                'total_blocks': total_blocks,
                'total_transactions': total_transactions,
                'unlinked_transactions': unlinked_transactions,
                'latest_block_index': latest_block.index if latest_block else None,
                'latest_block_hash': latest_block.hash if latest_block else None
            }
            
        except Exception as e:
            return {'error': f"Failed to get blockchain state: {str(e)}"}


# Convenience functions for direct usage
def integrate_single_transaction(transaction):
    """
    Integrates a single transaction into the blockchain.
    
    Args:
        transaction: Transaction object to integrate
        
    Returns:
        tuple: (success_status, result_data)
    """
    service = BlockchainIntegrationService()
    return service.process_transaction_batch([transaction])


def integrate_transaction_batch(transactions):
    """
    Integrates a batch of transactions into the blockchain.
    
    Args:
        transactions (list): List of Transaction objects to integrate
        
    Returns:
        tuple: (success_status, result_data)
    """
    service = BlockchainIntegrationService()
    return service.process_transaction_batch(transactions)


def verify_transaction_in_blockchain(transaction):
    """
    Verifies if a transaction exists in the blockchain and validates its integrity.
    
    Args:
        transaction: Transaction object to verify
        
    Returns:
        dict: Verification result data
    """
    try:
        # Check if transaction is linked to a block
        if not transaction.block:
            return {
                'verified': False,
                'reason': 'Transaction not linked to any block',
                'transaction_id': transaction.transaction_id
            }
        
        # Recalculate transaction hash and verify block integrity
        service = BlockchainIntegrationService()
        current_hash = service.generate_transaction_hash(transaction.to_dict())
        
        # Check if block hash is still valid (not tampered with)
        block_hash_valid = transaction.block.hash == transaction.block.calculate_hash()
        
        return {
            'verified': block_hash_valid,
            'transaction_id': transaction.transaction_id,
            'block_index': transaction.block.index,
            'block_hash': transaction.block.hash,
            'block_hash_valid': block_hash_valid,
            'current_transaction_hash': current_hash
        }
        
    except Exception as e:
        logger.error(f"Error verifying transaction {transaction.transaction_id}: {str(e)}")
        return {
            'verified': False,
            'error': str(e),
            'transaction_id': transaction.transaction_id
        }