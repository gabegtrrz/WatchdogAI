"""
Management command to view performance metrics.

Usage:
    python manage.py view_performance [--hours 24] [--operation-type blockchain_save]
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from apps.performance_monitoring.models import PerformanceMetric, PerformanceAlert
from apps.performance_monitoring.services import performance_monitor


class Command(BaseCommand):
    """
    Command to view performance metrics and alerts.
    
    **Features:**
    - Display performance summary for all operations
    - Show recent alerts and their severity
    - Filter by operation type and time range
    - Export data in various formats
    """
    
    help = 'View performance metrics and alerts'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to look back (default: 24)'
        )
        
        parser.add_argument(
            '--operation-type',
            type=str,
            choices=[choice[0] for choice in PerformanceMetric.OPERATION_CHOICES],
            help='Filter by specific operation type'
        )
        
        parser.add_argument(
            '--show-alerts',
            action='store_true',
            help='Show performance alerts'
        )
        
        parser.add_argument(
            '--severity',
            type=str,
            choices=['low', 'medium', 'high', 'critical'],
            help='Filter alerts by severity level'
        )
        
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json', 'csv'],
            default='table',
            help='Output format (default: table)'
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        hours = options['hours']
        operation_type = options['operation_type']
        show_alerts = options['show_alerts']
        severity = options['severity']
        output_format = options['format']
        
        self.stdout.write(
            self.style.SUCCESS(f'Performance Metrics Report (Last {hours} hours)')
        )
        self.stdout.write('=' * 60)
        
        # Get performance summary
        if operation_type:
            self._show_single_operation(operation_type, hours, output_format)
        else:
            self._show_performance_summary(hours, output_format)
        
        # Show alerts if requested
        if show_alerts:
            self.stdout.write('\n' + '=' * 60)
            self._show_alerts(hours, severity, output_format)
    
    def _show_single_operation(self, operation_type, hours, output_format):
        """Show metrics for a single operation type."""
        avg_time = PerformanceMetric.get_average_time(operation_type, hours)
        
        if output_format == 'json':
            import json
            data = {
                'operation_type': operation_type,
                'average_time_ms': avg_time,
                'hours': hours
            }
            self.stdout.write(json.dumps(data, indent=2))
        else:
            self.stdout.write(f'Operation: {operation_type}')
            self.stdout.write(f'Average Time: {avg_time:.2f}ms')
            self.stdout.write(f'Time Range: Last {hours} hours')
    
    def _show_performance_summary(self, hours, output_format):
        """Show performance summary for all operations."""
        summary = PerformanceMetric.get_performance_summary(hours)
        
        if output_format == 'json':
            import json
            self.stdout.write(json.dumps(summary, indent=2))
        elif output_format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Operation Type', 'Average Time (ms)', 'Min Time (ms)', 
                'Max Time (ms)', 'Total Operations', 'Success Rate (%)'
            ])
            
            # Write data
            for op_type, stats in summary.items():
                writer.writerow([
                    op_type,
                    f"{stats['average_time_ms']:.2f}",
                    f"{stats['min_time_ms']:.2f}",
                    f"{stats['max_time_ms']:.2f}",
                    stats['total_operations'],
                    f"{stats['success_rate']:.1f}"
                ])
            
            self.stdout.write(output.getvalue())
        else:
            # Table format
            self.stdout.write(f"{'Operation':<25} {'Avg (ms)':<10} {'Min (ms)':<10} {'Max (ms)':<10} {'Count':<8} {'Success %':<10}")
            self.stdout.write('-' * 80)
            
            for op_type, stats in summary.items():
                self.stdout.write(
                    f"{op_type:<25} "
                    f"{stats['average_time_ms']:<10.2f} "
                    f"{stats['min_time_ms']:<10.2f} "
                    f"{stats['max_time_ms']:<10.2f} "
                    f"{stats['total_operations']:<8} "
                    f"{stats['success_rate']:<10.1f}"
                )
    
    def _show_alerts(self, hours, severity, output_format):
        """Show performance alerts."""
        alerts = performance_monitor.get_recent_alerts(hours, severity)
        
        if not alerts:
            self.stdout.write(self.style.WARNING('No alerts found in the specified time range.'))
            return
        
        self.stdout.write(f'Performance Alerts (Last {hours} hours)')
        
        if output_format == 'json':
            import json
            alert_data = []
            for alert in alerts:
                alert_data.append({
                    'operation_type': alert.operation_type,
                    'severity': alert.severity,
                    'threshold_ms': alert.threshold_ms,
                    'actual_time_ms': alert.actual_time_ms,
                    'message': alert.message,
                    'created_at': alert.created_at.isoformat(),
                    'resolved': alert.resolved
                })
            self.stdout.write(json.dumps(alert_data, indent=2))
        else:
            # Table format
            self.stdout.write(f"{'Operation':<20} {'Severity':<10} {'Threshold':<10} {'Actual':<10} {'Ratio':<8} {'Resolved':<10}")
            self.stdout.write('-' * 80)
            
            for alert in alerts:
                ratio = alert.actual_time_ms / alert.threshold_ms
                resolved_status = 'Yes' if alert.resolved else 'No'
                
                # Color code severity
                severity_color = {
                    'critical': self.style.ERROR,
                    'high': self.style.WARNING,
                    'medium': self.style.NOTICE,
                    'low': self.style.SUCCESS
                }.get(alert.severity, str)
                
                self.stdout.write(
                    f"{alert.operation_type:<20} "
                    f"{severity_color(alert.severity.upper()):<10} "
                    f"{alert.threshold_ms:<10.2f} "
                    f"{alert.actual_time_ms:<10.2f} "
                    f"{ratio:<8.1f}x "
                    f"{resolved_status:<10}"
                ) 