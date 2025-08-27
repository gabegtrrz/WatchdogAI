"""
Performance monitoring models for tracking execution times
of critical operations like blockchain saves and anomaly detection.
"""

from django.db import models
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class PerformanceMetric(models.Model):
    """
    Stores performance metrics for various operations.
    
    **Purpose:** Track execution times for critical operations
    to identify performance bottlenecks and monitor system health.
    """
    
    OPERATION_CHOICES = [
        ('blockchain_save', 'Blockchain Transaction Save'),
        ('anomaly_detection', 'Anomaly Detection Analysis'),
        ('transaction_upload', 'Transaction Upload'),
        ('data_preprocessing', 'Data Preprocessing'),
        ('feature_engineering', 'Feature Engineering'),
        ('model_prediction', 'Model Prediction'),
        ('end_to_end_upload', 'End-to-End Transaction Upload'),
        ('single_transaction_upload', 'Single Transaction Upload'),
        ('csv_batch_upload', 'CSV Batch Upload'),
    ]
    
    # Core fields
    operation_type = models.CharField(
        max_length=50, 
        choices=OPERATION_CHOICES,
        help_text="Type of operation being measured"
    )
    execution_time_ms = models.FloatField(
        help_text="Execution time in milliseconds"
    )
    transaction_count = models.IntegerField(
        default=1,
        help_text="Number of transactions processed in this operation"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this metric was recorded"
    )
    success = models.BooleanField(
        default=True,
        help_text="Whether the operation completed successfully"
    )
    error_message = models.TextField(
        blank=True, 
        null=True,
        help_text="Error message if operation failed"
    )
    
    # Additional context
    user_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="User who triggered the operation (if applicable)"
    )
    session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Session identifier for tracking user sessions"
    )
    
    class Meta:
        db_table = 'performance_metrics'
        indexes = [
            models.Index(fields=['operation_type', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['success']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        """String representation with safe formatting."""
        try:
            execution_time = float(self.execution_time_ms)
            return f"{self.operation_type} - {execution_time:.2f}ms ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"
        except (ValueError, TypeError):
            return f"{self.operation_type} - N/A ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"
    
    @classmethod
    def get_average_time(cls, operation_type, hours=24):
        """
        Get average execution time for a specific operation.
        
        Args:
            operation_type: Type of operation to average
            hours: Number of hours to look back (default: 24)
            
        Returns:
            float: Average execution time in milliseconds, or 0 if no data
        """
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        metrics = cls.objects.filter(
            operation_type=operation_type,
            created_at__gte=cutoff_time,
            success=True
        )
        
        if not metrics.exists():
            return 0.0
        
        avg_time = metrics.aggregate(
            avg_time=models.Avg('execution_time_ms')
        )['avg_time']
        
        return avg_time or 0.0
    
    @classmethod
    def get_performance_summary(cls, hours=24):
        """
        Get performance summary for all operations.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            dict: Summary of performance metrics by operation type
        """
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Avg, Count, Min, Max
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        summary = {}
        
        for operation_type, _ in cls.OPERATION_CHOICES:
            metrics = cls.objects.filter(
                operation_type=operation_type,
                created_at__gte=cutoff_time
            )
            
            if metrics.exists():
                stats = metrics.aggregate(
                    avg_time=Avg('execution_time_ms'),
                    min_time=Min('execution_time_ms'),
                    max_time=Max('execution_time_ms'),
                    total_count=Count('id'),
                    success_count=Count('id', filter=models.Q(success=True))
                )
                
                summary[operation_type] = {
                    'average_time_ms': stats['avg_time'] or 0.0,
                    'min_time_ms': stats['min_time'] or 0.0,
                    'max_time_ms': stats['max_time'] or 0.0,
                    'total_operations': stats['total_count'],
                    'successful_operations': stats['success_count'],
                    'success_rate': (stats['success_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0.0
                }
            else:
                summary[operation_type] = {
                    'average_time_ms': 0.0,
                    'min_time_ms': 0.0,
                    'max_time_ms': 0.0,
                    'total_operations': 0,
                    'successful_operations': 0,
                    'success_rate': 0.0
                }
        
        return summary


class ResourceUsage(models.Model):
    """
    Tracks detailed resource consumption during transaction processing.
    
    **Purpose:** Monitor CPU, memory, database operations, and network usage
    from transaction upload until blockchain integration completion.
    """
    
    # Core tracking fields
    session_id = models.CharField(
        max_length=100,
        help_text="Unique session identifier for tracking upload lifecycle"
    )
    transaction_count = models.IntegerField(
        default=1,
        help_text="Number of transactions being processed"
    )
    
    # Resource measurements
    cpu_usage_percent = models.FloatField(
        default=0.0,
        help_text="CPU usage percentage during processing"
    )
    memory_usage_mb = models.FloatField(
        default=0.0,
        help_text="Memory usage in megabytes"
    )
    database_queries_count = models.IntegerField(
        default=0,
        help_text="Number of database queries executed"
    )
    database_queries_time_ms = models.FloatField(
        default=0.0,
        help_text="Total time spent on database queries in milliseconds"
    )
    network_requests_count = models.IntegerField(
        default=0,
        help_text="Number of external network requests made"
    )
    network_requests_time_ms = models.FloatField(
        default=0.0,
        help_text="Total time spent on network requests in milliseconds"
    )
    
    # Processing stages
    upload_time_ms = models.FloatField(
        default=0.0,
        help_text="Time spent on file upload and validation"
    )
    preprocessing_time_ms = models.FloatField(
        default=0.0,
        help_text="Time spent on data preprocessing"
    )
    enrichment_time_ms = models.FloatField(
        default=0.0,
        help_text="Time spent on data enrichment"
    )
    blockchain_integration_time_ms = models.FloatField(
        default=0.0,
        help_text="Time spent on blockchain integration"
    )
    total_processing_time_ms = models.FloatField(
        default=0.0,
        help_text="Total end-to-end processing time"
    )
    
    # Status tracking
    upload_success = models.BooleanField(
        default=False,
        help_text="Whether upload stage completed successfully"
    )
    preprocessing_success = models.BooleanField(
        default=False,
        help_text="Whether preprocessing stage completed successfully"
    )
    enrichment_success = models.BooleanField(
        default=False,
        help_text="Whether enrichment stage completed successfully"
    )
    blockchain_success = models.BooleanField(
        default=False,
        help_text="Whether blockchain integration completed successfully"
    )
    overall_success = models.BooleanField(
        default=False,
        help_text="Whether entire process completed successfully"
    )
    
    # Error tracking
    error_stage = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Stage where error occurred (if any)"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed error message if process failed"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When resource tracking started"
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When resource tracking completed"
    )
    user_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="User who initiated the upload"
    )
    
    class Meta:
        db_table = 'resource_usage'
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['overall_success']),
            models.Index(fields=['user_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Resource Usage - Session {self.session_id} ({self.transaction_count} transactions)"
    
    @property
    def total_database_time_ms(self):
        """Total database operations time"""
        return self.database_queries_time_ms
    
    @property
    def total_network_time_ms(self):
        """Total network operations time"""
        return self.network_requests_time_ms
    
    @property
    def processing_efficiency(self):
        """Calculate processing efficiency (successful operations / total time)"""
        if self.total_processing_time_ms > 0:
            return self.transaction_count / (self.total_processing_time_ms / 1000)  # transactions per second
        return 0.0
    
    @classmethod
    def get_resource_summary(cls, hours=24):
        """
        Get resource usage summary for the specified time period.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            dict: Summary of resource usage metrics
        """
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Avg, Count, Sum, Min, Max
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        usage_data = cls.objects.filter(created_at__gte=cutoff_time)
        
        if not usage_data.exists():
            return {
                'total_sessions': 0,
                'total_transactions': 0,
                'success_rate': 0.0,
                'average_processing_time_ms': 0.0,
                'average_cpu_usage': 0.0,
                'average_memory_usage_mb': 0.0,
                'total_database_queries': 0,
                'total_network_requests': 0
            }
        
        stats = usage_data.aggregate(
            total_sessions=Count('session_id', distinct=True),
            total_transactions=Sum('transaction_count'),
            successful_sessions=Count('session_id', filter=models.Q(overall_success=True)),
            avg_processing_time=Avg('total_processing_time_ms'),
            avg_cpu_usage=Avg('cpu_usage_percent'),
            avg_memory_usage=Avg('memory_usage_mb'),
            total_db_queries=Sum('database_queries_count'),
            total_network_requests=Sum('network_requests_count'),
            avg_db_time=Avg('database_queries_time_ms'),
            avg_network_time=Avg('network_requests_time_ms')
        )
        
        total_sessions = stats['total_sessions']
        success_rate = (stats['successful_sessions'] / total_sessions * 100) if total_sessions > 0 else 0.0
        
        return {
            'total_sessions': total_sessions,
            'total_transactions': stats['total_transactions'] or 0,
            'success_rate': success_rate,
            'average_processing_time_ms': stats['avg_processing_time'] or 0.0,
            'average_cpu_usage': stats['avg_cpu_usage'] or 0.0,
            'average_memory_usage_mb': stats['avg_memory_usage'] or 0.0,
            'total_database_queries': stats['total_db_queries'] or 0,
            'total_network_requests': stats['total_network_requests'] or 0,
            'average_database_time_ms': stats['avg_db_time'] or 0.0,
            'average_network_time_ms': stats['avg_network_time'] or 0.0
        }


class PerformanceAlert(models.Model):
    """
    Stores alerts for performance issues.
    
    **Purpose:** Track when operations exceed expected thresholds
    to help identify performance degradation.
    """
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    operation_type = models.CharField(
        max_length=50,
        choices=PerformanceMetric.OPERATION_CHOICES
    )
    threshold_ms = models.FloatField(
        help_text="Threshold that was exceeded (in milliseconds)"
    )
    actual_time_ms = models.FloatField(
        help_text="Actual execution time (in milliseconds)"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='medium'
    )
    message = models.TextField(
        help_text="Alert message describing the performance issue"
    )
    created_at = models.DateTimeField(
        default=timezone.now
    )
    resolved = models.BooleanField(
        default=False,
        help_text="Whether this alert has been resolved"
    )
    
    class Meta:
        db_table = 'performance_alerts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.operation_type} Alert - {self.severity} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})" 