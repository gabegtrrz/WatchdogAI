from django.apps import AppConfig


class PerformanceMonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.performance_monitoring'
    verbose_name = 'Performance Monitoring'
    
    def ready(self):
        """Import admin models when app is ready."""
        try:
            import apps.performance_monitoring.admin  # noqa
        except ImportError:
            pass 