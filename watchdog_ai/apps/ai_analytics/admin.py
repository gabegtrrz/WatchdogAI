from django.contrib import admin
from .models import AnomalyReport


@admin.register(AnomalyReport)
class AnomalyReportAdmin(admin.ModelAdmin):
    """
    Admin interface for AnomalyReport model.
    """
    list_display = [
        'transaction_id',
        'is_anomaly',
        'anomaly_severity',
        'confidence_level',
        'status',
        'detection_timestamp',
    ]
    
    list_filter = [
        'is_anomaly',
        'status',
        'explanation_generated',
        'detection_timestamp',
    ]
    
    search_fields = [
        'related_transaction__transaction_id',
        'related_transaction__item_name',
        'related_transaction__supplier',
    ]
    
    readonly_fields = [
        'detection_timestamp',
        'processing_duration_ms',
        'anomaly_severity',
        'is_high_priority',
    ]
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('related_transaction',)
        }),
        ('Anomaly Detection Results', {
            'fields': (
                'is_anomaly',
                'anomaly_score',
                'confidence_level',
                'anomaly_severity',
                'is_high_priority',
            )
        }),
        ('Processing Information', {
            'fields': (
                'status',
                'detection_timestamp',
                'processing_duration_ms',
                'processing_error',
            )
        }),
        ('Model Information', {
            'fields': (
                'model_version',
                'model_training_date',
            )
        }),
        ('Explanation Data', {
            'fields': (
                'explanation_generated',
                'explanation_timestamp',
                'feature_values',
                'shap_values',
                'top_contributing_features',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def transaction_id(self, obj):
        """Display transaction ID for better readability."""
        return obj.related_transaction.transaction_id if obj.related_transaction else "N/A"
    transaction_id.short_description = "Transaction ID"
