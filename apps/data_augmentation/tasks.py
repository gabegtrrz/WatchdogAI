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
    Fetch and cache the average price for a SINGLE item as a background task.

    This Celery task retrieves today's average price for the specified item_name in a way that is idempotent—meaning it can be executed multiple times without changing the outcome or causing unintended effects. If a cache entry for today already exists in
    `ItemAveragePrice`, the cached value is returned and no external scraping is
    performed. Otherwise, it will call `scrape_average_price_for_item` to obtain
    a fresh value and persist it.

    Retries: Up to 3 attempts with exponential backoff on unhandled exceptions.

    Args:
        item_name: Case-insensitive name of the item to price-check.

    Returns:
        A dictionary shaped for logging/inspection with keys:
        - 'status': One of {'cached', 'success', 'failed'}
        - 'item_name': The normalized item name provided to the task
        - 'price': Stringified price when available
        - 'date': ISO date string for the cache entry when available
        - 'error': Present only when status == 'failed'

    Status semantics:
        - 'cached': A record for `item_name` already existed in `ItemAveragePrice`
          for today's date, so no external scraping occurred. The returned 'price'
          and 'date' reflect the existing database entry.
        - 'success': No cache existed for today; the task scraped a fresh price
          via `scrape_average_price_for_item`, persisted it as a new
          `ItemAveragePrice` row for today, and returns that value in 'price'.
        - 'failed': Either no price could be obtained from the scraper (e.g.,
          parsing or availability issue) or an exception occurred and retries were
          exhausted. In this case, no new cache entry is created for today and the
          response includes an 'error' message.

    Side Effects:
        - Reads/writes `ItemAveragePrice` for today's date. Saved to model in the database.
        - Emits structured logs for observability.

    Raises:
        The task will schedule a retry on unexpected exceptions until
        `max_retries` is reached, then return a 'failed' result.
    """
    try:
        logger.info(f"Starting background price scraping for item: {item_name}")
        
        # Fast-path: return early if today's price is already cached
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
            pass # move on to scraping a fresh price
        
        # Scrape a fresh average price via the service layer
        scraped_price = scrape_average_price_for_item(item_name)
        
        if scraped_price:
            # Persist the newly scraped price as today's cache entry
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
        
        # Retry using exponential backoff (60s, 120s, 240s) up to max_retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task for '{item_name}' (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))  # Exponential backoff
            # First failure (retries == 0): 60 * 2^0 = 60s
            # Second failure (retries == 1): 60 * 2^1 = 120s
            # Third failure (retries == 2): 60 * 2^2 = 240s
        
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
    if not getattr(settings, 'ENABLE_PRICE_SCRAPING', False): # django's global settings object
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
    tasks_num = 0
    for item_name in unique_items:
        task = scrape_item_price_task.delay(item_name)
        tasks_num += 1
    
    logger.info(f"Created {len(tasks_num)} background scraping tasks")
    
    return {
        'status': 'started',
        'tasks_created': tasks_num,
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