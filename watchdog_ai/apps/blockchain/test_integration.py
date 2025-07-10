"""
Simple test script to verify blockchain integration module functionality.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchdog_ai.settings')
django.setup()

from apps.core.models import Transaction, ProcurementMethod
from apps.blockchain.integration import BlockchainIntegrationService, integrate_single_transaction
from apps.blockchain.services import verify_blockchain_integrity

def test_blockchain_integration():
    """Test the blockchain integration functionality"""
    
    print("🧪 Testing Blockchain Integration Module")
    print("=" * 50)
    
    # Create a test procurement method if it doesn't exist
    procurement_method, created = ProcurementMethod.objects.get_or_create(
        name="Test Procurement Method"
    )
    
    # Create a test transaction
    test_transaction = Transaction.objects.create(
        transaction_id="TEST_TX_001",
        project_name="Test Project",
        item_name="Test Item",
        quantity=10,
        unit_purchase_price=100.00,
        supplier="Test Supplier",
        invoice_number="INV-001",
        payment_receipt_number="REC-001",
        transaction_date="2025-01-15",
        procurement_method=procurement_method
    )
    
    print(f"✅ Created test transaction: {test_transaction.transaction_id}")
    
    # Test the integration service
    service = BlockchainIntegrationService()
    
    # Test 1: Prepare transaction for blockchain
    print("\n📋 Test 1: Preparing transaction for blockchain")
    try:
        prepared_data = service.prepare_transaction_for_blockchain(test_transaction)
        print(f"✅ Transaction prepared successfully")
        print(f"   - Hash: {prepared_data['data_integrity_hash'][:16]}...")
        print(f"   - Timestamp: {prepared_data['blockchain_timestamp']}")
    except Exception as e:
        print(f"❌ Failed to prepare transaction: {e}")
        return
    
    # Test 2: Integrate single transaction
    print("\n🔗 Test 2: Integrating transaction to blockchain")
    try:
        success, result_data = integrate_single_transaction(test_transaction)
        
        if success:
            print("✅ Transaction integrated successfully")
            print(f"   - Block created: {result_data['block_created']['index']}")
            print(f"   - Block hash: {result_data['block_created']['hash'][:16]}...")
            print(f"   - Integrity verified: {result_data['integrity_verified']}")
        else:
            print(f"❌ Integration failed: {result_data.get('error_message', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Integration error: {e}")
    
    # Test 3: Verify blockchain integrity
    print("\n🔍 Test 3: Verifying blockchain integrity")
    try:
        integrity_result = verify_blockchain_integrity()
        if integrity_result:
            print("✅ Blockchain integrity verified successfully")
        else:
            print("❌ Blockchain integrity check failed")
    except Exception as e:
        print(f"❌ Integrity check error: {e}")
    
    # Test 4: Verify specific transaction
    print("\n🔍 Test 4: Verifying specific transaction")
    try:
        verification_result = service.verify_transaction_in_blockchain(test_transaction)
        if verification_result.get('verified'):
            print("✅ Transaction verification successful")
            print(f"   - Block index: {verification_result['block_index']}")
            print(f"   - Block hash valid: {verification_result['block_hash_valid']}")
        else:
            print(f"❌ Transaction verification failed: {verification_result.get('reason', 'Unknown')}")
    except Exception as e:
        print(f"❌ Verification error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Blockchain Integration Test Complete")
    
    # Clean up test data
    try:
        test_transaction.delete()
        print("🧹 Test data cleaned up")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

if __name__ == "__main__":
    test_blockchain_integration() 