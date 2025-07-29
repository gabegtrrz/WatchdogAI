"""
Views for displaying performance monitoring data.

This module provides views to display performance metrics
collected during analysis pipeline execution.
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import json
import os
from typing import List, Dict, Any


def performance_dashboard(request):
    """
    Display performance metrics dashboard.
    
    Shows recent analysis performance data including:
    - Total analysis times
    - Step-by-step timing breakdowns
    - Success/failure rates
    - Performance trends
    """
    try:
        # Get performance log path from settings
        log_path = getattr(settings, 'PERFORMANCE_LOG_PATH', 'logs/performance_metrics.json')
        
        # Check if monitoring is enabled
        monitoring_enabled = getattr(settings, 'ENABLE_PERFORMANCE_MONITORING', True)
        
        if not monitoring_enabled:
            return render(request, 'performance_monitoring/dashboard.html', {
                'monitoring_enabled': False,
                'error_message': 'Performance monitoring is disabled in settings.'
            })
        
        # Read performance data
        if not os.path.exists(log_path):
            return render(request, 'performance_monitoring/dashboard.html', {
                'monitoring_enabled': True,
                'error_message': f'Performance log file not found at {log_path}',
                'metrics': []
            })
        
        with open(log_path, 'r', encoding='utf-8') as f:
            metrics_data = json.load(f)
        
        if not isinstance(metrics_data, list):
            metrics_data = [metrics_data]
        
        # Limit to last 50 entries for performance
        recent_metrics = metrics_data[:50]
        
        # Calculate summary statistics
        summary = _calculate_summary_stats(recent_metrics)
        
        context = {
            'monitoring_enabled': True,
            'metrics': recent_metrics,
            'summary': summary,
            'total_entries': len(metrics_data)
        }
        
        return render(request, 'performance_monitoring/dashboard.html', context)
        
    except Exception as e:
        return render(request, 'performance_monitoring/dashboard.html', {
            'monitoring_enabled': True,
            'error_message': f'Error loading performance data: {str(e)}',
            'metrics': []
        })


def performance_api(request):
    """
    API endpoint to return performance metrics as JSON.
    
    Returns:
        JSON response with recent performance metrics and summary statistics
    """
    try:
        log_path = getattr(settings, 'PERFORMANCE_LOG_PATH', 'logs/performance_metrics.json')
        monitoring_enabled = getattr(settings, 'ENABLE_PERFORMANCE_MONITORING', True)
        
        if not monitoring_enabled:
            return JsonResponse({
                'error': 'Performance monitoring is disabled',
                'monitoring_enabled': False
            })
        
        if not os.path.exists(log_path):
            return JsonResponse({
                'error': 'Performance log file not found',
                'monitoring_enabled': True,
                'metrics': []
            })
        
        with open(log_path, 'r', encoding='utf-8') as f:
            metrics_data = json.load(f)
        
        if not isinstance(metrics_data, list):
            metrics_data = [metrics_data]
        
        # Return last 20 entries
        recent_metrics = metrics_data[:20]
        summary = _calculate_summary_stats(recent_metrics)
        
        return JsonResponse({
            'monitoring_enabled': True,
            'metrics': recent_metrics,
            'summary': summary,
            'total_entries': len(metrics_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error loading performance data: {str(e)}',
            'monitoring_enabled': True,
            'metrics': []
        })


def _calculate_summary_stats(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary statistics from performance metrics.
    
    Args:
        metrics: List of performance metric dictionaries
        
    Returns:
        Dictionary containing summary statistics
    """
    if not metrics:
        return {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'avg_total_time': 0,
            'avg_step_times': {},
            'success_rate': 0
        }
    
    total_analyses = len(metrics)
    successful_analyses = sum(1 for m in metrics if m.get('status') == 'success')
    failed_analyses = total_analyses - successful_analyses
    
    # Calculate average total analysis time
    total_times = [m.get('total_analysis_time', 0) for m in metrics if m.get('total_analysis_time')]
    avg_total_time = sum(total_times) / len(total_times) if total_times else 0
    
    # Calculate average step times
    step_times = {}
    for metric in metrics:
        if 'step_timings' in metric:
            for step_name, step_time in metric['step_timings'].items():
                if step_name not in step_times:
                    step_times[step_name] = []
                step_times[step_name].append(step_time)
    
    avg_step_times = {}
    for step_name, times in step_times.items():
        avg_step_times[step_name] = sum(times) / len(times)
    
    return {
        'total_analyses': total_analyses,
        'successful_analyses': successful_analyses,
        'failed_analyses': failed_analyses,
        'avg_total_time': round(avg_total_time, 3),
        'avg_step_times': {k: round(v, 3) for k, v in avg_step_times.items()},
        'success_rate': round((successful_analyses / total_analyses) * 100, 1) if total_analyses > 0 else 0
    } 