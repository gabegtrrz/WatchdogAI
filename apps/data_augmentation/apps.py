from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver


class DataAugmentationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.data_augmentation"
    
    def ready(self):
        """Import admin models and trigger startup price scraping when app is ready."""
        try:
            import apps.data_augmentation.admin  # noqa
            
            # Only run startup scraping in production or when explicitly enabled
            from django.conf import settings
            if getattr(settings, 'ENABLE_STARTUP_PRICE_SCRAPING', False):
                # Use background task for startup scraping to avoid blocking
                from .tasks import startup_price_scraping_task
                startup_price_scraping_task.delay()
                
        except ImportError:
            pass


@receiver(post_migrate)
def create_procurement_methods(sender, **kwargs):
    """Create default procurement methods after migration."""
    from apps.core.models import ProcurementMethod
    
    default_methods = [
        'Public Bidding',
        'Direct Contracting',
        'Limited Source Bidding',
        'Repeat Order',
        'Shopping',
        'Emergency Purchase',
        'Negotiated Procurement',
        'Small Value Procurement'
    ]
    
    for method_name in default_methods:
        ProcurementMethod.objects.get_or_create(name=method_name)