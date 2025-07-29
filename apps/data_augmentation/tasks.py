from celery import shared_task
from django.conf import settings
from django.utils import timezone
from apps.data_augmentation.services import (
    scrape_average_price_for_item,
    get_unique_items_from_transactions
)
from apps.data_augmentation.models import ItemAveragePrice
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_item_price_task(self, item_name: str):
    """
    Background task to scrape price for a single item.
    Retries up to 3 times if scraping fails.
    """
    try:
        logger.info(f"Starting background price scraping for item: {item_name}")
        
        # Check if we already have today's price
        today = timezone.now().date()
        try:
            cached_price = ItemAveragePrice.objects.get(
                item_name__iexact=item_name,
                date=today
            )
            logger.info(f"Found cached price for '{item_name}' on {today}: {cached_price.average_price}")
            return {
                'status': 'cached',
                'item_name': item_name,
                'price': str(cached_price.average_price),
                'date': str(today)
            }
        except ItemAveragePrice.DoesNotExist:
            pass
        
        # Scrape the price
        scraped_price = scrape_average_price_for_item(item_name)
        
        if scraped_price:
            # Save to cache
            ItemAveragePrice.objects.create(
                item_name=item_name,
                date=today,
                average_price=scraped_price,
                details={'source': 'Amazon', 'background_task': True}
            )
            
            logger.info(f"Successfully scraped and cached price for '{item_name}': {scraped_price}")
            return {
                'status': 'success',
                'item_name': item_name,
                'price': str(scraped_price),
                'date': str(today)
            }
        else:
            logger.warning(f"Could not scrape price for '{item_name}'")
            return {
                'status': 'failed',
                'item_name': item_name,
                'error': 'No price found'
            }
            
    except Exception as exc:
        logger.error(f"Error scraping price for '{item_name}': {exc}")
        
        # Retry the task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task for '{item_name}' (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))  # Exponential backoff
        
        return {
            'status': 'failed',
            'item_name': item_name,
            'error': str(exc)
        }


@shared_task
def startup_price_scraping_task():
    """
    Background task to run startup price scraping for all unique items.
    This can be called during system boot-up without blocking the main process.
    """
    logger.info("Starting background startup price scraping task...")
    
    # Check if scraping is enabled
    if not getattr(settings, 'ENABLE_PRICE_SCRAPING', False):
        logger.info("Price scraping is disabled. Skipping background startup scraping.")
        return {
            'status': 'disabled',
            'message': 'Price scraping is disabled in settings'
        }
    
    # Get all unique items
    unique_items = get_unique_items_from_transactions()
    logger.info(f"Found {len(unique_items)} unique items for background startup scraping")
    
    if not unique_items:
        logger.info("No items found in transactions. Skipping background startup scraping.")
        return {
            'status': 'no_items',
            'message': 'No items found in transactions'
        }
    
    # Create tasks for each item
    tasks = []
    for item_name in unique_items:
        task = scrape_item_price_task.delay(item_name)
        tasks.append(task)
    
    logger.info(f"Created {len(tasks)} background scraping tasks")
    
    return {
        'status': 'started',
        'tasks_created': len(tasks),
        'items': unique_items
    }


@shared_task
def cleanup_old_price_cache_task(days_to_keep: int = 7):
    """
    Background task to cleanup old price cache entries.
    Keeps only the specified number of days of cache data.
    """
    try:
        cutoff_date = timezone.now().date() - timezone.timedelta(days=days_to_keep)
        
        # Count items to be deleted
        old_items_count = ItemAveragePrice.objects.filter(date__lt=cutoff_date).count()
        
        # Delete old items
        deleted_count, _ = ItemAveragePrice.objects.filter(date__lt=cutoff_date).delete()
        
        logger.info(f"Cleaned up {deleted_count} old price cache entries older than {cutoff_date}")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'cutoff_date': str(cutoff_date)
        }
        
    except Exception as e:
        logger.error(f"Error during price cache cleanup: {e}")
        return {
            'status': 'failed',
            'error': str(e)
        } 