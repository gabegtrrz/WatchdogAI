"""
Management command to clean up blockchain test data.

This command removes test transactions and blocks created during blockchain
integrity performance evaluation, while preserving the genesis block.

Usage:
    python manage.py cleanup_blockchain_test_data
    python manage.py cleanup_blockchain_test_data --config evaluation/blockchain/config/cleanup_config.yml
    python manage.py cleanup_blockchain_test_data --dry-run
    python manage.py cleanup_blockchain_test_data --older-than 7
    python manage.py cleanup_blockchain_test_data --complete-cleanup
"""

import json
import logging
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core import serializers
from apps.core.models import Transaction, ProcurementMethod
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
        parser.add_argument(
            '--complete-cleanup',
            action='store_true',
            help='Perform complete cleanup (removes ALL blockchain data)',
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
        complete_cleanup = options['complete_cleanup'] or config['data']['complete_cleanup']['enabled']
        
        self.stdout.write("🧹 Blockchain Data Cleanup")
        self.stdout.write("=" * 50)
        
        if complete_cleanup:
            self.stdout.write("⚠️  COMPLETE CLEANUP MODE - This will remove ALL blockchain data")
        
        if dry_run:
            self.stdout.write("🔍 DRY RUN MODE - No data will be deleted")
        
        # Handle complete cleanup
        if complete_cleanup:
            self._handle_complete_cleanup(config, dry_run, force, verbose)
            return
        
        # Handle regular test data cleanup
        self._handle_test_data_cleanup(config, dry_run, older_than_days, force, verbose)
    
    def _handle_complete_cleanup(self, config, dry_run, force, verbose):
        """Handle complete cleanup of all blockchain data."""
        complete_config = config['data']['complete_cleanup']
        
        # Create backup if requested
        if complete_config['create_backup'] and not dry_run:
            backup_path = self._create_backup(complete_config['backup_path'])
            if not backup_path:
                self.stdout.write(self.style.ERROR("❌ Failed to create backup. Aborting complete cleanup."))
                return
        
        # Get all data for deletion
        all_transactions = Transaction.objects.all() if complete_config['remove_all_transactions'] else Transaction.objects.none()
        all_blocks = Block.objects.all() if complete_config['remove_all_blocks'] else Block.objects.none()
        all_procurement_methods = ProcurementMethod.objects.all() if complete_config['remove_procurement_methods'] else ProcurementMethod.objects.none()
        
        # Display summary
        self._display_complete_cleanup_summary(all_transactions, all_blocks, all_procurement_methods, verbose)
        
        if not any([all_transactions.exists(), all_blocks.exists(), all_procurement_methods.exists()]):
            self.stdout.write("✅ No data found to clean up")
            return
        
        # Confirm deletion
        if not dry_run and not force:
            if config['safety']['require_complete_cleanup_confirmation']:
                if not self._confirm_complete_cleanup(all_transactions.count(), all_blocks.count(), all_procurement_methods.count()):
                    self.stdout.write("❌ Complete cleanup cancelled")
                    return
        
        # Perform complete cleanup
        self._perform_complete_cleanup(all_transactions, all_blocks, all_procurement_methods, dry_run, verbose)
        
        self.stdout.write("✅ Complete cleanup finished")
    
    def _handle_test_data_cleanup(self, config, dry_run, older_than_days, force, verbose):
        """Handle regular test data cleanup."""
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
        
        self.stdout.write("✅ Test data cleanup completed successfully")
    
    def _create_backup(self, backup_path_template):
        """Create a backup of all blockchain data."""
        try:
            # Generate backup path with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_path_template.format(timestamp=timestamp)
            
            # Ensure backup directory exists
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize all blockchain data
            backup_data = {
                'timestamp': timezone.now().isoformat(),
                'transactions': [],
                'blocks': [],
                'procurement_methods': []
            }
            
            # Backup transactions
            for transaction in Transaction.objects.all():
                backup_data['transactions'].append({
                    'transaction_id': transaction.transaction_id,
                    'project_name': transaction.project_name,
                    'item_name': transaction.item_name,
                    'quantity': transaction.quantity,
                    'unit_purchase_price': str(transaction.unit_purchase_price),
                    'total_purchase_price': str(transaction.total_purchase_price),
                    'transaction_date': transaction.transaction_date.isoformat(),
                    'created_at': transaction.created_at.isoformat(),
                    'updated_at': transaction.updated_at.isoformat()
                })
            
            # Backup blocks
            for block in Block.objects.all():
                backup_data['blocks'].append({
                    'index': block.index,
                    'timestamp': block.timestamp.isoformat(),
                    'hash': block.hash,
                    'previous_hash': block.previous_hash,
                    'merkle_root': block.merkle_root,
                    'created_at': block.created_at.isoformat()
                })
            
            # Backup procurement methods
            for method in ProcurementMethod.objects.all():
                backup_data['procurement_methods'].append({
                    'name': method.name,
                    'description': method.description,
                    'created_at': method.created_at.isoformat()
                })
            
            # Save backup
            with open(backup_path, 'w', encoding='utf-8') as file:
                json.dump(backup_data, file, indent=2, default=str)
            
            self.stdout.write(f"✅ Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error creating backup: {e}"))
            return None
    
    def _display_complete_cleanup_summary(self, transactions, blocks, procurement_methods, verbose):
        """Display summary for complete cleanup."""
        transaction_count = transactions.count()
        block_count = blocks.count()
        method_count = procurement_methods.count()
        
        self.stdout.write(f"📊 Complete Cleanup Summary:")
        self.stdout.write(f"   - Transactions: {transaction_count}")
        self.stdout.write(f"   - Blocks: {block_count}")
        self.stdout.write(f"   - Procurement Methods: {method_count}")
        
        if verbose:
            if transaction_count > 0:
                self.stdout.write(f"\n📋 Sample Transactions:")
                for transaction in transactions[:5]:
                    self.stdout.write(f"   - {transaction.transaction_id} ({transaction.project_name})")
                if transaction_count > 5:
                    self.stdout.write(f"   ... and {transaction_count - 5} more")
            
            if block_count > 0:
                self.stdout.write(f"\n📋 Sample Blocks:")
                for block in blocks[:5]:
                    self.stdout.write(f"   - Block {block.index} (Hash: {block.hash[:16]}...)")
                if block_count > 5:
                    self.stdout.write(f"   ... and {block_count - 5} more")
        
        self.stdout.write("")
    
    def _confirm_complete_cleanup(self, transaction_count, block_count, method_count):
        """Ask user to confirm complete cleanup."""
        self.stdout.write("⚠️  COMPLETE CLEANUP WARNING:")
        self.stdout.write("   This will permanently delete ALL blockchain data:")
        self.stdout.write(f"   - {transaction_count} transactions (including production data)")
        self.stdout.write(f"   - {block_count} blocks (including genesis block)")
        self.stdout.write(f"   - {method_count} procurement methods")
        self.stdout.write("")
        self.stdout.write("   This action cannot be undone!")
        self.stdout.write("")
        
        response = input("Type 'DELETE ALL DATA' to confirm complete cleanup: ").strip()
        return response == 'DELETE ALL DATA'
    
    def _perform_complete_cleanup(self, transactions, blocks, procurement_methods, dry_run, verbose):
        """Perform complete cleanup operation."""
        if dry_run:
            self.stdout.write("🔍 Would delete:")
            self.stdout.write(f"   - {transactions.count()} transactions")
            self.stdout.write(f"   - {blocks.count()} blocks")
            self.stdout.write(f"   - {procurement_methods.count()} procurement methods")
            return
        
        # Delete transactions
        transaction_count = transactions.count()
        if transaction_count > 0:
            if verbose:
                self.stdout.write(f"🗑️  Deleting {transaction_count} transactions...")
            
            deleted_transactions = transactions.delete()
            actual_transaction_count = deleted_transactions[0] if deleted_transactions else 0
            self.stdout.write(f"✅ Deleted {actual_transaction_count} transactions")
        
        # Delete blocks
        block_count = blocks.count()
        if block_count > 0:
            if verbose:
                self.stdout.write(f"🗑️  Deleting {block_count} blocks...")
            
            deleted_blocks = blocks.delete()
            actual_block_count = deleted_blocks[0] if deleted_blocks else 0
            self.stdout.write(f"✅ Deleted {actual_block_count} blocks")
        
        # Delete procurement methods
        method_count = procurement_methods.count()
        if method_count > 0:
            if verbose:
                self.stdout.write(f"🗑️  Deleting {method_count} procurement methods...")
            
            deleted_methods = procurement_methods.delete()
            actual_method_count = deleted_methods[0] if deleted_methods else 0
            self.stdout.write(f"✅ Deleted {actual_method_count} procurement methods")
    
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