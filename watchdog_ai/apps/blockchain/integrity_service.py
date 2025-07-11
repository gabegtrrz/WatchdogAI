"""
Blockchain Integrity Service

Purpose: Monitors blockchain integrity before and after transaction integration.
Sends email alerts if blockchain is compromised.

Design: Decoupled service following SOLID principles with clear separation of concerns.
"""

import logging
from typing import Dict, Any, Optional
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


# Global instance for easy access
integrity_service = BlockchainIntegrityService()