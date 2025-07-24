from django.apps import AppConfig


class TransactionManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.transaction_management"
    
    def ready(self):
        """Import admin models when app is ready."""
        try:
            import apps.transaction_management.admin  # noqa
        except ImportError:
            pass