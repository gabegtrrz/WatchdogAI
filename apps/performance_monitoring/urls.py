"""
URL patterns for performance monitoring API endpoints.
"""

from django.urls import path
from . import views

app_name = 'performance_monitoring'

urlpatterns = [
    # Performance summary for all operations
    path('api/performance/summary/', views.performance_summary, name='performance_summary'),
    
    # Metrics for specific operation type
    path('api/performance/operation/<str:operation_type>/', views.operation_metrics, name='operation_metrics'),
    
    # Performance alerts
    path('api/performance/alerts/', views.performance_alerts, name='performance_alerts'),
    
    # End-to-end performance metrics
    path('api/performance/end-to-end/', views.end_to_end_performance, name='end_to_end_performance'),
    
    # Comprehensive dashboard data
    path('api/performance/dashboard/', views.performance_dashboard, name='performance_dashboard'),
] 