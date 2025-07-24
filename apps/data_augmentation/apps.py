from django.apps import AppConfig


class DataAugmentationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.data_augmentation"
    
    def ready(self):
        """Import admin models when app is ready."""
        try:
            import apps.data_augmentation.admin  # noqa
        except ImportError:
            pass