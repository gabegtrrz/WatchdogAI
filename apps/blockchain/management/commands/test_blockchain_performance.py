"""
Management command to test and measure blockchain performance metrics.

This command measures:
1. Throughput: Transactions Per Second (TPS)
2. Data Integrity Verification Time: Time to traverse and verify the entire chain

Usage:
    python manage.py test_blockchain_performance --runs 5 --transactions-per-block 100
"""

import json
import time
import statistics
import pandas as pd
from io import StringIO
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone
from apps.blockchain.models import Block
from apps.blockchain.services import create_genesis_block, create_new_block, verify_blockchain_integrity
from apps.blockchain.integration import integrate_transaction_batch
from apps.core.models import Transaction, ProcurementMethod
from apps.transaction_management.services import process_transaction_csv, create_transactions_from_data
from apps.data_augmentation.services import enrich_transaction_list
import logging

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test and measure blockchain performance metrics'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--runs',
            type=int,
            default=3,
            help='Number of test runs to perform (default: 3)'
        )
        parser.add_argument(
            '--transactions-per-block',
            type=int,
            default=50,
            help='Number of transactions to create per block for throughput testing (default: 50)'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            default='blockchain_performance_results.json',
            help='Output file for JSON results (default: blockchain_performance_results.json)'
        )
        parser.add_argument(
            '--no-cleanup',
            action='store_true',
            help='Skip cleanup of test data after testing (default: cleanup is enabled)'
        )
    
    def handle(self, *args, **options):
        runs = options['runs']
        transactions_per_block = options['transactions_per_block']
        output_file = options['output_file']
        skip_cleanup = options['no_cleanup']
        
        self.stdout.write("🚀 Starting blockchain performance testing...")
        self.stdout.write(f"📊 Test Configuration:")
        self.stdout.write(f"  - Number of runs: {runs}")
        self.stdout.write(f"  - Transactions per block: {transactions_per_block}")
        self.stdout.write(f"  - Output file: {output_file}")
        self.stdout.write(f"  - Cleanup: {'Disabled' if skip_cleanup else 'Enabled (default)'}")
        
        # Store original state for cleanup
        original_block_count = Block.objects.count()
        original_transaction_count = Transaction.objects.count()
        
        try:
            # Ensure genesis block exists
            genesis_block = create_genesis_block()
            if not genesis_block:
                self.stdout.write(self.style.ERROR("❌ Failed to create genesis block"))
                return
            
            # Verify blockchain integrity before testing
            self.stdout.write("🔍 Verifying initial blockchain integrity...")
            if not verify_blockchain_integrity():
                self.stdout.write(self.style.WARNING("⚠️  Blockchain integrity check failed before testing"))
            
            # Run performance tests
            results = self._run_performance_tests(runs, transactions_per_block)
            
            # Save results to JSON file
            self._save_results(results, output_file)
            
            # Display summary
            self._display_summary(results)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error during performance testing: {e}"))
            logger.error(f"Performance testing error: {e}")
        finally:
            # Cleanup by default (unless --no-cleanup is specified)
            if not skip_cleanup:
                self._cleanup_test_data(original_block_count, original_transaction_count)
    
    def _run_performance_tests(self, runs, transactions_per_block):
        """Run multiple performance test iterations."""
        all_results = []
        
        for run in range(1, runs + 1):
            self.stdout.write(f"\n🔄 Running test iteration {run}/{runs}...")
            
            # Clean up any previous test data
            self._cleanup_previous_test_data()
            
            # Run single test iteration
            run_results = self._run_single_test(run, transactions_per_block)
            all_results.append(run_results)
            
            self.stdout.write(f"✅ Test iteration {run} completed")
        
        # Calculate aggregate statistics
        return self._calculate_aggregate_statistics(all_results)
    
    def _run_single_test(self, run_number, transactions_per_block):
        """Run a single performance test iteration."""
        results = {
            'run_number': run_number,
            'timestamp': timezone.now().isoformat(),
            'throughput_test': {},
            'integrity_test': {}
        }
        
        # Test 1: Throughput (TPS)
        throughput_results = self._test_throughput(transactions_per_block)
        results['throughput_test'] = throughput_results
        
        # Test 2: Data Integrity Verification Time
        integrity_results = self._test_integrity_verification()
        results['integrity_test'] = integrity_results
        
        return results
    
    def _test_throughput(self, transactions_per_block):
        """Test transaction processing throughput using the full pipeline."""
        self.stdout.write("  📈 Testing throughput with full transaction pipeline...")
        
        # Ensure procurement methods exist
        self.stdout.write("  🔧 Ensuring procurement methods exist...")
        self._ensure_procurement_methods_exist()
        
        # Read from existing CSV file
        start_time = time.time()
        csv_data = self._get_test_csv_data(transactions_per_block)
        csv_reading_time = time.time() - start_time
        
        # Process CSV through the full pipeline
        start_time = time.time()
        pipeline_results = self._run_transaction_pipeline(csv_data, transactions_per_block)
        pipeline_time = time.time() - start_time
        
        if not pipeline_results['success']:
            raise Exception(f"Pipeline failed: {pipeline_results.get('error', 'Unknown error')}")
        
        # Calculate metrics
        total_time = csv_reading_time + pipeline_time
        tps = transactions_per_block / total_time if total_time > 0 else 0
        
        return {
            'transactions_created': transactions_per_block,
            'csv_reading_time': csv_reading_time,
            'pipeline_time': pipeline_time,
            'total_time': total_time,
            'transactions_per_second': tps,
            'blockchain_success': pipeline_results['blockchain_success'],
            'enrichment_stats': pipeline_results['enrichment_stats'],
            'block_info': pipeline_results.get('block_info')
        }
    
    def _test_integrity_verification(self):
        """Test data integrity verification time."""
        self.stdout.write("  🔍 Testing integrity verification...")
        
        # Get current blockchain state
        total_blocks = Block.objects.count()
        total_transactions = Transaction.objects.count()
        
        # Measure integrity verification time
        start_time = time.time()
        integrity_valid = verify_blockchain_integrity()
        verification_time = time.time() - start_time
        
        return {
            'total_blocks': total_blocks,
            'total_transactions': total_transactions,
            'verification_time': verification_time,
            'integrity_valid': integrity_valid
        }
    
    def _get_test_csv_data(self, count):
        """Read test CSV data from existing file."""
        import os
        
        # Path to the existing CSV file
        csv_path = "data/training/training_data/22_100/unlabeled/eval.csv"
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Test CSV file not found: {csv_path}")
        
        # Create a file-like object that mimics Django's uploaded file
        class MockUploadedFile:
            def __init__(self, file_path):
                self.file_path = file_path
                self.name = "eval.csv"
                self.file = open(file_path, 'rb')
            
            def read(self):
                return self.file.read()
            
            def decode(self, encoding='utf-8'):
                return self.file.read().decode(encoding)
            
            def close(self):
                self.file.close()
        
        return MockUploadedFile(csv_path)
    
    def _ensure_procurement_methods_exist(self):
        """Ensure that procurement methods from the CSV exist in the database."""
        from apps.core.models import ProcurementMethod
        
        # Get procurement methods from the CSV file
        csv_path = "data/training/training_data/22_100/unlabeled/eval.csv"
        import pandas as pd
        
        df = pd.read_csv(csv_path)
        csv_methods = set(df['procurement_method_name'].unique())
        
        # Check which methods exist in the database
        existing_methods = set(ProcurementMethod.objects.values_list('name', flat=True))
        
        # Find missing methods
        missing_methods = csv_methods - existing_methods
        
        if missing_methods:
            self.stdout.write(f"  ⚠️  Creating missing procurement methods: {missing_methods}")
            for method_name in missing_methods:
                ProcurementMethod.objects.get_or_create(name=method_name)
                self.stdout.write(f"    - Created: {method_name}")
        
        return len(missing_methods)
    
    def _run_transaction_pipeline(self, csv_file, count):
        """Run the complete transaction processing pipeline."""
        try:
            # Step 1: Process CSV through validation
            valid_data, errors = process_transaction_csv(csv_file)
            
            if errors:
                # Log detailed error information
                self.stdout.write(f"  ❌ CSV validation errors:")
                for error in errors:
                    if 'type' in error:
                        self.stdout.write(f"    - {error['type']}: {error['message']}")
                    elif 'row' in error:
                        self.stdout.write(f"    - Row {error['row']}:")
                        for field_error in error.get('errors', []):
                            self.stdout.write(f"      {field_error['field']}: {field_error['error']}")
                
                return {
                    'success': False,
                    'error': f"CSV validation failed: {len(errors)} errors"
                }
            
            if not valid_data:
                return {
                    'success': False,
                    'error': "No valid data found in CSV"
                }
            
            # Limit to requested number of transactions
            valid_data = valid_data[:count] if count < len(valid_data) else valid_data
            
            # Step 2: Create transactions from validated data
            created_transactions = create_transactions_from_data(valid_data)
            
            # Step 3: Enrich transactions
            enrichment_stats = enrich_transaction_list(created_transactions)
            
            # Step 4: Integrate with blockchain
            blockchain_success, blockchain_result = integrate_transaction_batch(created_transactions)
            
            return {
                'success': True,
                'blockchain_success': blockchain_success,
                'enrichment_stats': enrichment_stats,
                'block_info': blockchain_result.get('block_info'),
                'integrated_count': blockchain_result.get('integrated_count', 0),
                'failed_count': blockchain_result.get('failed_count', 0)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _cleanup_previous_test_data(self):
        """Clean up test data from previous runs."""
        # Delete transactions from the test CSV file
        # We'll identify them by checking if they're from the eval.csv file
        # Since the CSV has specific transaction IDs, we can clean them up
        
        # Delete test blocks (except genesis)
        Block.objects.filter(index__gt=0).delete()
        
        # Note: We don't delete the actual transactions from the CSV file
        # as they are real test data that should persist
    
    def _calculate_aggregate_statistics(self, all_results):
        """Calculate aggregate statistics from all test runs."""
        throughput_times = [r['throughput_test']['total_time'] for r in all_results]
        throughput_tps = [r['throughput_test']['transactions_per_second'] for r in all_results]
        integrity_times = [r['integrity_test']['verification_time'] for r in all_results]
        integrity_blocks = [r['integrity_test']['total_blocks'] for r in all_results]
        integrity_transactions = [r['integrity_test']['total_transactions'] for r in all_results]
        
        return {
            'test_configuration': {
                'total_runs': len(all_results),
                'transactions_per_block': all_results[0]['throughput_test']['transactions_created'],
                'test_timestamp': timezone.now().isoformat()
            },
            'throughput_statistics': {
                'mean_tps': statistics.mean(throughput_tps),
                'median_tps': statistics.median(throughput_tps),
                'min_tps': min(throughput_tps),
                'max_tps': max(throughput_tps),
                'std_dev_tps': statistics.stdev(throughput_tps) if len(throughput_tps) > 1 else 0,
                'mean_total_time': statistics.mean(throughput_times),
                'median_total_time': statistics.median(throughput_times)
            },
            'integrity_statistics': {
                'mean_verification_time': statistics.mean(integrity_times),
                'median_verification_time': statistics.median(integrity_times),
                'min_verification_time': min(integrity_times),
                'max_verification_time': max(integrity_times),
                'std_dev_verification_time': statistics.stdev(integrity_times) if len(integrity_times) > 1 else 0,
                'mean_blocks_verified': statistics.mean(integrity_blocks),
                'mean_transactions_verified': statistics.mean(integrity_transactions)
            },
            'detailed_results': all_results
        }
    
    def _save_results(self, results, output_file):
        """Save results to JSON file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            self.stdout.write(f"💾 Results saved to {output_file}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to save results: {e}"))
    
    def _display_summary(self, results):
        """Display a summary of the test results."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📊 BLOCKCHAIN PERFORMANCE TEST RESULTS")
        self.stdout.write("="*60)
        
        # Throughput summary
        tps_stats = results['throughput_statistics']
        self.stdout.write(f"\n🚀 THROUGHPUT METRICS:")
        self.stdout.write(f"  - Mean TPS: {tps_stats['mean_tps']:.2f}")
        self.stdout.write(f"  - Median TPS: {tps_stats['median_tps']:.2f}")
        self.stdout.write(f"  - Min TPS: {tps_stats['min_tps']:.2f}")
        self.stdout.write(f"  - Max TPS: {tps_stats['max_tps']:.2f}")
        self.stdout.write(f"  - Std Dev TPS: {tps_stats['std_dev_tps']:.2f}")
        
        # Integrity verification summary
        integrity_stats = results['integrity_statistics']
        self.stdout.write(f"\n🔍 INTEGRITY VERIFICATION METRICS:")
        self.stdout.write(f"  - Mean verification time: {integrity_stats['mean_verification_time']:.4f}s")
        self.stdout.write(f"  - Median verification time: {integrity_stats['median_verification_time']:.4f}s")
        self.stdout.write(f"  - Min verification time: {integrity_stats['min_verification_time']:.4f}s")
        self.stdout.write(f"  - Max verification time: {integrity_stats['max_verification_time']:.4f}s")
        self.stdout.write(f"  - Mean blocks verified: {integrity_stats['mean_blocks_verified']:.1f}")
        self.stdout.write(f"  - Mean transactions verified: {integrity_stats['mean_transactions_verified']:.1f}")
        
        # Test configuration
        config = results['test_configuration']
        self.stdout.write(f"\n⚙️  TEST CONFIGURATION:")
        self.stdout.write(f"  - Total runs: {config['total_runs']}")
        self.stdout.write(f"  - Transactions per block: {config['transactions_per_block']}")
        self.stdout.write(f"  - Test timestamp: {config['test_timestamp']}")
        
        self.stdout.write("\n✅ Performance testing completed successfully!")
    
    def _cleanup_test_data(self, original_block_count, original_transaction_count):
        """Clean up test data and restore original state."""
        self.stdout.write("\n🧹 Cleaning up test data...")
        
        try:
            # Delete test transactions
            test_transactions = Transaction.objects.filter(
                transaction_id__startswith="TEST_TX_"
            )
            deleted_transactions = test_transactions.count()
            test_transactions.delete()
            
            # Delete test blocks (except genesis)
            test_blocks = Block.objects.filter(index__gt=0)
            deleted_blocks = test_blocks.count()
            test_blocks.delete()
            
            self.stdout.write(f"  - Deleted {deleted_transactions} test transactions")
            self.stdout.write(f"  - Deleted {deleted_blocks} test blocks")
            self.stdout.write("✅ Cleanup completed")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Cleanup failed: {e}")) 