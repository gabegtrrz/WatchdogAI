
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import logging
import os
from decimal import Decimal, getcontext
from django.utils import timezone
from django.conf import settings
from apps.core.models import Transaction
from .models import ItemAveragePrice

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
    
    # Check if scraping is enabled
    if not getattr(settings, 'ENABLE_PRICE_SCRAPING', False):
        logger.info(f"Price scraping is disabled. Skipping scraping for '{product_name}'.")
        return []
    
    search_url = f"https://www.amazon.com/s?k={product_name.replace(' ', '+')}"
    prices = []
    
    # Get timeout from settings
    timeout = getattr(settings, 'SCRAPING_TIMEOUT', 10)
    
    logger.info(f"Starting Amazon scraping for '{product_name}' (timeout: {timeout}s)")
    
    for attempt in range(retries):
        try:
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
            
            if prices:
                logger.info(f"Successfully scraped {len(prices)} prices for '{product_name}': {prices}")
                return prices # Return prices if found

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for '{product_name}' on attempt {attempt+1}: {e}")
            if attempt >= retries - 1:
                logger.error(f"All retry attempts failed for '{product_name}'")
                return [] # Return empty list after last retry
        
        except Exception as e:
            logger.error(f"An unexpected error occurred while scraping Amazon for '{product_name}': {e}")
            return [] # Return empty list on unexpected error

    logger.warning(f"No prices found for '{product_name}' after {retries} attempts")
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
    logger.info(f"Final price for '{item_name}': ₱{final_price} PHP")
    
    return final_price


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
        # Use today's date for the cache
        date_to_check = timezone.now().date()

        try:
            # 1. Check cache first
            cached_price = ItemAveragePrice.objects.get(
                item_name__iexact=item_name,
                date=date_to_check
            )
            logger.info(f"Found cached price for '{item_name}' on {date_to_check}: {cached_price.average_price}")
            transaction.average_price = cached_price.average_price

        except ItemAveragePrice.DoesNotExist:
            logger.info(f"No cached price for '{item_name}' on {date_to_check}. Scraping...")
            # 2. If not in cache, scrape
            scraped_price = scrape_average_price_for_item(item_name)

            if scraped_price:
                logger.info(f"Scraped price for '{item_name}': {scraped_price}")
                transaction.average_price = scraped_price
                
                # 3. Save to cache for future use
                ItemAveragePrice.objects.create(
                    item_name=item_name,
                    date=date_to_check,
                    average_price=scraped_price,
                    details={'source': 'Amazon'} # Example detail
                )
            else:
                logger.warning(f"Could not scrape a price for '{item_name}'. It will be skipped.")
                skipped_count += 1
                continue # Skip to the next transaction

        transactions_to_update.append(transaction)

    if transactions_to_update:
        # 4. Bulk update transactions for efficiency as clean save has been done previously
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
