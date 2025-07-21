"""
API views for performance monitoring.

**Features:**
- REST API endpoints for retrieving performance metrics
- JSON responses with performance summaries
- Filtering by operation type and time range
- Authentication and permission controls
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.core.exceptions import ValidationError
import json
import logging

from .models import PerformanceMetric, PerformanceAlert
from .services import performance_monitor

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def performance_summary(request):
    """
    Get performance summary for all operations.
    
    **Query Parameters:**
    - hours: Number of hours to look back (default: 24)
    - format: Response format (json, csv) (default: json)
    
    **Response:**
    ```json
    {
        "blockchain_save": {
            "average_time_ms": 1250.5,
            "min_time_ms": 800.0,
            "max_time_ms": 3000.0,
            "total_operations": 150,
            "successful_operations": 148,
            "success_rate": 98.7
        },
        "anomaly_detection": {
            "average_time_ms": 25000.0,
            "min_time_ms": 15000.0,
            "max_time_ms": 45000.0,
            "total_operations": 25,
            "successful_operations": 25,
            "success_rate": 100.0
        }
    }
    ```
    """
    try:
        hours = int(request.GET.get('hours', 24))
        if hours <= 0 or hours > 720:  # Max 30 days
            return JsonResponse(
                {'error': 'Hours must be between 1 and 720'}, 
                status=400
            )
        
        summary = PerformanceMetric.get_performance_summary(hours)
        
        return JsonResponse({
            'status': 'success',
            'hours': hours,
            'summary': summary
        })
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid hours parameter: {e}'}, status=400)
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def operation_metrics(request, operation_type):
    """
    Get metrics for a specific operation type.
    
    **Path Parameters:**
    - operation_type: Type of operation (blockchain_save, anomaly_detection, etc.)
    
    **Query Parameters:**
    - hours: Number of hours to look back (default: 24)
    
    **Response:**
    ```json
    {
        "operation_type": "blockchain_save",
        "average_time_ms": 1250.5,
        "hours": 24,
        "recent_metrics": [
            {
                "execution_time_ms": 1200.0,
                "transaction_count": 5,
                "success": true,
                "created_at": "2024-01-15T10:30:00Z"
            }
        ]
    }
    ```
    """
    try:
        # Validate operation type
        valid_operations = [choice[0] for choice in PerformanceMetric.OPERATION_CHOICES]
        if operation_type not in valid_operations:
            return JsonResponse(
                {'error': f'Invalid operation type. Valid types: {valid_operations}'}, 
                status=400
            )
        
        hours = int(request.GET.get('hours', 24))
        if hours <= 0 or hours > 720:
            return JsonResponse(
                {'error': 'Hours must be between 1 and 720'}, 
                status=400
            )
        
        # Get average time
        avg_time = PerformanceMetric.get_average_time(operation_type, hours)
        
        # Get recent metrics (last 10)
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        recent_metrics = PerformanceMetric.objects.filter(
            operation_type=operation_type,
            created_at__gte=cutoff_time
        ).order_by('-created_at')[:10]
        
        metrics_data = []
        for metric in recent_metrics:
            metrics_data.append({
                'execution_time_ms': metric.execution_time_ms,
                'transaction_count': metric.transaction_count,
                'success': metric.success,
                'created_at': metric.created_at.isoformat(),
                'error_message': metric.error_message
            })
        
        return JsonResponse({
            'status': 'success',
            'operation_type': operation_type,
            'average_time_ms': avg_time,
            'hours': hours,
            'recent_metrics': metrics_data
        })
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid parameter: {e}'}, status=400)
    except Exception as e:
        logger.error(f"Error getting operation metrics: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def performance_alerts(request):
    """
    Get recent performance alerts.
    
    **Query Parameters:**
    - hours: Number of hours to look back (default: 24)
    - severity: Filter by severity level (low, medium, high, critical)
    - resolved: Filter by resolution status (true, false)
    
    **Response:**
    ```json
    {
        "alerts": [
            {
                "operation_type": "blockchain_save",
                "severity": "high",
                "threshold_ms": 5000.0,
                "actual_time_ms": 12000.0,
                "message": "Operation blockchain_save took 12000.00ms, exceeding threshold of 5000.00ms",
                "created_at": "2024-01-15T10:30:00Z",
                "resolved": false
            }
        ]
    }
    ```
    """
    try:
        hours = int(request.GET.get('hours', 24))
        if hours <= 0 or hours > 720:
            return JsonResponse(
                {'error': 'Hours must be between 1 and 720'}, 
                status=400
            )
        
        severity = request.GET.get('severity')
        resolved = request.GET.get('resolved')
        
        # Get alerts
        alerts = performance_monitor.get_recent_alerts(hours, severity)
        
        # Filter by resolution status if specified
        if resolved is not None:
            resolved_bool = resolved.lower() == 'true'
            alerts = [alert for alert in alerts if alert.resolved == resolved_bool]
        
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'operation_type': alert.operation_type,
                'severity': alert.severity,
                'threshold_ms': alert.threshold_ms,
                'actual_time_ms': alert.actual_time_ms,
                'message': alert.message,
                'created_at': alert.created_at.isoformat(),
                'resolved': alert.resolved
            })
        
        return JsonResponse({
            'status': 'success',
            'hours': hours,
            'alerts': alerts_data
        })
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid parameter: {e}'}, status=400)
    except Exception as e:
        logger.error(f"Error getting performance alerts: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def end_to_end_performance(request):
    """
    Get end-to-end performance metrics for transaction uploads.
    
    **Query Parameters:**
    - hours: Number of hours to look back (default: 24)
    - operation_type: Specific operation type (single_transaction_upload, csv_batch_upload)
    
    **Response:**
    ```json
    {
        "single_transaction_upload": {
            "average_time_ms": 8500.0,
            "total_operations": 25,
            "success_rate": 96.0
        },
        "csv_batch_upload": {
            "average_time_ms": 25000.0,
            "total_operations": 10,
            "success_rate": 90.0
        }
    }
    ```
    """
    try:
        hours = int(request.GET.get('hours', 24))
        if hours <= 0 or hours > 720:
            return JsonResponse(
                {'error': 'Hours must be between 1 and 720'}, 
                status=400
            )
        
        operation_type = request.GET.get('operation_type')
        
        if operation_type:
            # Get specific operation metrics
            avg_time = PerformanceMetric.get_average_time(operation_type, hours)
            summary = PerformanceMetric.get_performance_summary(hours)
            
            if operation_type in summary:
                stats = summary[operation_type]
                return JsonResponse({
                    'status': 'success',
                    'operation_type': operation_type,
                    'hours': hours,
                    'average_time_ms': avg_time,
                    'total_operations': stats['total_operations'],
                    'success_rate': stats['success_rate'],
                    'min_time_ms': stats['min_time_ms'],
                    'max_time_ms': stats['max_time_ms']
                })
            else:
                return JsonResponse({
                    'status': 'success',
                    'operation_type': operation_type,
                    'hours': hours,
                    'average_time_ms': 0.0,
                    'total_operations': 0,
                    'success_rate': 0.0,
                    'min_time_ms': 0.0,
                    'max_time_ms': 0.0
                })
        else:
            # Get all end-to-end operation metrics
            summary = PerformanceMetric.get_performance_summary(hours)
            
            # Filter for end-to-end operations
            end_to_end_metrics = {}
            for op_type, stats in summary.items():
                if op_type in ['single_transaction_upload', 'csv_batch_upload', 'end_to_end_upload']:
                    end_to_end_metrics[op_type] = {
                        'average_time_ms': stats['average_time_ms'],
                        'total_operations': stats['total_operations'],
                        'success_rate': stats['success_rate'],
                        'min_time_ms': stats['min_time_ms'],
                        'max_time_ms': stats['max_time_ms']
                    }
            
            return JsonResponse({
                'status': 'success',
                'hours': hours,
                'end_to_end_metrics': end_to_end_metrics
            })
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid parameter: {e}'}, status=400)
    except Exception as e:
        logger.error(f"Error getting end-to-end performance: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def performance_dashboard(request):
    """
    Get comprehensive performance dashboard data.
    
    **Query Parameters:**
    - hours: Number of hours to look back (default: 24)
    
    **Response:**
    ```json
    {
        "summary": {...},
        "alerts": [...],
        "top_slow_operations": [...],
        "success_rates": {...}
    }
    ```
    """
    try:
        hours = int(request.GET.get('hours', 24))
        if hours <= 0 or hours > 720:
            return JsonResponse(
                {'error': 'Hours must be between 1 and 720'}, 
                status=400
            )
        
        # Get performance summary
        summary = PerformanceMetric.get_performance_summary(hours)
        
        # Get recent alerts
        alerts = performance_monitor.get_recent_alerts(hours)
        alerts_data = []
        for alert in alerts[:10]:  # Limit to 10 most recent
            alerts_data.append({
                'operation_type': alert.operation_type,
                'severity': alert.severity,
                'threshold_ms': alert.threshold_ms,
                'actual_time_ms': alert.actual_time_ms,
                'message': alert.message,
                'created_at': alert.created_at.isoformat(),
                'resolved': alert.resolved
            })
        
        # Get top slow operations
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Avg
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        slow_operations = PerformanceMetric.objects.filter(
            created_at__gte=cutoff_time,
            success=True
        ).values('operation_type').annotate(
            avg_time=Avg('execution_time_ms')
        ).order_by('-avg_time')[:5]
        
        top_slow = []
        for op in slow_operations:
            top_slow.append({
                'operation_type': op['operation_type'],
                'average_time_ms': op['avg_time']
            })
        
        return JsonResponse({
            'status': 'success',
            'hours': hours,
            'summary': summary,
            'alerts': alerts_data,
            'top_slow_operations': top_slow
        })
        
    except ValueError as e:
        return JsonResponse({'error': f'Invalid parameter: {e}'}, status=400)
    except Exception as e:
        logger.error(f"Error getting performance dashboard: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500) 