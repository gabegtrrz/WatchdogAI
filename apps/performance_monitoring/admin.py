"""
Admin interface for performance monitoring models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import PerformanceMetric, PerformanceAlert


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    """
    Admin interface for PerformanceMetric model.
    
    **Features:**
    - Filterable by operation type, success status, and date range
    - Searchable by error messages and user/session IDs
    - Read-only interface to prevent manual data manipulation
    - Performance summary display
    """
    
    list_display = [
        'operation_type', 
        'execution_time_display', 
        'transaction_count',
        'success', 
        'created_at'
    ]
    
    list_filter = [
        'operation_type',
        'success',
        'created_at',
    ]
    
    search_fields = [
        'error_message',
        'user_id',
        'session_id'
    ]
    
    readonly_fields = [
        'operation_type',
        'execution_time_ms',
        'transaction_count',
        'created_at',
        'success',
        'error_message',
        'user_id',
        'session_id'
    ]
    
    ordering = ['-created_at']
    
    list_per_page = 50
    
    def execution_time_display(self, obj):
        """Display execution time with color coding."""
        if obj.execution_time_ms > 10000:  # > 10 seconds
            color = 'red'
        elif obj.execution_time_ms > 5000:  # > 5 seconds
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {};">{:.2f}ms</span>',
            color,
            obj.execution_time_ms
        )
    execution_time_display.short_description = 'Execution Time'
    
    def has_add_permission(self, request):
        """Prevent manual creation of metrics."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent manual editing of metrics."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return True
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related()
    
    def changelist_view(self, request, extra_context=None):
        """Add performance summary to changelist view."""
        extra_context = extra_context or {}
        
        # Get performance summary for the last 24 hours
        summary = PerformanceMetric.get_performance_summary(hours=24)
        extra_context['performance_summary'] = summary
        
        return super().changelist_view(request, extra_context)


@admin.register(PerformanceAlert)
class PerformanceAlertAdmin(admin.ModelAdmin):
    """
    Admin interface for PerformanceAlert model.
    
    **Features:**
    - Filterable by operation type, severity, and resolution status
    - Bulk actions for resolving alerts
    - Color-coded severity display
    - Performance threshold information
    """
    
    list_display = [
        'operation_type',
        'severity_display',
        'threshold_display',
        'actual_time_display',
        'ratio_display',
        'resolved',
        'created_at'
    ]
    
    list_filter = [
        'operation_type',
        'severity',
        'resolved',
        'created_at',
    ]
    
    search_fields = [
        'message',
        'operation_type'
    ]
    
    readonly_fields = [
        'operation_type',
        'threshold_ms',
        'actual_time_ms',
        'severity',
        'message',
        'created_at'
    ]
    
    ordering = ['-created_at']
    
    list_per_page = 50
    
    actions = ['resolve_alerts']
    
    def severity_display(self, obj):
        """Display severity with color coding."""
        colors = {
            'critical': 'red',
            'high': 'orange',
            'medium': 'yellow',
            'low': 'green'
        }
        color = colors.get(obj.severity, 'black')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.severity.upper()
        )
    severity_display.short_description = 'Severity'
    
    def threshold_display(self, obj):
        """Display threshold time."""
        return f"{obj.threshold_ms:.2f}ms"
    threshold_display.short_description = 'Threshold'
    
    def actual_time_display(self, obj):
        """Display actual time with color coding."""
        if obj.actual_time_ms > obj.threshold_ms * 3:
            color = 'red'
        elif obj.actual_time_ms > obj.threshold_ms * 2:
            color = 'orange'
        else:
            color = 'yellow'
        
        return format_html(
            '<span style="color: {};">{:.2f}ms</span>',
            color,
            obj.actual_time_ms
        )
    actual_time_display.short_description = 'Actual Time'
    
    def ratio_display(self, obj):
        """Display ratio of actual to threshold time."""
        ratio = obj.actual_time_ms / obj.threshold_ms
        return f"{ratio:.1f}x"
    ratio_display.short_description = 'Ratio'
    
    def resolve_alerts(self, request, queryset):
        """Bulk action to resolve alerts."""
        updated = queryset.update(resolved=True)
        self.message_user(
            request,
            f"Successfully resolved {updated} performance alert(s)."
        )
    resolve_alerts.short_description = "Mark selected alerts as resolved"
    
    def has_add_permission(self, request):
        """Prevent manual creation of alerts."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow editing only the resolved field."""
        return True 