from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    
    def ready(self):
        """Import admin models when app is ready."""
        try:
            import apps.core.admin  # noqa
        except ImportError:
            pass
