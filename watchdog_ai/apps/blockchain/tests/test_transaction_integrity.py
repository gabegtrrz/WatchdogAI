"""
Test script to demonstrate transaction-level tamper detection.

This script shows how to:
1. Generate transaction hashes for existing transactions
2. Check transaction integrity
3. Simulate tampering and detect it
4. Identify specific tampered transactions
"""

import os
import sys
import django
from django.db import transaction as transaction_db

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchdog_ai.settings')
django.setup()

from apps.core.models import Transaction
from apps.blockchain.integrity_service import integrity_service
from apps.blockchain.integration import generate_transaction_hashes, identify_tampered_transactions


def demonstrate_transaction_integrity():
    """Demonstrate transaction-level integrity checking."""
    
    print("🔍 Transaction Integrity Demonstration")
    print("=" * 50)
    
    # Step 1: Generate hashes for existing transactions
    print("\n1. Generating transaction hashes...")
    hash_results = generate_transaction_hashes()
    print(f"   - Total processed: {hash_results['total_processed']}")
    print(f"   - Hashes generated: {hash_results['hashes_generated']}")
    print(f"   - Errors: {len(hash_results['errors'])}")
    
    if hash_results['errors']:
        print("   - Error details:")
        for error in hash_results['errors']:
            print(f"     * {error['transaction_id']}: {error['error']}")
    
    # Step 2: Check initial integrity
    print("\n2. Checking initial transaction integrity...")
    integrity_results = integrity_service.verify_transaction_level_integrity()
    print(f"   - Total checked: {integrity_results['total_checked']}")
    print(f"   - Valid: {len(integrity_results['valid_transactions'])}")
    print(f"   - Compromised: {len(integrity_results['compromised_transactions'])}")
    print(f"   - Unhashed: {len(integrity_results['unhashed_transactions'])}")
    
    # Step 3: Simulate tampering (if we have transactions)
    if integrity_results['valid_transactions']:
        print("\n3. Simulating transaction tampering...")
        
        # Get a valid transaction to tamper with
        valid_tx_id = integrity_results['valid_transactions'][0]['transaction_id']
        transaction = Transaction.objects.get(transaction_id=valid_tx_id)
        
        print(f"   - Selected transaction: {transaction.transaction_id}")
        print(f"   - Original item name: {transaction.item_name}")
        print(f"   - Original unit price: {transaction.unit_purchase_price}")
        
        # Simulate tampering by changing the item name
        original_item_name = transaction.item_name
        transaction.item_name = f"TAMPERED_{original_item_name}"
        
        with transaction_db.atomic():
            transaction.save(update_fields=['item_name'])
        
        print(f"   - Tampered item name: {transaction.item_name}")
        
        # Step 4: Check integrity after tampering
        print("\n4. Checking integrity after tampering...")
        tampered_transactions = identify_tampered_transactions()
        
        if tampered_transactions:
            print(f"   - Found {len(tampered_transactions)} tampered transactions:")
            for tx in tampered_transactions:
                print(f"     * {tx['transaction_id']}: {tx['item_name']}")
                print(f"       Block: {tx['block_index']}")
                print(f"       Stored Hash: {tx['stored_hash'][:16]}...")
                print(f"       Current Hash: {tx['current_hash'][:16]}...")
        else:
            print("   - No tampered transactions detected (unexpected)")
        
        # Step 5: Restore the original data
        print("\n5. Restoring original transaction data...")
        transaction.item_name = original_item_name
        
        with transaction_db.atomic():
            transaction.save(update_fields=['item_name'])
        
        print(f"   - Restored item name: {transaction.item_name}")
        
        # Step 6: Verify integrity is restored
        print("\n6. Verifying integrity after restoration...")
        final_integrity = integrity_service.verify_transaction_level_integrity()
        print(f"   - Valid: {len(final_integrity['valid_transactions'])}")
        print(f"   - Compromised: {len(final_integrity['compromised_transactions'])}")
        
        if not final_integrity['compromised_transactions']:
            print("   ✅ Integrity restored successfully!")
        else:
            print("   ❌ Integrity still compromised!")
    
    else:
        print("\n3. No valid transactions found to demonstrate tampering.")
        print("   Please create some transactions first.")
    
    print("\n" + "=" * 50)
    print("🎯 Transaction Integrity Demonstration Complete!")


def show_integrity_summary():
    """Show a summary of current transaction integrity status."""
    
    print("\n📊 Current Transaction Integrity Summary")
    print("-" * 40)
    
    total_transactions = Transaction.objects.count()
    unhashed_transactions = Transaction.objects.filter(transaction_hash__isnull=True).count()
    
    print(f"Total transactions: {total_transactions}")
    print(f"Transactions with hashes: {total_transactions - unhashed_transactions}")
    print(f"Transactions without hashes: {unhashed_transactions}")
    
    if total_transactions > 0:
        integrity_results = integrity_service.verify_transaction_level_integrity()
        print(f"Valid transactions: {len(integrity_results['valid_transactions'])}")
        print(f"Compromised transactions: {len(integrity_results['compromised_transactions'])}")
        
        if integrity_results['compromised_transactions']:
            print("\n🚨 COMPROMISED TRANSACTIONS:")
            for tx in integrity_results['compromised_transactions']:
                print(f"  - {tx['transaction_id']}: {tx['item_name']}")
    
    print("-" * 40)


if __name__ == "__main__":
    print("🚀 Starting Transaction Integrity Test")
    
    # Show current status
    show_integrity_summary()
    
    # Run demonstration
    demonstrate_transaction_integrity()
    
    # Show final status
    show_integrity_summary()
    
    print("\n✨ Test completed!") 