"""
Management command to test performance monitoring functionality.

This command allows testing the performance monitoring system
by simulating analysis pipeline steps and verifying metrics are saved.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import time
import json
import os
from apps.performance_monitoring.services import PerformanceMonitor


class Command(BaseCommand):
    help = 'Test performance monitoring functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-id',
            type=str,
            default='test-run-123',
            help='Test analysis run ID'
        )
        parser.add_argument(
            '--steps',
            type=int,
            default=5,
            help='Number of test steps to simulate'
        )

    def handle(self, *args, **options):
        run_id = options['run_id']
        num_steps = options['steps']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting performance monitoring test for run: {run_id}')
        )
        
        # Check if monitoring is enabled
        enabled = getattr(settings, 'ENABLE_PERFORMANCE_MONITORING', True)
        log_path = getattr(settings, 'PERFORMANCE_LOG_PATH', 'logs/performance_metrics.json')
        
        self.stdout.write(f'Performance monitoring enabled: {enabled}')
        self.stdout.write(f'Log path: {log_path}')
        
        if not enabled:
            self.stdout.write(
                self.style.WARNING('Performance monitoring is disabled. Enable it in settings to test.')
            )
            return
        
        # Create performance monitor
        monitor = PerformanceMonitor(run_id)
        monitor.start_analysis()
        
        # Simulate analysis steps
        step_names = [
            'data_conversion',
            'data_preprocessing', 
            'feature_engineering',
            'model_refitting',
            'anomaly_detection',
            'shap_analysis',
            'database_save'
        ]
        
        for i in range(min(num_steps, len(step_names))):
            step_name = step_names[i]
            self.stdout.write(f'Simulating step: {step_name}')
            
            monitor.start_step(step_name)
            
            # Simulate work
            time.sleep(0.1)  # 100ms
            
            duration = monitor.end_step(step_name)
            self.stdout.write(f'  Completed in {duration:.3f}s')
        
        # End analysis with test metrics
        metrics = monitor.end_analysis({
            'transactions_analyzed': 100,
            'anomalies_found': 5,
            'contamination_rate': 0.05,
            'status': 'success',
            'test_run': True
        })
        
        self.stdout.write(
            self.style.SUCCESS(f'Analysis completed in {metrics.get("total_analysis_time", 0):.3f}s')
        )
        
        # Verify metrics were saved
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list) and len(data) > 0:
                    latest_metrics = data[0]  # First entry (most recent)
                    
                    if latest_metrics.get('analysis_run_id') == run_id:
                        self.stdout.write(
                            self.style.SUCCESS('✓ Performance metrics saved successfully')
                        )
                        self.stdout.write(f'  Total time: {latest_metrics.get("total_analysis_time", 0):.3f}s')
                        self.stdout.write(f'  Steps recorded: {latest_metrics.get("total_steps", 0)}')
                        self.stdout.write(f'  Status: {latest_metrics.get("status", "unknown")}')
                    else:
                        self.stdout.write(
                            self.style.ERROR('✗ Metrics saved but run ID mismatch')
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR('✗ No metrics found in log file')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error reading metrics file: {e}')
                )
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ Metrics file not found at {log_path}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Performance monitoring test completed')
        ) 