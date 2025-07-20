"""
Test script for blockchain integrity service.

This demonstrates how the integrity service works with the blockchain integration.
"""

from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from .integrity_service import BlockchainIntegrityService
from .services import verify_blockchain_integrity
from apps.core.models import Transaction


class BlockchainIntegrityServiceTest(TestCase):
    """Test cases for blockchain integrity service."""
    
    def setUp(self):
        """Set up test data."""
        self.integrity_service = BlockchainIntegrityService()
        
        # Create mock transactions for testing
        self.mock_transactions = [
            # fake transaction objects that look and behave like real Transaction objects
            MagicMock(
                transaction_id="TX001",
                item_name="Test Item 1",
                unit_purchase_price=100.00
            ),
            MagicMock(
                transaction_id="TX002", 
                item_name="Test Item 2",
                unit_purchase_price=200.00
            )
        ]
    
    # @patch replaces real functions with fake ones during testing.
    @patch('apps.blockchain.integrity_service.verify_blockchain_integrity') # tests code without needing a real blockchain

    @patch('apps.blockchain.integrity_service.send_mail')
    
    def test_integrity_check_before_integration_success(self, mock_send_mail, mock_verify):
        """Test integrity check before integration when blockchain is valid."""
        # Mock blockchain integrity as valid
        mock_verify.return_value = True
        
        result = self.integrity_service.check_integrity_before_integration(self.mock_transactions)
        
        # Verify results
        self.assertTrue(result['integrity_valid'])
        self.assertEqual(result['transaction_count'], 2)
        self.assertFalse(result['alert_sent'])
        
        # Verify no email was sent
        mock_send_mail.assert_not_called()
    
    @patch('apps.blockchain.integrity_service.verify_blockchain_integrity')
    @patch('apps.blockchain.integrity_service.send_mail')
    def test_integrity_check_before_integration_failure(self, mock_send_mail, mock_verify):
        """Test integrity check before integration when blockchain is compromised."""
        # Mock blockchain integrity as invalid
        mock_verify.return_value = False
        
        result = self.integrity_service.check_integrity_before_integration(self.mock_transactions)
        
        # Verify results
        self.assertFalse(result['integrity_valid'])
        self.assertEqual(result['transaction_count'], 2)
        self.assertTrue(result['alert_sent'])
        
        # Verify email was sent
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('BLOCKCHAIN INTEGRITY COMPROMISED', call_args[1]['subject'])
        self.assertIn('BEFORE', call_args[1]['subject'])
    
    @patch('apps.blockchain.integrity_service.verify_blockchain_integrity')
    @patch('apps.blockchain.integrity_service.send_mail')
    def test_integrity_check_after_integration_success(self, mock_send_mail, mock_verify):
        """Test integrity check after integration when blockchain is valid."""
        # Mock blockchain integrity as valid
        mock_verify.return_value = True
        
        result = self.integrity_service.check_integrity_after_integration(
            self.mock_transactions, 
            integration_success=True
        )
        
        # Verify results
        self.assertTrue(result['integrity_valid'])
        self.assertEqual(result['transaction_count'], 2)
        self.assertTrue(result['integration_success'])
        self.assertFalse(result['alert_sent'])
        
        # Verify no email was sent
        mock_send_mail.assert_not_called()
    
    @patch('apps.blockchain.integrity_service.verify_blockchain_integrity')
    @patch('apps.blockchain.integrity_service.send_mail')
    def test_integrity_check_after_integration_failure(self, mock_send_mail, mock_verify):
        """Test integrity check after integration when blockchain is compromised."""
        # Mock blockchain integrity as invalid
        mock_verify.return_value = False
        
        result = self.integrity_service.check_integrity_after_integration(
            self.mock_transactions, 
            integration_success=True
        )
        
        # Verify results
        self.assertFalse(result['integrity_valid'])
        self.assertEqual(result['transaction_count'], 2)
        self.assertTrue(result['integration_success'])
        self.assertTrue(result['alert_sent'])
        
        # Verify email was sent
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('BLOCKCHAIN INTEGRITY COMPROMISED', call_args[1]['subject'])
        self.assertIn('AFTER', call_args[1]['subject'])


def demonstrate_integrity_service():
    """
    Demonstration function showing how the integrity service works.
    
    This function shows the typical usage pattern:
    1. Check integrity before integration
    2. Perform integration
    3. Check integrity after integration
    """
    print("=== Blockchain Integrity Service Demonstration ===")
    
    # Create service instance
    integrity_service = BlockchainIntegrityService()
    
    # Mock transactions
    mock_transactions = [
        MagicMock(transaction_id="TX001", item_name="Laptop", unit_purchase_price=1000.00),
        MagicMock(transaction_id="TX002", item_name="Printer", unit_purchase_price=500.00)
    ]
    
    print("1. Checking integrity BEFORE integration...")
    before_result = integrity_service.check_integrity_before_integration(mock_transactions)
    print(f"   Integrity valid: {before_result['integrity_valid']}")
    print(f"   Alert sent: {before_result['alert_sent']}")
    
    if not before_result['integrity_valid']:
        print("   ❌ Integration blocked due to integrity issues!")
        return
    
    print("2. Performing blockchain integration...")
    # Simulate successful integration
    integration_success = True
    
    print("3. Checking integrity AFTER integration...")
    after_result = integrity_service.check_integrity_after_integration(
        mock_transactions, 
        integration_success
    )
    print(f"   Integrity valid: {after_result['integrity_valid']}")
    print(f"   Alert sent: {after_result['alert_sent']}")
    
    if after_result['alert_sent']:
        print("   ⚠️ Integrity alert sent after integration!")
    else:
        print("   ✅ All integrity checks passed!")
    
    print("=== Demonstration Complete ===")


if __name__ == "__main__":
    # Run demonstration
    demonstrate_integrity_service() 