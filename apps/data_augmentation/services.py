
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import logging
import os
import time
from decimal import Decimal, getcontext
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from apps.core.models import Transaction
from .models import ItemAveragePrice
from apps.performance_monitoring.services import PerformanceMonitor

# It's better to configure this in Django's settings.py
# For now, we will use a placeholder or get it from env.
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY", "YOUR_API_KEY_HERE")
MAX_SOURCES_PER_ITEM = 5
USD_TO_PHP_RATE = 56

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Force DEBUG level for this module

# Set precision for Decimal
getcontext().prec = 17 # max_digits=15, decimal_places=2 needs precision

def get_scrapeops_url(url, location="us", render_js=False):
    """Generates a ScrapeOps proxy URL."""
    if SCRAPEOPS_API_KEY == "YOUR_API_KEY_HERE":
        logger.warning("ScrapeOps API key is not set. Using a placeholder.")
        # Fallback to direct request if API key is not set
        return url

    payload = {
        "api_key": SCRAPEOPS_API_KEY,
        "url": url,
        "country": location
    }
    if render_js:
        payload['render_js'] = 'true'

    proxy_url = "https://proxy.scrapeops.io/v1/?" + urlencode(payload)
    logger.debug(f"Generated ScrapeOps URL: {proxy_url}")
    return proxy_url

def clean_price(price_str) -> Decimal | None:
    if not price_str:
        return None
    try:
        # More robust cleaning to handle different currency symbols and commas
        cleaned = ''.join(filter(lambda x: x.isdigit() or x == '.', price_str.replace(",", "")))
        if cleaned:
            return Decimal(cleaned)
        return None
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not convert price '{price_str}' to Decimal: {e}")
        return None

def scrape_amazon_prices(product_name: str, location="us", retries=3) -> list[Decimal]:
    """Scrapes a single page of Amazon search results for a product and returns a list of prices."""
    
    # Initialize performance monitoring
    monitor = PerformanceMonitor(f"scrape-amazon-{int(time.time())}")
    monitor.start_analysis()
    
    # Check if scraping is enabled
    if not getattr(settings, 'ENABLE_PRICE_SCRAPING', False):
        logger.info(f"Price scraping is disabled. Skipping scraping for '{product_name}'.")
        monitor.end_analysis({
            'product_name': product_name,
            'prices_found': 0,
            'status': 'disabled'
        })
        return []
    
    search_url = f"https://www.amazon.com/s?k={product_name.replace(' ', '+')}"
    prices = []
    
    # Get timeout from settings
    timeout = getattr(settings, 'SCRAPING_TIMEOUT', 10)
    
    logger.info(f"Starting Amazon scraping for '{product_name}' (timeout: {timeout}s)")
    
    for attempt in range(retries):
        try:
            monitor.start_step(f"attempt_{attempt+1}")
            
            proxy_url = get_scrapeops_url(search_url, location=location)
            logger.info(f"Attempt {attempt+1}/{retries}: Fetching page for '{product_name}' via proxy.")
            
            # Use timeout from settings
            resp = requests.get(proxy_url, timeout=timeout)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')
            results = soup.find_all('div', attrs={'data-component-type': 's-search-result'})
            
            logger.info(f"Found {len(results)} search results for '{product_name}'")
            
            if not results:
                logger.warning(f"No search result containers found for '{product_name}'.")
                monitor.end_step(f"attempt_{attempt+1}")
                continue

            for result in results:
                if len(prices) >= MAX_SOURCES_PER_ITEM:
                    logger.debug(f"Reached max sources ({MAX_SOURCES_PER_ITEM}) for '{product_name}'")
                    break
                
                price_element = result.find('span', {'class': 'a-price'})
                if price_element:
                    price_whole = price_element.find('span', {'class': 'a-price-whole'})
                    price_fraction = price_element.find('span', {'class': 'a-price-fraction'})
                    
                    if price_whole and price_fraction:
                        price_str = f"{price_whole.text.strip()}{price_fraction.text.strip()}"
                        price_decimal = clean_price(price_str)
                        if price_decimal:
                            prices.append(price_decimal)
                            logger.debug(f"Found price for '{product_name}': ${price_decimal}")
            
            monitor.end_step(f"attempt_{attempt+1}")
            
            if prices:
                logger.info(f"Successfully scraped {len(prices)} prices for '{product_name}': {prices}")
                # End analysis with success
                monitor.end_analysis({
                    'product_name': product_name,
                    'prices_found': len(prices),
                    'attempts_made': attempt + 1,
                    'status': 'success'
                })
                return prices # Return prices if found

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for '{product_name}' on attempt {attempt+1}: {e}")
            monitor.end_step(f"attempt_{attempt+1}")
            if attempt >= retries - 1:
                logger.error(f"All retry attempts failed for '{product_name}'")
                # End analysis with error
                monitor.end_analysis({
                    'product_name': product_name,
                    'prices_found': 0,
                    'attempts_made': retries,
                    'status': 'error',
                    'error_message': str(e)
                })
                return [] # Return empty list after last retry
        
        except Exception as e:
            logger.error(f"An unexpected error occurred while scraping Amazon for '{product_name}': {e}")
            monitor.end_step(f"attempt_{attempt+1}")
            # End analysis with error
            monitor.end_analysis({
                'product_name': product_name,
                'prices_found': 0,
                'attempts_made': attempt + 1,
                'status': 'error',
                'error_message': str(e)
            })
            return [] # Return empty list on unexpected error

    logger.warning(f"No prices found for '{product_name}' after {retries} attempts")
    # End analysis with no prices found
    monitor.end_analysis({
        'product_name': product_name,
        'prices_found': 0,
        'attempts_made': retries,
        'status': 'no_prices_found'
    })
    return prices

