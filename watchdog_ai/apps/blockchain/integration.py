"""
Blockchain Integration Module

Purpose: Processes transaction data and adds it to the simulated blockchain to ensure data integrity.

Key Processes:
- Atomic Blockchain Integration: Ensures all-or-nothing blockchain operations
- Status Tracking: Tracks integration status for each transaction
- Retry Mechanism: Allows retrying failed integrations
- Error Reporting: Sends error reports to admin email
"""

import hashlib
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.db import transaction as db_transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

from .models import Block
from .services import create_new_block, verify_blockchain_integrity, create_genesis_block
from .integrity_service import integrity_service
from apps.core.models import Transaction

# Setup logging for this module
logger = logging.getLogger(__name__)


class BlockchainIntegrationError(Exception):
    """Custom exception for blockchain integration errors"""
    pass


class BlockchainIntegrationService:
    """
    Simple atomic blockchain integration service.
    Handles the complete lifecycle of adding transactions to the blockchain.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def integrate_transactions_atomic(self, transactions):
        """
        Atomically integrates transactions into the blockchain.
        If any step fails, all changes are rolled back.
        
        Args:
            transactions (list): List of Transaction objects to integrate
            
        Returns:
            dict: Result with success status and details
        """

        # Initialize result dictionary with default values
        # Keep note of this dictionary structure
        result = {
            'success': False,
            'integrated_count': 0,
            'failed_count': 0,
            'error_message': None,
            'block_info': None,
            'integrity_checks': {
                'before': None,
                'after': None
            }
        }
        
        # Step 0: Check integrity BEFORE integration
        before_check = integrity_service.check_integrity_before_integration(transactions)
        result['integrity_checks']['before'] = before_check
        
        if not before_check['integrity_valid']:
            error_msg = "Blockchain integrity compromised before integration"
            self.logger.error(error_msg)
            result.update({
                'success': False,
                'failed_count': len(transactions),
                'error_message': error_msg
            })
            return result
        
        try:
            with db_transaction.atomic():
                # Step 1: Update transaction status to 'pending'
                for transaction in transactions:
                    transaction.blockchain_status = 'pending'
                    transaction.last_blockchain_attempt = timezone.now()
                    transaction.save(update_fields=['blockchain_status', 'last_blockchain_attempt'])
                
                # Step 2: Create new block with transactions
                new_block = create_new_block(transactions)
                if not new_block:
                    raise BlockchainIntegrationError("Failed to create new block")
                
                # Step 3: Update transaction status to 'integrated'
                for transaction in transactions:
                    transaction.blockchain_status = 'integrated'
                    transaction.blockchain_error = None
                    transaction.save(update_fields=['blockchain_status', 'blockchain_error'])
                
                result.update({
                    'success': True,
                    'integrated_count': len(transactions),
                    'block_info': {
                        'index': new_block.index,
                        'hash': new_block.hash,
                        'transaction_count': len(transactions)
                    }
                })
                
                self.logger.info(f"Successfully integrated {len(transactions)} transactions into block {new_block.index}")
                
        except Exception as e:
            error_msg = f"Blockchain integration failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # Update transaction status to 'failed'
            for transaction in transactions:
                transaction.blockchain_status = 'failed'
                transaction.blockchain_error = error_msg
                transaction.blockchain_retry_count += 1
                transaction.save(update_fields=['blockchain_status', 'blockchain_error', 'blockchain_retry_count'])
            
            result.update({
                'success': False,
                'failed_count': len(transactions),
                'error_message': error_msg
            })
            
            # Send error report to admin
            self._send_error_report(transactions, error_msg)
            
            return result
        
        # Step 4: Check integrity AFTER integration
        after_check = integrity_service.check_integrity_after_integration(transactions, result['success'])
        result['integrity_checks']['after'] = after_check
        
        return result

    def retry_failed_integrations(self, max_retries=3):
        """
        Retries blockchain integration for transactions that previously failed.
        
        Args:
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            dict: Result with retry statistics
        """
        # Get transactions that failed and haven't exceeded max retries
        failed_transactions = Transaction.objects.filter(
            blockchain_status='failed',
            blockchain_retry_count__lt=max_retries
        ).select_related('block')
        
        if not failed_transactions.exists():
            return {
                'success': True,
                'message': 'No failed transactions to retry',
                'retried_count': 0
            }
        
        # Group transactions by block (if they were part of the same batch)
        # For simplicity, we'll retry them individually or in small batches
        result = self.integrate_transactions_atomic(list(failed_transactions))
        
        return {
            'success': result['success'],
            'retried_count': result['integrated_count'] + result['failed_count'],
            'integrated_count': result['integrated_count'],
            'failed_count': result['failed_count'],
            'error_message': result.get('error_message')
        }

    def _send_error_report(self, transactions, error_msg):
        """
        Sends error report to admin email.
        
        Args:
            transactions (list): Transactions that failed
            error_msg (str): Error message
        """
        try:
            # Create email content
            subject = "Blockchain Integration Error Report"
            
            body = f"""
            Blockchain integration failed for {len(transactions)} transaction(s).
            
            Error: {error_msg}
            
            Failed Transactions:
            """
            
            for transaction in transactions:
                body += f"- {transaction.transaction_id}: {transaction.item_name}\n"
            
            body += f"""
            Timestamp: {timezone.now()}
            
            Please review the blockchain integration logs for more details.
            """
            
            # Send email (you'll need to configure email settings in Django)
            self._send_email(
                to_email="watchdogai.help@gmail.com",
                subject=subject,
                body=body
            )
            
            self.logger.info("Error report sent to admin email")
            
        except Exception as e:
            self.logger.error(f"Failed to send error report: {str(e)}")

    def _send_email(self, to_email, subject, body):
        """
        Sends email using Django's email backend.
        Requires proper email configuration in settings.py
        """
        try:
            from django.core.mail import send_mail
            
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
        except Exception as e:
            self.logger.error(f"Email sending failed: {str(e)}")


### Convenience functions for direct usage
def integrate_transaction_batch(transactions):
    """
    Integrates a batch of transactions into the blockchain atomically.
    
    Args:
        transactions (list): List of Transaction objects to integrate
        
    Returns:
        tuple: (success_status, result_data)
    """
    service = BlockchainIntegrationService()
    result = service.integrate_transactions_atomic(transactions)
    return result['success'], result


def retry_failed_blockchain_integrations():
    """
    Retries all failed blockchain integrations.
    
    Returns:
        dict: Retry result data
    """
    service = BlockchainIntegrationService()
    return service.retry_failed_integrations()


def get_blockchain_status_summary():
    """
    Gets a summary of blockchain integration status.
    
    Returns:
        dict: Status summary
    """
    try:
        total_transactions = Transaction.objects.count()
        pending_count = Transaction.objects.filter(blockchain_status='pending').count()
        integrated_count = Transaction.objects.filter(blockchain_status='integrated').count()
        failed_count = Transaction.objects.filter(blockchain_status='failed').count()
        
        return {
            'total_transactions': total_transactions,
            'pending_integration': pending_count,
            'successfully_integrated': integrated_count,
            'failed_integration': failed_count,
            'integration_rate': (integrated_count / total_transactions * 100) if total_transactions > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting blockchain status summary: {str(e)}")
        return {'error': str(e)}