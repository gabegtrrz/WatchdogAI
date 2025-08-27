"""
Management command to evaluate blockchain integrity verification performance.

This command creates test blockchains with different sizes (100, 1,000, 10,000 blocks)
and measures the time it takes to verify integrity for each size.

Usage:
    python manage.py evaluate_integrity_performance --config evaluation/blockchain/config/integrity_performance_config.yml
"""

import csv
import json
import time
import logging
import yaml
from decimal import Decimal
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.core.models import Transaction, ProcurementMethod
from apps.blockchain.models import Block
from apps.blockchain.services import create_new_block, verify_blockchain_integrity, create_genesis_block

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Evaluate blockchain integrity verification performance with different block sizes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            default='evaluation/blockchain/config/integrity_performance_config.yml',
            help='Path to YAML configuration file',
        )
    
    def handle(self, *args, **options):
        config_path = options['config']
        
        # Load configuration from YAML
        config = self._load_config(config_path)
        if not config:
            return
        
        self.stdout.write("🚀 Starting blockchain integrity performance evaluation...")
        self.stdout.write(f"📊 Testing block sizes: {config['test']['block_sizes']}")
        self.stdout.write(f"📦 Transactions per block: {config['input']['transactions_per_block']}")
        self.stdout.write(f"🔄 Iterations per test: {config['test']['iterations']}")
        
        # Load transaction data from CSV
        transactions_data = self._load_transaction_data(config['input']['csv_file'])
        if not transactions_data:
            self.stdout.write(self.style.ERROR("❌ Failed to load transaction data"))
            return
        
        # Ensure we have a procurement method
        procurement_method = self._get_or_create_procurement_method()
        
        # Run performance evaluation
        results = self._evaluate_performance(
            transactions_data, 
            config['test']['block_sizes'], 
            config['input']['transactions_per_block'], 
            config['test']['iterations'],
            procurement_method
        )
        
        # Display results
        self._display_results(results, config)
        
        # Save results to file
        self._save_results(results, config)
        
        # Cleanup if requested
        if config['test']['cleanup']:
            self._cleanup_test_data()
    
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
    
    def _load_transaction_data(self, csv_file):
        """Load transaction data from CSV file."""
        try:
            transactions = []
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    transactions.append(row)
            
            self.stdout.write(f"✅ Loaded {len(transactions)} transactions from {csv_file}")
            return transactions
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error loading CSV file: {e}"))
            return None
    
    def _get_or_create_procurement_method(self):
        """Get or create a default procurement method."""
        method, created = ProcurementMethod.objects.get_or_create(
            name="Competitive Bidding",
            defaults={'description': 'Default procurement method for testing'}
        )
        if created:
            self.stdout.write("✅ Created default procurement method")
        return method
    
    def _create_test_transaction(self, data, procurement_method, index):
        """Create a test transaction from CSV data."""
        try:
            # Generate unique transaction ID
            transaction_id = f"TEST-{index:06d}"
            
            # Parse numeric fields
            quantity = int(data.get('quantity', 1))
            unit_price = Decimal(data.get('unit_purchase_price', '0.00'))
            total_price = Decimal(data.get('total_purchase_price', '0.00'))
            average_price = Decimal(data.get('average_price', '0.00')) if data.get('average_price') else None
            approved_budget = Decimal(data.get('approved_budget', '0.00')) if data.get('approved_budget') else None
            
            # Parse date fields
            transaction_date = timezone.datetime.strptime(data.get('transaction_date', '2022-01-01'), '%Y-%m-%d').date()
            
            # Create transaction
            transaction = Transaction.objects.create(
                transaction_id=transaction_id,
                project_name=data.get('project_name', 'Test Project'),
                end_user_unit=data.get('end_user_unit', 'Test Unit'),
                project_description=data.get('project_description', 'Test Description'),
                item_name=data.get('item_name', 'Test Item'),
                quantity=quantity,
                unit_purchase_price=unit_price,
                total_purchase_price=total_price,
                average_price=average_price,
                approved_budget=approved_budget,
                procurement_method=procurement_method,
                supplier=data.get('supplier', 'Test Supplier'),
                procurement_officer=data.get('procurement_officer', 'Test Officer'),
                invoice_number=data.get('invoice_number', f'INV-{index:06d}'),
                payment_receipt_number=data.get('payment_receipt_number', f'RCPT-{index:06d}'),
                transaction_date=transaction_date,
                blockchain_status='pending'
            )
            
            return transaction
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error creating transaction {index}: {e}"))
            return None
    
    def _create_test_blockchain(self, transactions_data, num_blocks, transactions_per_block, procurement_method):
        """Create a test blockchain with specified number of blocks."""
        self.stdout.write(f"🏗️  Creating test blockchain with {num_blocks} blocks...")
        
        # Clear existing blocks (except genesis)
        Block.objects.filter(index__gt=0).delete()
        Transaction.objects.filter(block__isnull=False).delete()
        
        # Ensure genesis block exists
        genesis_block = Block.objects.filter(index=0).first()
        if not genesis_block:
            genesis_block = create_genesis_block()
        
        total_transactions_needed = num_blocks * transactions_per_block
        created_transactions = []
        
        # Create transactions
        for i in range(total_transactions_needed):
            # Cycle through CSV data if we need more transactions
            csv_index = i % len(transactions_data)
            transaction = self._create_test_transaction(
                transactions_data[csv_index], 
                procurement_method, 
                i
            )
            if transaction:
                created_transactions.append(transaction)
        
        # Create blocks with transactions
        for block_index in range(1, num_blocks + 1):
            start_idx = (block_index - 1) * transactions_per_block
            end_idx = start_idx + transactions_per_block
            block_transactions = created_transactions[start_idx:end_idx]
            
            # Create new block
            new_block = create_new_block(block_transactions)
            if not new_block:
                self.stdout.write(self.style.ERROR(f"❌ Failed to create block {block_index}"))
                return None
        
        self.stdout.write(f"✅ Created blockchain with {num_blocks} blocks and {len(created_transactions)} transactions")
        return len(created_transactions)
    
    def _measure_integrity_verification_time(self):
        """Measure time taken to verify blockchain integrity."""
        start_time = time.time()
        is_valid = verify_blockchain_integrity()
        end_time = time.time()
        
        return {
            'time_seconds': end_time - start_time,
            'is_valid': is_valid
        }
    
    def _evaluate_performance(self, transactions_data, block_sizes, transactions_per_block, iterations, procurement_method):
        """Run performance evaluation for different block sizes."""
        results = {}
        
        for block_size in block_sizes:
            self.stdout.write(f"\n📈 Testing block size: {block_size}")
            results[block_size] = {
                'times': [],
                'valid_results': [],
                'total_transactions': 0
            }
            
            for iteration in range(iterations):
                self.stdout.write(f"  🔄 Iteration {iteration + 1}/{iterations}")
                
                # Create test blockchain
                total_transactions = self._create_test_blockchain(
                    transactions_data, 
                    block_size, 
                    transactions_per_block, 
                    procurement_method
                )
                
                if total_transactions is None:
                    self.stdout.write(self.style.ERROR(f"  ❌ Failed to create blockchain for iteration {iteration + 1}"))
                    continue
                
                # Measure integrity verification time
                verification_result = self._measure_integrity_verification_time()
                
                results[block_size]['times'].append(verification_result['time_seconds'])
                results[block_size]['valid_results'].append(verification_result['is_valid'])
                results[block_size]['total_transactions'] = total_transactions
                
                self.stdout.write(f"    ⏱️  Verification time: {verification_result['time_seconds']:.4f}s")
                self.stdout.write(f"    ✅ Integrity valid: {verification_result['is_valid']}")
        
        return results
    
    def _display_results(self, results, config):
        """Display performance evaluation results."""
        self.stdout.write("\n" + "="*80)
        self.stdout.write("📊 BLOCKCHAIN INTEGRITY PERFORMANCE RESULTS")
        self.stdout.write("="*80)
        
        thresholds = config.get('thresholds', {})
        
        for block_size, data in results.items():
            if not data['times']:
                continue
                
            avg_time = sum(data['times']) / len(data['times'])
            min_time = min(data['times'])
            max_time = max(data['times'])
            valid_count = sum(data['valid_results'])
            total_iterations = len(data['times'])
            
            self.stdout.write(f"\n🔸 Block Size: {block_size:,} blocks")
            self.stdout.write(f"   📦 Total Transactions: {data['total_transactions']:,}")
            self.stdout.write(f"   ⏱️  Average Time: {avg_time:.4f}s")
            self.stdout.write(f"   ⏱️  Min Time: {min_time:.4f}s")
            self.stdout.write(f"   ⏱️  Max Time: {max_time:.4f}s")
            self.stdout.write(f"   ✅ Valid Results: {valid_count}/{total_iterations}")
            
            # Calculate throughput
            if avg_time > 0:
                throughput = data['total_transactions'] / avg_time
                self.stdout.write(f"   🚀 Throughput: {throughput:.2f} transactions/second")
                
                # Check thresholds
                max_time_threshold = thresholds.get('max_verification_time_seconds')
                min_throughput_threshold = thresholds.get('min_throughput_transactions_per_second')
                
                if max_time_threshold and avg_time > max_time_threshold:
                    self.stdout.write(f"   ⚠️  WARNING: Average time exceeds threshold ({max_time_threshold}s)")
                
                if min_throughput_threshold and throughput < min_throughput_threshold:
                    self.stdout.write(f"   ⚠️  WARNING: Throughput below threshold ({min_throughput_threshold} txn/s)")
        
        # Performance comparison
        self.stdout.write("\n" + "-"*80)
        self.stdout.write("📈 PERFORMANCE COMPARISON")
        self.stdout.write("-"*80)
        
        block_sizes = sorted(results.keys())
        if len(block_sizes) >= 2:
            for i in range(len(block_sizes) - 1):
                current_size = block_sizes[i]
                next_size = block_sizes[i + 1]
                
                if results[current_size]['times'] and results[next_size]['times']:
                    current_avg = sum(results[current_size]['times']) / len(results[current_size]['times'])
                    next_avg = sum(results[next_size]['times']) / len(results[next_size]['times'])
                    
                    size_ratio = next_size / current_size
                    time_ratio = next_avg / current_avg
                    
                    self.stdout.write(f"\n🔸 {current_size:,} → {next_size:,} blocks:")
                    self.stdout.write(f"   📊 Size increase: {size_ratio:.1f}x")
                    self.stdout.write(f"   ⏱️  Time increase: {time_ratio:.2f}x")
                    
                    if time_ratio < size_ratio:
                        self.stdout.write(f"   ✅ Sub-linear scaling (good performance)")
                    elif time_ratio == size_ratio:
                        self.stdout.write(f"   ⚠️  Linear scaling")
                    else:
                        self.stdout.write(f"   ❌ Super-linear scaling (performance degradation)")
    
    def _save_results(self, results, config):
        """Save results to JSON file."""
        try:
            output_file = config['output']['results_file']
            
            # Ensure output directory exists
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare results data
            results_data = {
                'timestamp': timezone.now().isoformat(),
                'config': config,
                'results': results,
                'summary': {}
            }
            
            # Add summary statistics
            for block_size, data in results.items():
                if data['times']:
                    avg_time = sum(data['times']) / len(data['times'])
                    throughput = data['total_transactions'] / avg_time if avg_time > 0 else 0
                    
                    results_data['summary'][block_size] = {
                        'average_time_seconds': avg_time,
                        'min_time_seconds': min(data['times']),
                        'max_time_seconds': max(data['times']),
                        'total_transactions': data['total_transactions'],
                        'throughput_transactions_per_second': throughput,
                        'valid_results_count': sum(data['valid_results']),
                        'total_iterations': len(data['times'])
                    }
            
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as file:
                json.dump(results_data, file, indent=2, default=str)
            
            self.stdout.write(f"✅ Results saved to {output_file}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error saving results: {e}"))
    
    def _cleanup_test_data(self):
        """Clean up test data after evaluation."""
        self.stdout.write("\n🧹 Cleaning up test data...")
        
        try:
            # Delete test transactions
            test_transactions = Transaction.objects.filter(transaction_id__startswith='TEST-')
            test_count = test_transactions.count()
            test_transactions.delete()
            
            # Delete blocks (except genesis)
            test_blocks = Block.objects.filter(index__gt=0)
            block_count = test_blocks.count()
            test_blocks.delete()
            
            self.stdout.write(f"✅ Cleaned up {test_count} test transactions and {block_count} test blocks")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error during cleanup: {e}"))