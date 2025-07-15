"""
Blockchain Integrity Service

Purpose: Monitors blockchain integrity before and after transaction integration.
Sends email alerts if blockchain is compromised.

Design: Decoupled service following SOLID principles with clear separation of concerns.
"""

import logging
from typing import Dict, Any, Optional, List
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .services import verify_blockchain_integrity
from .models import IntegrityCheck
from apps.core.models import Transaction

logger = logging.getLogger(__name__)


class BlockchainIntegrityService:
    """
    Service for monitoring blockchain integrity and alerting on compromise.
    
    Responsibilities:
    - Check blockchain integrity before/after operations
    - Check transaction-level integrity for specific tamper detection
    - Send email alerts when integrity is compromised
    - Log integrity check results
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def check_integrity_before_integration(self, transactions: list) -> Dict[str, Any]:
        """
        Check blockchain integrity before integrating new transactions.
        
        Args:
            transactions: List of transactions to be integrated
            
        Returns:
            Dict with integrity status and details
        """
        self.logger.info(f"Checking blockchain integrity before integrating {len(transactions)} transactions")
        
        integrity_valid = verify_blockchain_integrity()
        transaction_ids = [getattr(tx, 'transaction_id', str(tx)) for tx in transactions]
        
        # Create integrity check record
        integrity_check = IntegrityCheck.objects.create(
            check_type='BEFORE',
            integrity_valid=integrity_valid,
            transaction_count=len(transactions),
            transaction_ids=', '.join(transaction_ids),
            alert_sent=False
        )
        
        result = {
            'integrity_valid': integrity_valid,
            'check_timestamp': integrity_check.timestamp,
            'transaction_count': len(transactions),
            'alert_sent': False,
            'check_id': integrity_check.id
        }
        
        if not integrity_valid:
            self.logger.error("Blockchain integrity compromised before integration")
            error_message = "Blockchain integrity check failed before transaction integration"
            self._send_integrity_alert("BEFORE", transactions, error_message)
            
            # Update record with alert status and error
            integrity_check.alert_sent = True
            integrity_check.error_message = error_message
            integrity_check.save()
            
            result['alert_sent'] = True
        
        return result
    
    def check_integrity_after_integration(self, transactions: list, integration_success: bool) -> Dict[str, Any]:
        """
        Check blockchain integrity after integrating transactions.
        
        Args:
            transactions: List of transactions that were integrated
            integration_success: Whether the integration was successful
            
        Returns:
            Dict with integrity status and details
        """
        self.logger.info(f"Checking blockchain integrity after integrating {len(transactions)} transactions")
        
        integrity_valid = verify_blockchain_integrity()
        transaction_ids = [getattr(tx, 'transaction_id', str(tx)) for tx in transactions]
        
        # Create integrity check record
        integrity_check = IntegrityCheck.objects.create(
            check_type='AFTER',
            integrity_valid=integrity_valid,
            transaction_count=len(transactions),
            transaction_ids=', '.join(transaction_ids),
            integration_success=integration_success,
            alert_sent=False
        )
        
        result = {
            'integrity_valid': integrity_valid,
            'check_timestamp': integrity_check.timestamp,
            'transaction_count': len(transactions),
            'integration_success': integration_success,
            'alert_sent': False,
            'check_id': integrity_check.id
        }
        
        if not integrity_valid:
            self.logger.error("Blockchain integrity compromised after integration")
            error_message = "Blockchain integrity check failed after transaction integration"
            self._send_integrity_alert("AFTER", transactions, error_message)
            
            # Update record with alert status and error
            integrity_check.alert_sent = True
            integrity_check.error_message = error_message
            integrity_check.save()
            
            result['alert_sent'] = True
        
        return result

    def verify_transaction_level_integrity(self, transactions: Optional[List[Transaction]] = None) -> Dict[str, Any]:
        """
        Verify integrity at the transaction level.
        
        Args:
            transactions: List of transactions to check, or None for all
            
        Returns:
            Dict with detailed integrity results
        """
        if transactions is None:
            transactions = Transaction.objects.all()
        
        results = {
            'total_checked': len(transactions),
            'valid_transactions': [],
            'compromised_transactions': [],
            'unhashed_transactions': []
        }
        
        for transaction in transactions:
            if not transaction.transaction_hash:
                results['unhashed_transactions'].append({
                    'transaction_id': transaction.transaction_id,
                    'item_name': transaction.item_name,
                    'reason': 'No hash stored'
                })
            elif not transaction.verify_transaction_integrity():
                results['compromised_transactions'].append({
                    'transaction_id': transaction.transaction_id,
                    'item_name': transaction.item_name,
                    'stored_hash': transaction.transaction_hash,
                    'current_hash': transaction.calculate_transaction_hash(),
                    'block_index': transaction.block.index if transaction.block else None
                })
            else:
                results['valid_transactions'].append({
                    'transaction_id': transaction.transaction_id,
                    'item_name': transaction.item_name
                })
        
        return results

    def identify_tampered_transactions(self) -> List[Dict[str, Any]]:
        """
        Identify specifically which transactions have been tampered with.
        
        Returns:
            List of tampered transaction details
        """
        integrity_results = self.verify_transaction_level_integrity()
        
        if integrity_results['compromised_transactions']:
            self._send_detailed_tamper_alert(integrity_results['compromised_transactions'])
        
        return integrity_results['compromised_transactions']

    def generate_transaction_hashes(self, transactions: Optional[List[Transaction]] = None) -> Dict[str, Any]:
        """
        Generate transaction hashes for transactions that don't have them.
        
        Args:
            transactions: List of transactions to process, or None for all unhashed transactions
            
        Returns:
            Dict with generation results
        """
        if transactions is None:
            transactions = Transaction.objects.filter(transaction_hash__isnull=True)
        
        results = {
            'total_processed': len(transactions),
            'hashes_generated': 0,
            'errors': []
        }
        
        for transaction in transactions:
            try:
                transaction.transaction_hash = transaction.calculate_transaction_hash()
                transaction.save(update_fields=['transaction_hash'])
                results['hashes_generated'] += 1
            except Exception as e:
                results['errors'].append({
                    'transaction_id': transaction.transaction_id,
                    'error': str(e)
                })
        
        return results
    
    def _send_integrity_alert(self, check_type: str, transactions: list, error_message: str):
        """
        Send email alert when blockchain integrity is compromised.
        
        Args:
            check_type: "BEFORE" or "AFTER" integration
            transactions: List of transactions involved
            error_message: Description of the integrity issue
        """
        try:
            subject = f"🚨 BLOCKCHAIN INTEGRITY COMPROMISED - {check_type} Integration"
            
            # email body with transaction details
            body = f"""
            CRITICAL: Blockchain integrity has been compromised!
            
            Check Type: {check_type} transaction integration
            Timestamp: {timezone.now()}
            Error: {error_message}
            
            Transactions involved:
            """
            
            for tx in transactions:
                body += f"- {tx.transaction_id}: {tx.item_name} (${tx.unit_purchase_price})\n"
            
            body += f"""
            
            IMMEDIATE ACTION REQUIRED:
            1. Review blockchain logs
            2. Check for unauthorized modifications
            3. Consider blockchain rollback if necessary
            
            This is an automated alert from WatchdogAI.
            """
            
            # Send email
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False
            )
            
            self.logger.info(f"Integrity alert sent for {check_type} check")
            
        except Exception as e:
            self.logger.error(f"Failed to send integrity alert: {str(e)}")

    def _send_detailed_tamper_alert(self, compromised_transactions: List[Dict[str, Any]]):
        """
        Send detailed alert about specific tampered transactions.
        
        Args:
            compromised_transactions: List of compromised transaction details
        """
        try:
            subject = "🚨 SPECIFIC TRANSACTIONS TAMPERED WITH"
            
            body = f"""
            CRITICAL: {len(compromised_transactions)} specific transactions have been tampered with!
            
            Tampered Transactions:
            """
            
            for tx in compromised_transactions:
                body += f"""
            - Transaction ID: {tx['transaction_id']}
              Item: {tx['item_name']}
              Block: {tx['block_index']}
              Stored Hash: {tx['stored_hash'][:16]}...
              Current Hash: {tx['current_hash'][:16]}...
            """
            
            body += f"""
            
            IMMEDIATE ACTION REQUIRED:
            1. Investigate these specific transactions
            2. Check for unauthorized database access
            3. Consider rolling back affected blocks
            4. Review audit logs for suspicious activity
            
            Timestamp: {timezone.now()}
            """
            
            # Send email alert
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False
            )
            
            self.logger.info(f"Detailed tamper alert sent for {len(compromised_transactions)} transactions")
            
        except Exception as e:
            self.logger.error(f"Failed to send detailed tamper alert: {str(e)}")


# Global instance for easy access
integrity_service = BlockchainIntegrityService()