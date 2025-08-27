"""
Tests for performance monitoring functionality.
"""

from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
import json

from .models import PerformanceMetric, PerformanceAlert
from .services import performance_monitor


class PerformanceMonitoringTestCase(TestCase):
    """Test cases for performance monitoring functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create some test metrics
        PerformanceMetric.objects.create(
            operation_type='blockchain_save',
            execution_time_ms=1500.0,
            transaction_count=5,
            success=True
        )
        
        PerformanceMetric.objects.create(
            operation_type='anomaly_detection',
            execution_time_ms=25000.0,
            transaction_count=10,
            success=True
        )
        
        # Create a test alert
        PerformanceAlert.objects.create(
            operation_type='blockchain_save',
            threshold_ms=5000.0,
            actual_time_ms=12000.0,
            severity='high',
            message='Test alert'
        )
    
    def test_performance_metric_creation(self):
        """Test that performance metrics can be created."""
        metric = PerformanceMetric.objects.create(
            operation_type='blockchain_save',
            execution_time_ms=2000.0,
            transaction_count=3,
            success=True
        )
        
        self.assertEqual(metric.operation_type, 'blockchain_save')
        self.assertEqual(metric.execution_time_ms, 2000.0)
        self.assertTrue(metric.success)
    
    def test_get_average_time(self):
        """Test getting average execution time."""
        avg_time = PerformanceMetric.get_average_time('blockchain_save', 24)
        self.assertEqual(avg_time, 1500.0)
    
    def test_get_performance_summary(self):
        """Test getting performance summary."""
        summary = PerformanceMetric.get_performance_summary(24)
        
        self.assertIn('blockchain_save', summary)
        self.assertIn('anomaly_detection', summary)
        
        blockchain_stats = summary['blockchain_save']
        self.assertEqual(blockchain_stats['average_time_ms'], 1500.0)
        self.assertEqual(blockchain_stats['total_operations'], 1)
        self.assertEqual(blockchain_stats['successful_operations'], 1)
        self.assertEqual(blockchain_stats['success_rate'], 100.0)
    
    def test_performance_summary_api(self):
        """Test performance summary API endpoint."""
        response = self.client.get('/performance/api/performance/summary/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'success')
        self.assertIn('summary', data)
        self.assertIn('blockchain_save', data['summary'])
    
    def test_operation_metrics_api(self):
        """Test operation metrics API endpoint."""
        response = self.client.get('/performance/api/performance/operation/blockchain_save/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['operation_type'], 'blockchain_save')
        self.assertEqual(data['average_time_ms'], 1500.0)
    
    def test_performance_alerts_api(self):
        """Test performance alerts API endpoint."""
        response = self.client.get('/performance/api/performance/alerts/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'success')
        self.assertIn('alerts', data)
        self.assertEqual(len(data['alerts']), 1)
        self.assertEqual(data['alerts'][0]['operation_type'], 'blockchain_save')
    
    def test_performance_dashboard_api(self):
        """Test performance dashboard API endpoint."""
        response = self.client.get('/performance/api/performance/dashboard/')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'success')
        self.assertIn('summary', data)
        self.assertIn('alerts', data)
        self.assertIn('top_slow_operations', data)
    
    def test_invalid_operation_type(self):
        """Test API with invalid operation type."""
        response = self.client.get('/performance/api/performance/operation/invalid_operation/')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_invalid_hours_parameter(self):
        """Test API with invalid hours parameter."""
        response = self.client.get('/performance/api/performance/summary/?hours=-1')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_performance_monitor_service(self):
        """Test performance monitor service methods."""
        # Test getting average time
        avg_time = performance_monitor.get_average_time('blockchain_save', 24)
        self.assertEqual(avg_time, 1500.0)
        
        # Test getting performance summary
        summary = performance_monitor.get_performance_summary(24)
        self.assertIn('blockchain_save', summary)
        
        # Test getting alerts
        alerts = performance_monitor.get_recent_alerts(24)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].operation_type, 'blockchain_save')
    
    def test_alert_creation(self):
        """Test that alerts are created for threshold violations."""
        # Create a metric that exceeds threshold
        PerformanceMetric.objects.create(
            operation_type='blockchain_save',
            execution_time_ms=10000.0,  # Exceeds 5 second threshold
            transaction_count=1,
            success=True
        )
        
        # Check that alert was created
        alerts = PerformanceAlert.objects.filter(
            operation_type='blockchain_save',
            actual_time_ms=10000.0
        )
        self.assertTrue(alerts.exists())
        
        alert = alerts.first()
        self.assertEqual(alert.threshold_ms, 5000.0)
        self.assertEqual(alert.severity, 'high')  # 2x threshold = high severity 