### Orchestrator
def scrape_average_price_for_item(item_name: str) -> Decimal | None:
    """
    Scrapes web sources for an item's price and returns the average price.
    For now, it only scrapes Amazon.
    """
    logger.info(f"Starting scraping process for item: {item_name}")
    
    # In the future, we can add more sources here.
    # e.g., alibaba_prices = scrape_alibaba_prices(item_name)
    amazon_prices = scrape_amazon_prices(item_name)
    
    all_prices = amazon_prices
    
    if not all_prices:
        logger.warning(f"Could not find any prices for item: {item_name}")
        return None
        
    average_price = sum(all_prices) / Decimal(len(all_prices))
    logger.info(f"Calculated average price for '{item_name}': ${average_price} USD")

    # Convert to PHP
    average_price = average_price * Decimal(str(USD_TO_PHP_RATE))
    
    # Standardize to 2 decimal places for consistency with the model
    final_price = average_price.quantize(Decimal('0.01'))
    logger.info(f"Final price for '{item_name}': PHP {final_price}")
    
    return final_price


def get_unique_items_from_transactions() -> list[str]:
    """
    Retrieves all unique item names from existing transactions.
    Used for startup price scraping to ensure all items have average prices.
    """
    try:
        unique_items = Transaction.objects.values_list('item_name', flat=True).distinct()
        return list(unique_items)
    except Exception as e:
        logger.error(f"Error retrieving unique items: {e}")
        return []


def detect_new_items() -> list[str]:
    """
    Detects items that don't have any price cache entries.
    These are considered "new" items that need price scraping.
    """
    try:
        # Get all unique items from transactions
        all_items = set(get_unique_items_from_transactions())
        
        # Get all items that have price cache entries
        cached_items = set(ItemAveragePrice.objects.values_list('item_name', flat=True).distinct())
        
        # Find new items (items without any cache entries)
        new_items = all_items - cached_items
        
        logger.info(f"Detected {len(new_items)} new items without price cache: {list(new_items)}")
        return list(new_items)
        
    except Exception as e:
        logger.error(f"Error detecting new items: {e}")
        return []


def startup_price_scraping():
    """
    Runs once upon system boot-up to scrape prices for all unique items in the system.
    This ensures that all existing items have average prices available for analysis.
    """
    logger.info("Starting startup price scraping process...")
    
    # Check if scraping is enabled
    if not getattr(settings, 'ENABLE_PRICE_SCRAPING', False):
        logger.info("Price scraping is disabled. Skipping startup scraping.")
        return
    
    # Get all unique items from transactions
    unique_items = get_unique_items_from_transactions()
    logger.info(f"Found {len(unique_items)} unique items for startup scraping")
    
    if not unique_items:
        logger.info("No items found in transactions. Skipping startup scraping.")
        return
    
    today = timezone.now().date()
    scraped_count = 0
    cached_count = 0
    error_count = 0
    
    for item_name in unique_items:
        try:
            # Check if we already have today's price for this item
            try:
                cached_price = ItemAveragePrice.objects.get(
                    item_name__iexact=item_name,
                    date=today
                )
                logger.debug(f"Found cached price for '{item_name}' on {today}: {cached_price.average_price}")
                cached_count += 1
                continue
                
            except ItemAveragePrice.DoesNotExist:
                logger.info(f"No cached price for '{item_name}' on {today}. Scraping...")
                
                # Scrape the price
                scraped_price = scrape_average_price_for_item(item_name)
                
                if scraped_price:
                    # Save to cache
                    ItemAveragePrice.objects.create(
                        item_name=item_name,
                        date=today,
                        average_price=scraped_price,
                        details={'source': 'Amazon', 'startup_scraping': True}
                    )
                    scraped_count += 1
                    logger.info(f"Successfully scraped and cached price for '{item_name}': {scraped_price}")
                else:
                    logger.warning(f"Could not scrape price for '{item_name}'")
                    error_count += 1
                    
        except Exception as e:
            logger.error(f"Error processing item '{item_name}': {e}")
            error_count += 1
    
    logger.info(f"Startup price scraping completed. "
                f"Scraped: {scraped_count}, Cached: {cached_count}, Errors: {error_count}")


