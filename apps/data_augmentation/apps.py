from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

import logging
logger = logging.getLogger(__name__)


class DataAugmentationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.data_augmentation"
    
    def ready(self):
        """Import admin models and trigger startup price scraping when app is ready."""
        try:
            import apps.data_augmentation.admin  # noqa
            
            # Run startup scraping when explicitly enabled (in any environment)
            from django.conf import settings
            environment = getattr(settings, 'ENVIRONMENT', 'development')
            enable_startup = getattr(settings, 'ENABLE_STARTUP_PRICE_SCRAPING', False)
            
            if enable_startup:
                # Use background task for startup scraping to avoid blocking
                from .tasks import startup_price_scraping_task
                startup_price_scraping_task.delay()
                logger.info(f"Started price scraping task in background for '{environment}' environment")
            else:
                logger.info(f"Startup price scraping disabled in '{environment}' environment")
                
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