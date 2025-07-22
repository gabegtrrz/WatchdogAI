"""
Management command to view resource usage statistics.

Usage:
    python manage.py view_resource_usage [--hours 24] [--format table|json|csv]
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import json
import csv
from io import StringIO

from apps.performance_monitoring.models import ResourceUsage, PerformanceMetric
from apps.performance_monitoring.services import get_resource_summary, get_performance_summary


class Command(BaseCommand):
    help = 'View resource usage statistics for transaction processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to look back (default: 24)'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'csv'],
            default='table',
            help='Output format (default: table)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed breakdown by stage'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        output_format = options['format']
        detailed = options['detailed']

        try:
            # Get resource summary
            resource_summary = get_resource_summary(hours)
            performance_summary = get_performance_summary(hours)

            if output_format == 'json':
                self.output_json(resource_summary, performance_summary)
            elif output_format == 'csv':
                self.output_csv(resource_summary, performance_summary, hours)
            else:
                self.output_table(resource_summary, performance_summary, hours, detailed)

        except Exception as e:
            raise CommandError(f'Error generating resource usage report: {e}')

    def output_json(self, resource_summary, performance_summary):
        """Output data in JSON format."""
        data = {
            'resource_summary': resource_summary,
            'performance_summary': performance_summary,
            'timestamp': timezone.now().isoformat()
        }
        self.stdout.write(json.dumps(data, indent=2))

    def output_csv(self, resource_summary, performance_summary, hours):
        """Output data in CSV format."""
        output = StringIO()
        writer = csv.writer(output)

        # Write resource summary
        writer.writerow(['Resource Usage Summary'])
        writer.writerow(['Metric', 'Value'])
        for key, value in resource_summary.items():
            writer.writerow([key, value])

        writer.writerow([])
        writer.writerow(['Performance Summary'])
        writer.writerow(['Operation', 'Avg Time (ms)', 'Success Rate (%)', 'Total Operations'])
        
        for operation, stats in performance_summary.items():
            if stats['total_operations'] > 0:
                writer.writerow([
                    operation,
                    stats['average_time_ms'],
                    stats['success_rate'],
                    stats['total_operations']
                ])

        self.stdout.write(output.getvalue())

    def output_table(self, resource_summary, performance_summary, hours, detailed):
        """Output data in formatted table."""
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"RESOURCE USAGE REPORT (Last {hours} hours)")
        self.stdout.write(f"{'='*60}\n")

        # Resource Summary
        self.stdout.write("RESOURCE SUMMARY:")
        self.stdout.write("-" * 40)
        self.stdout.write(f"Total Sessions: {resource_summary['total_sessions']}")
        self.stdout.write(f"Total Transactions: {resource_summary['total_transactions']}")
        self.stdout.write(f"Success Rate: {resource_summary['success_rate']:.1f}%")
        self.stdout.write(f"Average Processing Time: {resource_summary['average_processing_time_ms']:.1f}ms")
        self.stdout.write(f"Average CPU Usage: {resource_summary['average_cpu_usage']:.1f}%")
        self.stdout.write(f"Average Memory Usage: {resource_summary['average_memory_usage_mb']:.1f}MB")
        self.stdout.write(f"Total Database Queries: {resource_summary['total_database_queries']}")
        self.stdout.write(f"Total Network Requests: {resource_summary['total_network_requests']}")
        self.stdout.write(f"Average Database Time: {resource_summary.get('average_database_time_ms', 0.0):.1f}ms")
        self.stdout.write(f"Average Network Time: {resource_summary.get('average_network_time_ms', 0.0):.1f}ms")

        # Performance Summary
        self.stdout.write(f"\nPERFORMANCE SUMMARY:")
        self.stdout.write("-" * 40)
        for operation, stats in performance_summary.items():
            if stats['total_operations'] > 0:
                self.stdout.write(f"{operation.replace('_', ' ').title()}:")
                self.stdout.write(f"  Avg Time: {stats['average_time_ms']:.1f}ms")
                self.stdout.write(f"  Success Rate: {stats['success_rate']:.1f}%")
                self.stdout.write(f"  Total Operations: {stats['total_operations']}")
                self.stdout.write()

        if detailed:
            self.output_detailed_breakdown(hours)

    def output_detailed_breakdown(self, hours):
        """Output detailed breakdown by processing stage."""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Get recent resource usage records
        recent_usage = ResourceUsage.objects.filter(
            created_at__gte=cutoff_time
        ).order_by('-created_at')[:10]

        if recent_usage:
            self.stdout.write(f"\nRECENT SESSIONS (Last {hours} hours):")
            self.stdout.write("-" * 60)
            
            for usage in recent_usage:
                self.stdout.write(f"\nSession: {usage.session_id}")
                self.stdout.write(f"  Transactions: {usage.transaction_count}")
                self.stdout.write(f"  Total Time: {usage.total_processing_time_ms:.1f}ms")
                self.stdout.write(f"  CPU Usage: {usage.cpu_usage_percent:.1f}%")
                self.stdout.write(f"  Memory: {usage.memory_usage_mb:.1f}MB")
                self.stdout.write(f"  DB Queries: {usage.database_queries_count}")
                self.stdout.write(f"  Network Requests: {usage.network_requests_count}")
                self.stdout.write(f"  Status: {'SUCCESS' if usage.overall_success else 'FAILED'}")
                
                if usage.upload_time_ms > 0:
                    self.stdout.write(f"  Upload Time: {usage.upload_time_ms:.1f}ms")
                if usage.preprocessing_time_ms > 0:
                    self.stdout.write(f"  Preprocessing Time: {usage.preprocessing_time_ms:.1f}ms")
                if usage.enrichment_time_ms > 0:
                    self.stdout.write(f"  Enrichment Time: {usage.enrichment_time_ms:.1f}ms")
                if usage.blockchain_integration_time_ms > 0:
                    self.stdout.write(f"  Blockchain Time: {usage.blockchain_integration_time_ms:.1f}ms")
                
                if usage.error_message:
                    self.stdout.write(f"  Error: {usage.error_message}")

        # Performance alerts
        from apps.performance_monitoring.services import performance_monitor
        recent_alerts = performance_monitor.get_recent_alerts(hours=hours, severity='high')
        
        if recent_alerts:
            self.stdout.write(f"\nRECENT ALERTS (Last {hours} hours):")
            self.stdout.write("-" * 60)
            
            for alert in recent_alerts:
                self.stdout.write(f"\n{alert.operation_type.replace('_', ' ').title()}:")
                self.stdout.write(f"  Severity: {alert.severity.upper()}")
                self.stdout.write(f"  Threshold: {alert.threshold_ms:.1f}ms")
                self.stdout.write(f"  Actual Time: {alert.actual_time_ms:.1f}ms")
                self.stdout.write(f"  Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                self.stdout.write(f"  Message: {alert.message}")

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("Report generated successfully!")
        self.stdout.write(f"{'='*60}\n") 