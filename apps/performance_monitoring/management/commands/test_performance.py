"""
Management command to test performance monitoring functionality.

Usage:
    python manage.py test_performance
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import time
import random

from apps.performance_monitoring.services import track_performance, performance_monitor


class Command(BaseCommand):
    """
    Test command for performance monitoring.
    
    **Purpose:** Verify that performance monitoring is working correctly
    by creating test metrics and checking the system.
    """
    
    help = 'Test performance monitoring functionality'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--operation-type',
            type=str,
            default='single_transaction_upload',
            help='Type of operation to test'
        )
        
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of test operations to run'
        )
    
    def handle(self, *args, **options):
        """Execute the test command."""
        operation_type = options['operation_type']
        count = options['count']
        
        self.stdout.write(
            self.style.SUCCESS(f'Testing performance monitoring with {count} {operation_type} operations...')
        )
        
        # Test the decorator
        for i in range(count):
            # Simulate varying execution times
            execution_time = random.uniform(1.0, 10.0)  # 1-10 seconds
            
            @track_performance(operation_type, transaction_count=1)
            def test_function():
                time.sleep(execution_time)
                if random.choice([True, True, True, False]):  # 75% success rate
                    return True
                else:
                    raise Exception("Test error")
            
            try:
                test_function()
                self.stdout.write(f'  Test {i+1}: {execution_time:.2f}s ({operation_type}) - SUCCESS')
            except Exception:
                self.stdout.write(f'  Test {i+1}: {execution_time:.2f}s ({operation_type}) - FAILED')
        
        # Show results
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Performance Test Results:')
        self.stdout.write('=' * 50)
        
        # Get average time
        avg_time = performance_monitor.get_average_time(operation_type, hours=1)
        self.stdout.write(f'Average time for {operation_type}: {avg_time:.2f}ms')
        
        # Get performance summary
        summary = performance_monitor.get_performance_summary(hours=1)
        if operation_type in summary:
            stats = summary[operation_type]
            self.stdout.write(f'Total operations: {stats["total_operations"]}')
            self.stdout.write(f'Success rate: {stats["success_rate"]:.1f}%')
            self.stdout.write(f'Min time: {stats["min_time_ms"]:.2f}ms')
            self.stdout.write(f'Max time: {stats["max_time_ms"]:.2f}ms')
        
        # Get recent alerts
        alerts = performance_monitor.get_recent_alerts(hours=1)
        if alerts:
            self.stdout.write(f'\nRecent alerts: {len(alerts)}')
            for alert in alerts[:3]:  # Show first 3 alerts
                self.stdout.write(f'  - {alert.operation_type}: {alert.actual_time_ms:.2f}ms > {alert.threshold_ms:.2f}ms ({alert.severity})')
        else:
            self.stdout.write('\nNo alerts generated')
        
        self.stdout.write(
            self.style.SUCCESS('\nPerformance monitoring test completed successfully!')
        ) 