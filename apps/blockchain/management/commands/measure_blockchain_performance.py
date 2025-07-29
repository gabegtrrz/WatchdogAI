"""
Blockchain Performance Measurement Command

Purpose: Measures the performance of the blockchain integration process,
specifically the `integrate_transactions_atomic` method.

This command is configurable via a YAML file to specify test runs,
transaction data, and other parameters.
"""

import logging
import time
import json
import yaml
import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.core.serializers.json import DjangoJSONEncoder
import datetime

from apps.blockchain.integration import BlockchainIntegrationService
from apps.core.models import Transaction
from apps.blockchain.models import Block
from apps.transaction_management.services import process_transaction_csv, create_transactions_from_data

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle datetime objects.
    """
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)


class Command(BaseCommand):
    """
    Django command to measure blockchain integration performance.
    """
    help = "Measures the performance of the blockchain integration process."

    def add_arguments(self, parser):
        """
        Adds command-line arguments.
        """
        parser.add_argument(
            '--config',
            type=str,
            default='evaluation/blockchain/performance_test_config.yml',
            help='Path to the YAML configuration file for the performance test.'
        )

    def handle(self, *args, **options):
        """
        Main entry point for the command.
        """
        config_path = options['config']
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Configuration file not found at: {config_path}"))
            return

        self.stdout.write(self.style.SUCCESS("Starting blockchain performance test..."))
        self._run_performance_test(config)
        self.stdout.write(self.style.SUCCESS("Blockchain performance test finished."))

    def _run_performance_test(self, config):
        """
        Runs the performance test based on the provided configuration.
        """
        test_runs = config.get('test_runs', 1)
        cleanup_after_test = config.get('cleanup_after_test', True)
        output_path = config.get('output_path', 'performance_results.json')
        transaction_data_paths = config.get('transaction_data_paths', [])

        results = []

        for data_path in transaction_data_paths:
            self.stdout.write(f"Testing with data from: {data_path}")

            try:
                with open(data_path, 'rb') as f:
                    valid_data, validation_errors = process_transaction_csv(f)
                
                if validation_errors:
                    self.stdout.write(self.style.ERROR(f"Validation errors in {data_path}:"))
                    for error in validation_errors:
                        self.stdout.write(str(error))
                    continue

            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f"Transaction data file not found: {data_path}"))
                continue

            if not valid_data:
                self.stdout.write(self.style.WARNING(f"No valid transactions loaded from {data_path}, skipping."))
                continue

            num_transactions = len(valid_data)
            
            for i in range(test_runs):
                self.stdout.write(f"--- Run {i+1}/{test_runs} for {data_path} ---")

                if cleanup_after_test:
                    self._cleanup_data()
                
                created_transactions = create_transactions_from_data(valid_data)


                service = BlockchainIntegrationService(stdout=self.stdout)
                
                start_time = time.time()
                result = service.integrate_transactions_atomic(created_transactions)
                end_time = time.time()
                
                total_time = end_time - start_time
                throughput = num_transactions / total_time if total_time > 0 else 0

                run_result = {
                    'run': i + 1,
                    'data_path': data_path,
                    'num_transactions': num_transactions,
                    'total_time_seconds': total_time,
                    'transactions_per_second': throughput,
                    'integration_details': result
                }

                results.append(run_result)
                
                self.stdout.write(f"Total time: {total_time:.4f} seconds")
                self.stdout.write(f"Throughput: {throughput:.2f} transactions/sec")
                
                if 'timing' in result:
                    self.stdout.write(json.dumps(result['timing'], indent=4, cls=DateTimeEncoder))


        self._save_results(results, output_path)

    def _cleanup_data(self):
        """
        Cleans up data created during the test.
        """
        self.stdout.write("Cleaning up test data...")
        with db_transaction.atomic():
            Transaction.objects.all().delete()
            Block.objects.all().delete()
        self.stdout.write("Cleanup complete.")

    def _save_results(self, results, output_path):
        """
        Saves the performance test results to a JSON file.
        If the file already exists, new results will be prepended.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        existing_results = []
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r') as f:
                    # handle empty file
                    content = f.read()
                    if content:
                        existing_results = json.loads(content)
                        if not isinstance(existing_results, list):
                            self.stdout.write(self.style.WARNING(f"Existing results file {output_path} is not a list. Overwriting."))
                            existing_results = []
            except json.JSONDecodeError:
                self.stdout.write(self.style.WARNING(f"Could not decode existing results from {output_path}. Overwriting."))
                existing_results = []
        
        combined_results = results + existing_results

        with open(output_path, 'w') as f:
            json.dump(combined_results, f, indent=4, cls=DateTimeEncoder)
        self.stdout.write(self.style.SUCCESS(f"Results saved to {output_path}"))