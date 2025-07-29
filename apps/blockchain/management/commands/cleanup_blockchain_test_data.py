"""
Management command to clean up blockchain test data.

This command removes test transactions and blocks created during blockchain
integrity performance evaluation, while preserving the genesis block.

Usage:
    python manage.py cleanup_blockchain_test_data
    python manage.py cleanup_blockchain_test_data --config evaluation/blockchain/config/cleanup_config.yml
    python manage.py cleanup_blockchain_test_data --dry-run
    python manage.py cleanup_blockchain_test_data --older-than 7
"""

import logging
import yaml
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Transaction
from apps.blockchain.models import Block

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up blockchain test data created during performance evaluation'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            default='evaluation/blockchain/config/cleanup_config.yml',
            help='Path to YAML configuration file',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--older-than',
            type=int,
            default=None,
            help='Only delete test data older than N days',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation prompts',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about what is being deleted',
        )
    
    def handle(self, *args, **options):
        config_path = options['config']
        
        # Load configuration from YAML
        config = self._load_config(config_path)
        if not config:
            return
        
        # Override config with CLI arguments if provided
        dry_run = options['dry_run'] if options['dry_run'] is not None else config['cleanup']['dry_run']
        older_than_days = options['older_than'] if options['older_than'] is not None else config['cleanup']['older_than_days']
        force = options['force'] if options['force'] is not None else config['cleanup']['force']
        verbose = options['verbose'] if options['verbose'] is not None else config['cleanup']['verbose']
        
        self.stdout.write("🧹 Blockchain Test Data Cleanup")
        self.stdout.write("=" * 50)
        
        if dry_run:
            self.stdout.write("🔍 DRY RUN MODE - No data will be deleted")
        
        # Get test data counts
        test_transactions = self._get_test_transactions(older_than_days) if config['data']['clean_transactions'] else Transaction.objects.none()
        test_blocks = self._get_test_blocks(older_than_days) if config['data']['clean_blocks'] else Block.objects.none()
        
        # Apply safety limits
        max_delete_count = config['safety']['max_delete_count']
        if max_delete_count:
            test_transactions = test_transactions[:max_delete_count]
            test_blocks = test_blocks[:max_delete_count]
        
        # Display summary
        self._display_summary(test_transactions, test_blocks, verbose)
        
        if not test_transactions.exists() and not test_blocks.exists():
            self.stdout.write("✅ No test data found to clean up")
            return
        
        # Confirm deletion (unless force is used)
        confirm_threshold = config['safety']['confirm_threshold']
        total_items = test_transactions.count() + test_blocks.count()
        
        if not dry_run and not force and total_items > confirm_threshold:
            if not self._confirm_deletion(test_transactions.count(), test_blocks.count()):
                self.stdout.write("❌ Cleanup cancelled")
                return
        
        # Perform cleanup
        self._perform_cleanup(test_transactions, test_blocks, dry_run, verbose)
        
        self.stdout.write("✅ Cleanup completed successfully")
    
    def _load_config(self, config_path):
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            self.stdout.write(f"✅ Loaded configuration from {config_path}")
            return config
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ Configuration file not found: {config_path}"))
            return None
        except yaml.YAMLError as e:
            self.stdout.write(self.style.ERROR(f"❌ Error parsing YAML configuration: {e}"))
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error loading configuration: {e}"))
            return None
    
    def _get_test_transactions(self, older_than_days=None):
        """Get test transactions that should be cleaned up."""
        queryset = Transaction.objects.filter(transaction_id__startswith='TEST-')
        
        if older_than_days:
            cutoff_date = timezone.now() - timedelta(days=older_than_days)
            queryset = queryset.filter(created_at__lt=cutoff_date)
        
        return queryset
    
    def _get_test_blocks(self, older_than_days=None):
        """Get test blocks that should be cleaned up (excluding genesis block)."""
        queryset = Block.objects.filter(index__gt=0)
        
        if older_than_days:
            cutoff_date = timezone.now() - timedelta(days=older_than_days)
            queryset = queryset.filter(created_at__lt=cutoff_date)
        
        return queryset
    
    def _display_summary(self, test_transactions, test_blocks, verbose):
        """Display summary of data to be cleaned up."""
        transaction_count = test_transactions.count()
        block_count = test_blocks.count()
        
        self.stdout.write(f"📊 Found {transaction_count} test transactions")
        self.stdout.write(f"📦 Found {block_count} test blocks (excluding genesis)")
        
        if verbose and transaction_count > 0:
            self.stdout.write("\n📋 Test Transactions:")
            for transaction in test_transactions[:10]:  # Show first 10
                self.stdout.write(f"   - {transaction.transaction_id} ({transaction.project_name})")
            
            if transaction_count > 10:
                self.stdout.write(f"   ... and {transaction_count - 10} more")
        
        if verbose and block_count > 0:
            self.stdout.write("\n📋 Test Blocks:")
            for block in test_blocks[:10]:  # Show first 10
                self.stdout.write(f"   - Block {block.index} (Hash: {block.hash[:16]}...)")
            
            if block_count > 10:
                self.stdout.write(f"   ... and {block_count - 10} more")
        
        self.stdout.write("")
    
    def _confirm_deletion(self, transaction_count, block_count):
        """Ask user to confirm deletion."""
        self.stdout.write("⚠️  This will permanently delete:")
        self.stdout.write(f"   - {transaction_count} test transactions")
        self.stdout.write(f"   - {block_count} test blocks")
        self.stdout.write("")
        
        response = input("Are you sure you want to continue? (yes/no): ").lower().strip()
        return response in ['yes', 'y']
    
    def _perform_cleanup(self, test_transactions, test_blocks, dry_run, verbose):
        """Perform the actual cleanup operation."""
        if dry_run:
            self.stdout.write("🔍 Would delete:")
            self.stdout.write(f"   - {test_transactions.count()} test transactions")
            self.stdout.write(f"   - {test_blocks.count()} test blocks")
            return
        
        # Delete test transactions
        transaction_count = test_transactions.count()
        if transaction_count > 0:
            if verbose:
                self.stdout.write(f"🗑️  Deleting {transaction_count} test transactions...")
            
            deleted_transactions = test_transactions.delete()
            actual_transaction_count = deleted_transactions[0] if deleted_transactions else 0
            self.stdout.write(f"✅ Deleted {actual_transaction_count} test transactions")
        
        # Delete test blocks
        block_count = test_blocks.count()
        if block_count > 0:
            if verbose:
                self.stdout.write(f"🗑️  Deleting {block_count} test blocks...")
            
            deleted_blocks = test_blocks.delete()
            actual_block_count = deleted_blocks[0] if deleted_blocks else 0
            self.stdout.write(f"✅ Deleted {actual_block_count} test blocks")
        
        # Verify genesis block is preserved
        genesis_block = Block.objects.filter(index=0).first()
        if genesis_block:
            self.stdout.write("✅ Genesis block preserved")
        else:
            self.stdout.write("⚠️  Warning: Genesis block not found")
    
    def _get_database_stats(self):
        """Get database statistics for reporting."""
        total_transactions = Transaction.objects.count()
        total_blocks = Block.objects.count()
        test_transactions = Transaction.objects.filter(transaction_id__startswith='TEST-').count()
        test_blocks = Block.objects.filter(index__gt=0).count()
        
        return {
            'total_transactions': total_transactions,
            'total_blocks': total_blocks,
            'test_transactions': test_transactions,
            'test_blocks': test_blocks,
            'production_transactions': total_transactions - test_transactions,
            'production_blocks': total_blocks - test_blocks
        } 