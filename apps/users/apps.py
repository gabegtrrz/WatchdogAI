from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    
    def ready(self):
        """Import admin models when app is ready."""
        try:
            import apps.users.admin  # noqa
        except ImportError:
            pass