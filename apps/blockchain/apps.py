from django.apps import AppConfig


class BlockchainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.blockchain"
    
    def ready(self):
        """Import admin models when app is ready."""
        try:
            import apps.blockchain.admin  # noqa
        except ImportError:
            pass