"""
Management command to generate transaction hashes for existing transactions.

Usage:
    python manage.py generate_transaction_hashes
"""

from django.core.management.base import BaseCommand
from apps.core.models import Transaction
from apps.blockchain.integrity_service import integrity_service


class Command(BaseCommand):
    help = 'Generate transaction hashes for existing transactions that don\'t have them'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        # Get transactions without hashes
        unhashed_transactions = Transaction.objects.filter(transaction_hash__isnull=True)
        total_unhashed = unhashed_transactions.count()
        
        if total_unhashed == 0:
            self.stdout.write(
                self.style.SUCCESS('All transactions already have hashes!')
            )
            return
        
        self.stdout.write(f"Found {total_unhashed} transactions without hashes.")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
            return
        
        # Generate hashes using the integrity service
        results = integrity_service.generate_transaction_hashes()
        
        # Display results
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated hashes for {results['hashes_generated']} transactions"
            )
        )
        
        if results['errors']:
            self.stdout.write(
                self.style.ERROR(f"Encountered {len(results['errors'])} errors:")
            )
            for error in results['errors']:
                self.stdout.write(
                    f"  - Transaction {error['transaction_id']}: {error['error']}"
                )
        
        if verbose:
            self.stdout.write(f"Total processed: {results['total_processed']}")
            self.stdout.write(f"Hashes generated: {results['hashes_generated']}")
            self.stdout.write(f"Errors: {len(results['errors'])}")
        
        # Verify integrity after generation
        self.stdout.write("\nVerifying transaction integrity...")
        integrity_results = integrity_service.verify_transaction_level_integrity()
        
        self.stdout.write(
            f"Integrity check results:"
            f"\n  - Valid transactions: {len(integrity_results['valid_transactions'])}"
            f"\n  - Compromised transactions: {len(integrity_results['compromised_transactions'])}"
            f"\n  - Unhashed transactions: {len(integrity_results['unhashed_transactions'])}"
        )
        
        if integrity_results['compromised_transactions']:
            self.stdout.write(
                self.style.ERROR(
                    f"⚠️  WARNING: {len(integrity_results['compromised_transactions'])} "
                    "transactions appear to be compromised!"
                )
            )
            if verbose:
                for tx in integrity_results['compromised_transactions']:
                    self.stdout.write(
                        f"  - {tx['transaction_id']}: {tx['item_name']}"
                    ) 