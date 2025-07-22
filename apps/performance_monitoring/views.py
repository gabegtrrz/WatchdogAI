"""
Performance monitoring views for displaying resource usage and performance metrics.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import PerformanceMetric, PerformanceAlert, ResourceUsage
from .services import get_performance_summary, get_resource_summary, performance_monitor


@login_required
def performance_dashboard(request):
    """
    Dashboard view for displaying performance metrics and resource usage.
    """
    # Get time range from request (default to 24 hours)
    hours = int(request.GET.get('hours', 24))
    
    # Get performance summary
    performance_data = get_performance_summary(hours)
    
    # Get resource usage summary
    resource_data = get_resource_summary(hours)
    
    # Get recent alerts
    recent_alerts = performance_monitor.get_recent_alerts(hours=24, severity='high')
    
    # Get recent resource usage records
    recent_usage = ResourceUsage.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=hours)
    ).order_by('-created_at')[:10]
    
    context = {
        'performance_data': performance_data,
        'resource_data': resource_data,
        'recent_alerts': recent_alerts,
        'recent_usage': recent_usage,
        'hours': hours,
        'time_ranges': [1, 6, 24, 72, 168]  # 1h, 6h, 24h, 3d, 1w
    }
    
    return render(request, 'performance_monitoring/dashboard.html', context)


@login_required
def resource_usage_detail(request, session_id):
    """
    Detailed view for a specific resource usage session.
    """
    try:
        resource_record = ResourceUsage.objects.get(session_id=session_id)
        
        # Get related performance metrics
        related_metrics = PerformanceMetric.objects.filter(
            session_id=session_id
        ).order_by('-created_at')
        
        context = {
            'resource_record': resource_record,
            'related_metrics': related_metrics,
        }
        
        return render(request, 'performance_monitoring/resource_detail.html', context)
        
    except ResourceUsage.DoesNotExist:
        return render(request, 'performance_monitoring/not_found.html', {
            'message': f'Resource usage session {session_id} not found.'
        })


@login_required
def performance_api(request):
    """
    API endpoint for performance data (for AJAX requests).
    """
    hours = int(request.GET.get('hours', 24))
    
    try:
        performance_data = get_performance_summary(hours)
        resource_data = get_resource_summary(hours)
        
        return JsonResponse({
            'success': True,
            'performance': performance_data,
            'resource': resource_data,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def alerts_view(request):
    """
    View for displaying performance alerts.
    """
    hours = int(request.GET.get('hours', 24))
    severity = request.GET.get('severity')
    
    alerts = performance_monitor.get_recent_alerts(hours=hours, severity=severity)
    
    context = {
        'alerts': alerts,
        'hours': hours,
        'severity': severity,
        'severity_choices': ['low', 'medium', 'high', 'critical']
    }
    
    return render(request, 'performance_monitoring/alerts.html', context)


@login_required
def resource_usage_list(request):
    """
    List view for resource usage records.
    """
    hours = int(request.GET.get('hours', 24))
    success_only = request.GET.get('success_only', 'false').lower() == 'true'
    
    queryset = ResourceUsage.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=hours)
    )
    
    if success_only:
        queryset = queryset.filter(overall_success=True)
    
    resource_records = queryset.order_by('-created_at')[:50]
    
    context = {
        'resource_records': resource_records,
        'hours': hours,
        'success_only': success_only,
        'total_count': queryset.count()
    }
    
    return render(request, 'performance_monitoring/resource_list.html', context) 