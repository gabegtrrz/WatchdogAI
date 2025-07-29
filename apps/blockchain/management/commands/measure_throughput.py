"""
Management command to measure blockchain transaction throughput from a CSV file.
This command measures Transactions Per Second (TPS) by processing transactions from a given CSV file.
Usage:
    python manage.py measure_throughput --runs 5 --csv-path /path/to/your/transactions.csv
"""

import json
import time
import statistics
from django.core.management.base import BaseCommand
from apps.blockchain.services import create_genesis_block
from apps.blockchain.integration import integrate_transaction_batch
from apps.core.models import Transaction
from apps.blockchain.models import Block
from apps.transaction_management.services import process_transaction_csv, create_transactions_from_data
import logging
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command to measure blockchain throughput.
    """
    help = 'Measures blockchain transaction throughput (TPS) from a CSV file.'
    
    def add_arguments(self, parser):
        """
        Adds command-line arguments to the command.
        """
        parser.add_argument(
            '--runs',
            type=int,
            default=3,
            help='Number of test runs to perform.'
        )
        parser.add_argument(
            '--csv-path',
            type=str,
            required=True,
            help='Path to the CSV file containing transaction data.'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            default='blockchain_throughput_results.json',
            help='Output file for JSON results.'
        )
    
    def handle(self, *args, **options):
        """
        The main logic of the command.
        """
        runs = options['runs']
        csv_path = options['csv_path']
        output_file = options['output_file']

        self.stdout.write(self.style.SUCCESS("🚀 Starting Blockchain Throughput Measurement..."))
        self.stdout.write(f"📈 Number of runs: {runs}")
        self.stdout.write(f"📄 Using CSV file: {csv_path}")

        # Load and process the CSV file once before the runs
        try:
            with open(csv_path, 'rb') as f:
                transactions_data, errors = process_transaction_csv(f)
            
            if errors:
                self.stdout.write(self.style.ERROR("❌ Errors found in CSV file:"))
                for error in errors:
                    self.stdout.write(str(error))
                return
            if not transactions_data:
                self.stdout.write(self.style.ERROR("❌ No valid transaction data found in the CSV."))
                return
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ CSV file not found at: {csv_path}"))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ An error occurred while reading the CSV: {e}"))
            return

        transactions_per_run = len(transactions_data)
        self.stdout.write(f"📦 Transactions per run: {transactions_per_run}")

        # Ensure genesis block exists before starting
        create_genesis_block()
        
        all_results = []
        for i in range(runs):
            self.stdout.write(f"\n--- Running Test {i+1} of {runs} ---")
            
            # Clean up data from previous runs to ensure a fresh start
            self._cleanup_test_data()

            # Create transaction model instances from the data
            transactions_to_process = create_transactions_from_data(transactions_data)
            
            # Start the timer and run the test
            start_time = time.time()
            integrate_transaction_batch(transactions_to_process)
            end_time = time.time()
            
            # Calculate results
            duration = end_time - start_time
            tps = transactions_per_run / duration if duration > 0 else float('inf')
            
            self.stdout.write(self.style.SUCCESS(f"✅ Run {i+1} completed in {duration:.2f} seconds."))
            self.stdout.write(f"   Transactions Per Second (TPS): {tps:.2f}")
            
            all_results.append({
                'run': i + 1,
                'duration': duration,
                'tps': tps
            })

        # Calculate and display summary statistics
        self._display_summary(all_results, transactions_per_run)

        # Save the results to a file
        self._save_results(all_results, output_file)
        
        # Final cleanup of all test data
        self._cleanup_test_data()

    def _cleanup_test_data(self):
        """
        Removes all blocks except the genesis block and their associated transactions.
        """
        self.stdout.write("🧹 Cleaning up test data...")
        # Deleting blocks will cascade and delete associated transactions
        Block.objects.filter(index__gt=0).delete()
        self.stdout.write("✅ Cleanup complete.")

    def _display_summary(self, results, transactions_per_run):
        """
        Calculates and displays the summary of all test runs.
        """
        if not results:
            self.stdout.write(self.style.WARNING("No results to display."))
            return

        tps_values = [r['tps'] for r in results]
        
        # Calculate statistics
        mean_tps = statistics.mean(tps_values)
        median_tps = statistics.median(tps_values)
        min_tps = min(tps_values)
        max_tps = max(tps_values)
        std_dev_tps = statistics.stdev(tps_values) if len(tps_values) > 1 else 0

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("📊 Throughput Test Summary"))
        self.stdout.write("="*50)
        self.stdout.write(f"Transactions per run: {transactions_per_run}")
        self.stdout.write(f"Mean TPS: {mean_tps:.2f}")
        self.stdout.write(f"Median TPS: {median_tps:.2f}")
        self.stdout.write(f"Min TPS: {min_tps:.2f}")
        self.stdout.write(f"Max TPS: {max_tps:.2f}")
        self.stdout.write(f"Standard Deviation: {std_dev_tps:.2f}")
        self.stdout.write("="*50)
    
    def _save_results(self, results, output_file):
        """
        Saves the collected results to a JSON file.
        """
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
        self.stdout.write(f"💾 Results saved to '{output_file}'") 