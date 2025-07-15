"""
Management command to check transaction integrity and identify tampered transactions.

Usage:
    python manage.py check_transaction_integrity
"""

from django.core.management.base import BaseCommand
from apps.blockchain.integrity_service import integrity_service


class Command(BaseCommand):
    help = 'Check transaction integrity and identify tampered transactions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed information about each transaction',
        )
        parser.add_argument(
            '--send-alerts',
            action='store_true',
            help='Send email alerts if tampered transactions are found',
        )
    
    def handle(self, *args, **options):
        detailed = options['detailed']
        send_alerts = options['send_alerts']
        
        self.stdout.write("🔍 Checking transaction integrity...")
        
        # Perform transaction-level integrity check
        integrity_results = integrity_service.verify_transaction_level_integrity()
        
        # Display summary
        self.stdout.write(
            f"\n📊 Integrity Check Summary:"
            f"\n  - Total transactions checked: {integrity_results['total_checked']}"
            f"\n  - Valid transactions: {len(integrity_results['valid_transactions'])}"
            f"\n  - Compromised transactions: {len(integrity_results['compromised_transactions'])}"
            f"\n  - Unhashed transactions: {len(integrity_results['unhashed_transactions'])}"
        )
        
        # Show detailed results if requested
        if detailed:
            if integrity_results['valid_transactions']:
                self.stdout.write(f"\n✅ Valid Transactions ({len(integrity_results['valid_transactions'])}):")
                for tx in integrity_results['valid_transactions']:
                    self.stdout.write(f"  - {tx['transaction_id']}: {tx['item_name']}")
            
            if integrity_results['compromised_transactions']:
                self.stdout.write(f"\n❌ Compromised Transactions ({len(integrity_results['compromised_transactions'])}):")
                for tx in integrity_results['compromised_transactions']:
                    self.stdout.write(
                        f"  - {tx['transaction_id']}: {tx['item_name']}"
                        f"\n    Block: {tx['block_index']}"
                        f"\n    Stored Hash: {tx['stored_hash'][:16]}..."
                        f"\n    Current Hash: {tx['current_hash'][:16]}..."
                    )
            
            if integrity_results['unhashed_transactions']:
                self.stdout.write(f"\n⚠️  Unhashed Transactions ({len(integrity_results['unhashed_transactions'])}):")
                for tx in integrity_results['unhashed_transactions']:
                    self.stdout.write(f"  - {tx['transaction_id']}: {tx['item_name']} ({tx['reason']})")
        
        # Handle compromised transactions
        if integrity_results['compromised_transactions']:
            self.stdout.write(
                self.style.ERROR(
                    f"\n🚨 CRITICAL: {len(integrity_results['compromised_transactions'])} "
                    "transactions have been tampered with!"
                )
            )
            
            if send_alerts:
                self.stdout.write("📧 Sending email alerts...")
                tampered_transactions = integrity_service.identify_tampered_transactions()
                self.stdout.write(
                    self.style.SUCCESS(f"Email alerts sent for {len(tampered_transactions)} tampered transactions")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Use --send-alerts to send email notifications about tampered transactions"
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n✅ No compromised transactions found!")
            )
        
        # Handle unhashed transactions
        if integrity_results['unhashed_transactions']:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  {len(integrity_results['unhashed_transactions'])} "
                    "transactions don't have hashes. Run 'generate_transaction_hashes' to create them."
                )
            )
        
        # Overall status
        if integrity_results['compromised_transactions']:
            self.stdout.write(
                self.style.ERROR("\n🔴 INTEGRITY COMPROMISED - Immediate action required!")
            )
        elif integrity_results['unhashed_transactions']:
            self.stdout.write(
                self.style.WARNING("\n🟡 PARTIAL INTEGRITY - Some transactions need hashes.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n🟢 ALL TRANSACTIONS INTEGRITY VERIFIED!")
            ) 