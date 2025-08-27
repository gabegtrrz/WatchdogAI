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
] 