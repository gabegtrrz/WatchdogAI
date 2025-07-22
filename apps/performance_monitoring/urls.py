"""
URL patterns for performance monitoring app.
"""

from django.urls import path
from . import views

app_name = 'performance_monitoring'

urlpatterns = [
    # Dashboard and overview
    path('dashboard/', views.performance_dashboard, name='dashboard'),
    path('api/', views.performance_api, name='api'),
    
    # Resource usage views
    path('resource/<str:session_id>/', views.resource_usage_detail, name='resource_detail'),
    path('resource/list/', views.resource_usage_list, name='resource_list'),
    
    # Alerts
    path('alerts/', views.alerts_view, name='alerts'),
] 