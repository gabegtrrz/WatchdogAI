"""
Management command to test scraping performance.

This command tests how long it takes to scrape 1 price by running
the scraping process 3 times and measuring performance metrics.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import time
from apps.data_augmentation.services import scrape_amazon_prices


class Command(BaseCommand):
    help = 'Test scraping performance by running 3 scraping attempts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            type=str,
            default='laptop',
            help='Product name to test scraping (default: laptop)'
        )
        parser.add_argument(
            '--retries',
            type=int,
            default=1,
            help='Number of retries per attempt (default: 1)'
        )

    def handle(self, *args, **options):
        product_name = options['product']
        retries = options['retries']
        
        self.stdout.write(
            self.style.SUCCESS(f'Testing scraping performance for "{product_name}"')
        )
        self.stdout.write(f'Number of retries per attempt: {retries}')
        self.stdout.write(f'Price scraping enabled: {getattr(settings, "ENABLE_PRICE_SCRAPING", False)}')
        self.stdout.write('=' * 60)
        
        if not getattr(settings, 'ENABLE_PRICE_SCRAPING', False):
            self.stdout.write(
                self.style.WARNING('Price scraping is disabled. Enable it in settings to test.')
            )
            return
        
        results = []
        
        for i in range(3):
            self.stdout.write(f'\nTest {i+1}/3:')
            self.stdout.write(f'Starting scraping for "{product_name}"...')
            
            start_time = time.time()
            
            try:
                prices = scrape_amazon_prices(product_name, retries=retries)
                
                end_time = time.time()
                duration = end_time - start_time
                
                if prices:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Success! Found {len(prices)} prices in {duration:.2f}s')
                    )
                    self.stdout.write(f'  Prices: {prices}')
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠ No prices found in {duration:.2f}s')
                    )
                
                results.append({
                    'test_number': i + 1,
                    'duration': duration,
                    'prices_found': len(prices),
                    'success': len(prices) > 0
                })
                
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                
                self.stdout.write(
                    self.style.ERROR(f'✗ Error after {duration:.2f}s: {e}')
                )
                
                results.append({
                    'test_number': i + 1,
                    'duration': duration,
                    'prices_found': 0,
                    'success': False,
                    'error': str(e)
                })
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('PERFORMANCE SUMMARY'))
        self.stdout.write('=' * 60)
        
        successful_tests = [r for r in results if r['success']]
        failed_tests = [r for r in results if not r['success']]
        
        if successful_tests:
            avg_duration = sum(r['duration'] for r in successful_tests) / len(successful_tests)
            min_duration = min(r['duration'] for r in successful_tests)
            max_duration = max(r['duration'] for r in successful_tests)
            
            self.stdout.write(f'Successful tests: {len(successful_tests)}/3')
            self.stdout.write(f'Average duration: {avg_duration:.2f}s')
            self.stdout.write(f'Min duration: {min_duration:.2f}s')
            self.stdout.write(f'Max duration: {max_duration:.2f}s')
        else:
            self.stdout.write(self.style.ERROR('No successful tests'))
        
        if failed_tests:
            self.stdout.write(f'Failed tests: {len(failed_tests)}/3')
            for test in failed_tests:
                self.stdout.write(f'  Test {test["test_number"]}: {test["duration"]:.2f}s - {test.get("error", "No prices found")}')
        
        # Check performance metrics file
        log_path = getattr(settings, 'PERFORMANCE_LOG_PATH', 'logs/performance_monitoring/performance_metrics.json')
        self.stdout.write(f'\nPerformance metrics saved to: {log_path}')
        
        try:
            import json
            import os
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Find scraping-related entries
                scraping_entries = [entry for entry in data if 'scrape-amazon' in entry.get('analysis_run_id', '')]
                
                if scraping_entries:
                    self.stdout.write(f'Found {len(scraping_entries)} scraping performance entries in log file')
                    latest = scraping_entries[0]  # Most recent
                    self.stdout.write(f'Latest scraping time: {latest.get("total_analysis_time", 0):.2f}s')
                    self.stdout.write(f'Latest status: {latest.get("status", "unknown")}')
                else:
                    self.stdout.write('No scraping performance entries found in log file')
            else:
                self.stdout.write('Performance log file not found')
                
        except Exception as e:
            self.stdout.write(f'Error reading performance log: {e}')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Scraping performance test completed!')) 