def get_or_scrape_average_price(item_name: str) -> Decimal | None:
    """
    Gets the average price for an item from cache, or scrapes it if not available.
    This is the main function used by the enrichment process.
    
    Args:
        item_name: Name of the item to get average price for
        
    Returns:
        Decimal: Average price in PHP, or None if not available
    """
    today = timezone.now().date()
    
    try:
        # Check cache first
        cached_price = ItemAveragePrice.objects.get(
            item_name__iexact=item_name,
            date=today
        )
        logger.debug(f"Found cached price for '{item_name}' on {today}: {cached_price.average_price}")
        return cached_price.average_price
        
    except ItemAveragePrice.DoesNotExist:
        logger.info(f"No cached price for '{item_name}' on {today}. Scraping...")
        
        # Scrape the price
        scraped_price = scrape_average_price_for_item(item_name)
        
        if scraped_price:
            # Save to cache
            ItemAveragePrice.objects.create(
                item_name=item_name,
                date=today,
                average_price=scraped_price,
                details={'source': 'Amazon', 'on_demand_scraping': True}
            )
            logger.info(f"Successfully scraped and cached price for '{item_name}': {scraped_price}")
            return scraped_price
        else:
            logger.warning(f"Could not scrape price for '{item_name}'")
            return None


def enrich_transaction_list(transactions: list[Transaction]):
    """
    Enriches a list of transactions with an average price and returns enrichment stats.
    
    It uses a caching mechanism to avoid re-scraping for the same item on the same day.
    Includes improved error handling and timeout management to prevent worker timeouts.

    Returns:
        A dictionary with counts of updated and skipped transactions.
        Example: {'updated': 10, 'skipped': 2, 'errors': 0}
    """
    logger.info(f"Starting enrichment for {len(transactions)} transactions.")

    # Check if scraping is enabled
    if not getattr(settings, 'ENABLE_PRICE_SCRAPING', False):
        logger.info("Price scraping is disabled. Skipping enrichment process.")
        return {
            'updated': 0,
            'skipped': len(transactions),
            'errors': 0
        }

    transactions_to_update = []
    skipped_count = 0
    error_count = 0

    for i, transaction in enumerate(transactions):
        item_name = str(transaction.item_name)

        try:
            # Get or scrape average price for this item
            average_price = get_or_scrape_average_price(item_name)
            
            if average_price:
                transaction.average_price = average_price
                transactions_to_update.append(transaction)
            else:
                logger.warning(f"Could not get average price for '{item_name}'. It will be skipped.")
                skipped_count += 1
                continue

        except Exception as e:
            logger.error(f"Error processing transaction {transaction.transaction_id} for item '{item_name}': {e}")
            error_count += 1
            continue

    if transactions_to_update:
        # Bulk update transactions for efficiency
        Transaction.objects.bulk_update(transactions_to_update, ['average_price'])
        logger.info(f"Successfully updated {len(transactions_to_update)} transactions.")
    else:
        logger.info("No transactions were updated.")
        
    return {
        'updated': len(transactions_to_update),
        'skipped': skipped_count,
        'errors': error_count
    } 

def test_logging():
    """Test function to verify logging is working correctly."""
    logger.debug("DEBUG: This is a debug message from data_augmentation.services")
    logger.info("INFO: This is an info message from data_augmentation.services")
    logger.warning("WARNING: This is a warning message from data_augmentation.services")
    logger.error("ERROR: This is an error message from data_augmentation.services")
    return "Logging test completed" 
