# [Source: scraper.txt]
import time
import requests
import json
import logging
import os
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from datetime import datetime, date
import pathlib

### Local Imports ###
from procurement_data_config import PROCUREMENT_DATA
from api_key import SCRAPEOPS_API_KEY

### Placeholder for METHODS_DATA if import fails or is not available
# METHODS_DATA = {
#     "Method1": {"items": {"laptop": {}, "mouse": {}}},
#     "Method2": {"items": {"keyboard": {}, "monitor": {}}},
# }


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

### Define constants for file paths ###

# determines the absolute path to the directory where the scraper.py script itself is located

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()

OUTPUT_FOLDER_PATH = SCRIPT_DIR / "scraper_output" # Folder for output files
# OUTPUT_JSON_FILENAME = f"realtime_average_prices_{date.today().strftime('%Y-%m-%d')}.json"
OUTPUT_JSON_FILENAME = f"realtime_average_prices_{date.today().strftime('%Y-%m-%d')}.json"
OUTPUT_JSON_FULL_PATH = OUTPUT_FOLDER_PATH / OUTPUT_JSON_FILENAME


API_KEY = SCRAPEOPS_API_KEY # API key for ScrapeOps

USD_TO_PHP = 56.0 # Conversion rate: 1 USD = 56 PHP
MAX_SOURCES_PER_ITEM = 5 # Maximum number of sources to average per item

class DataPipeline:
    
    def __init__(self, output_filename=OUTPUT_JSON_FILENAME, folder_path=OUTPUT_FOLDER_PATH):
        # Stores {item: [{"price": float, "url": str}, ...]}
        self.scraped_data = {}
        self.output_filepath = folder_path / output_filename
        folder_path.mkdir(parents=True, exist_ok=True) 
        os.makedirs(folder_path, exist_ok=True)
        self.last_updated_time = None # Will store the timestamp when saving

    # Modified add_data to store price and URL pairs, and use MAX_SOURCES_PER_ITEM
    def add_data(self, item, price, url=""):
       
        if price > 0:  # Only include valid prices
            if item not in self.scraped_data:
                self.scraped_data[item] = []

            # Add data only if we haven't reached the max number of sources
            if len(self.scraped_data[item]) < MAX_SOURCES_PER_ITEM:
                 # Ensure URL is not empty, provide a placeholder if necessary
                source_url = url if url else "N/A"
                self.scraped_data[item].append({"price": price, "url": source_url})
                logger.info(f"Added price {price} from {source_url} for item {item}. Sources: {len(self.scraped_data[item])}/{MAX_SOURCES_PER_ITEM}")
            else:
                 logger.debug(f"({MAX_SOURCES_PER_ITEM}) prices accomplished {item}.")


    # Modified save_to_json to create the desired output structure
    def save_to_json(self):

        #initialized output_data as an empty dictionary
        output_data = {}

        self.last_updated_time = datetime.now().isoformat() # !!! Use ISO format for timestamp

        for item, sources in self.scraped_data.items():
            if not sources: # Skip items with no valid sources found
                logger.warning(f"No valid sources found for item: {item}. Skipping.")
                continue

            # Calculate average price from the collected sources (up to MAX_SOURCES_PER_ITEM)
            total_price = sum(source["price"] for source in sources)
            num_sources = len(sources)
            average_price = total_price / num_sources if num_sources > 0 else 0.0
            # source_links = [source["url"] for source in sources]

            output_data[item] = {
                "item_name": item, # Added for clarity, matches the key
                "last_updated": self.last_updated_time,
                "average_price": round(average_price, 2), # Round to 2 decimal places
                "pricing_unit": "₱",
                "num_sources": num_sources,
                # "source_links": source_links
            }
            logger.info(f"Calculated average price for {item}: {average_price:.2f} from {num_sources} sources.")

        # Save the combined data to the single JSON file
        try:
            with open(self.output_filepath, mode="w", encoding="utf-8") as output_file:
                json.dump(output_data, output_file, indent=4)
            logger.info(f"Successfully saved data to {self.output_filepath}")
        except IOError as e:
            logger.error(f"Error saving data to {self.output_filepath}: {e}")


def get_scrapeops_url(url, location="us"):
    payload = {
        "api_key": API_KEY,
        "url": url,
        "country": location
    }
    # Ensure the base URL ends with a slash if needed, and handle query params correctly
    proxy_url = "https://proxy.scrapeops.io/v1/?" + urlencode(payload)
    logger.debug(f"Generated ScrapeOps URL: {proxy_url}")
    return proxy_url


def clean_price(price_str, pricing_unit):
    if not price_str or pricing_unit not in price_str:
        logger.debug(f"Price string '{price_str}' is empty or does not contain unit '{pricing_unit}'.")
        return 0.0
    try:
        # More robust cleaning
        cleaned = ''.join(filter(lambda x: x.isdigit() or x == '.', price_str.replace(pricing_unit, "").replace(",", "").strip()))
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not convert price '{price_str}' to float: {e}")
        return 0.0


def search_products(product_name: str, page_number=1, location="us", retries=3, data_pipeline=None):
    """Scrapes a single page of Amazon search results for a product."""
    tries = 0
    success = False
    search_url = f"https://www.amazon.com/s?k={product_name.replace(' ', '+')}&page={page_number}" # URL encode product name

    while tries < retries and not success:
        try:
            proxy_url = get_scrapeops_url(search_url, location=location)
            logger.info(f"Attempt {tries+1}/{retries}: Fetching page {page_number} for '{product_name}' via proxy: {proxy_url}")
            # Increased timeout for potentially slow proxy/network
            resp = requests.get(proxy_url, timeout=20)
            resp.raise_for_status() # Check for HTTP errors

            logger.info(f"Successfully fetched page {page_number} for '{product_name}'. Status: {resp.status_code}")
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Find result containers (might need adjustment based on current Amazon structure)
            # Using 'data-component-type="s-search-result"' is often more reliable
            results = soup.find_all('div', {'data-component-type': 's-search-result'})
            logger.info(f"Found {len(results)} potential results on page {page_number} for '{product_name}'.")

            if not results:
                 logger.warning(f"No search result containers found on page {page_number} for '{product_name}'. Check selectors.")
                 # Try to save soup for debugging if needed
                 # with open(f"debug_{product_name}_page{page_number}.html", "w", encoding="utf-8") as f:
                 #     f.write(resp.text)

            processed_count = 0
            for result in results:
                # Limit processing if max sources already reached for this item in the pipeline
                if product_name in data_pipeline.scraped_data and len(data_pipeline.scraped_data[product_name]) >= MAX_SOURCES_PER_ITEM:
                     logger.info(f"Max sources ({MAX_SOURCES_PER_ITEM}) reached for '{product_name}' proceeding with next item.")
                     success = True # Mark as success for this page, even if stopping early
                     return # Exit the function early for this item

                title_element = result.find('h2')
                item_title = title_element.text.strip() if title_element else "N/A"

                price_element = result.find('span', class_='a-price')
                price_symbol_element = result.find('span', class_='a-price-symbol')
                price_whole_element = result.find('span', class_='a-price-whole')
                price_fraction_element = result.find('span', class_='a-price-fraction')

                usd_symbol = price_symbol_element.text if price_symbol_element else "$"
                price_str = ""
                if price_whole_element and price_fraction_element:
                    price_str = f"{usd_symbol}{price_whole_element.text}{price_fraction_element.text}"
                elif price_element: # Fallback if whole/fraction not found
                     price_str = price_element.text.strip()


                link_element = result.find('a', class_='a-link-normal', href=True)
                # Construct full URL, ensure it doesn't start with /gp/slredirect/
                product_url = ""
                if link_element and link_element['href'] and not link_element['href'].startswith('/gp/slredirect/'):
                    product_url = f"https://www.amazon.com{link_element['href']}"

                if price_str and product_url:
                    usd_price = clean_price(price_str, usd_symbol)
                    php_price = usd_price * USD_TO_PHP if usd_price else 0.0
                    if php_price > 0:
                         # Add data to the pipeline
                        data_pipeline.add_data(product_name, php_price, product_url)
                        processed_count += 1
                    else:
                         logger.debug(f"Skipping item '{item_title}' due to zero price after cleaning/conversion.")

                else:
                     logger.debug(f"Skipping result for '{item_title}' due to missing price ('{price_str}') or URL ('{product_url}').")


            if processed_count == 0 and len(results) > 0:
                 logger.warning(f"Processed 0 items with valid prices/URLs from {len(results)} results found for '{product_name}' on page {page_number}.")

            success = True # Mark as successful if the page was fetched and parsed, even if no items added

        except requests.exceptions.RequestException as e:
            tries += 1
            logger.warning(f"Network error scraping page {page_number} for '{product_name}': {str(e)}, tries left: {retries-tries}")
            if tries < retries: time.sleep(2) # Wait longer before retrying on network errors
        except Exception as e:
            tries += 1
            logger.error(f"Unexpected error scraping page {page_number} for '{product_name}': {str(e)}, tries left: {retries-tries}", exc_info=True) # Log traceback
            if tries < retries: time.sleep(1)

    if not success:
        logger.error(f"Failed to scrape page {page_number} for '{product_name}' after {retries} retries.")



def threaded_search(product_name, pages, data_pipeline, max_workers=5, location="us", retries=3):
    """Runs search_products in parallel threads for multiple pages."""
    logger.info(f"Starting threaded search for '{product_name}' across {pages} pages.")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks
        futures = [
            executor.submit(
                search_products, product_name, page, location, retries, data_pipeline
            ) for page in range(1, pages + 1)
        ]
        # Wait for all tasks to complete (optional, result() blocks)
        for future in futures:
            try:
                future.result() # Retrieve result or raise exception if task failed
            except Exception as e:
                 logger.error(f"A thread encountered an error during execution: {e}", exc_info=True)


def run_scraper(limit_items=None):
    """Main function to run the scraper."""
    logger.info("Initializing scraper...")
    MAX_RETRIES = 3
    PAGES_TO_SCRAPE = 1 # Adjust how many pages per item (more pages = more potential sources)
    MAX_THREADS = 3
    LOCATION = "us" # Or specify desired Amazon region (e.g., "uk", "ca")

    
    pipeline = DataPipeline()

    # --- Item Collection ---
    all_items = []
    try:
        all_items = PROCUREMENT_DATA['Item_Name'].tolist() # Get all items from PROCUREMENT_DATA

        all_items = list(set(all_items)) # Remove duplicates
        

        ### Applying limit for items to be scraped ###
        if limit_items is not None and limit_items > 0:
             logger.info(f"Limiting processing to the first {limit_items} items.")
             all_items = all_items[:limit_items]

        if not all_items:
             logger.error("No items found to scrape.")
             return
        
        logger.info(f"Items to scrape ({len(all_items)}): {all_items}")

    except Exception as e:
         logger.error(f"Error collecting items from PROCUREMENT_DATA: {e}", exc_info=True)
         return # Exit if there's an error collecting items


    ### Scraper stars here ###
    logger.info("Scraper initialized.")
    logger.info("Starting scraper...")
    start_time = time.time()

    for item in all_items:
        threaded_search(
            item,
            PAGES_TO_SCRAPE,
            data_pipeline=pipeline,
            max_workers=MAX_THREADS,
            retries=MAX_RETRIES,
            location=LOCATION
        )

    end_time = time.time()
    logger.info(f"Scraping threads completed in {end_time - start_time:.2f} seconds.")

    ### Saving Data ###
    pipeline.save_to_json()
    logger.info("Scraping process finished.")


### Check data freshness and run scraper if needed ###
def check_and_run_scraper_if_needed(limit_items=None):
    '''checks if the average price data file exists and was updated today.
    if not, runs the scraper.'''
    
    should_scrape = False
    today = date.today()

    logger.info(f"Checking data file: {OUTPUT_JSON_FULL_PATH}")

    if not OUTPUT_JSON_FULL_PATH.exists():
        logger.info("Data file does not exist. Scraping needed.")
        should_scrape = True
    else:
        try:
            logger.info("Checking if average price data is up-to-date...")
            # Get modification time and convert to date
            last_modified_timestamp = OUTPUT_JSON_FULL_PATH.stat().st_mtime # system call to get last modified time
            # Convert to date object
            last_modified_date = date.fromtimestamp(last_modified_timestamp)
            logger.info(f"Data file last modified on: {last_modified_date}")

            if last_modified_date < today:
                logger.info(f"Data file is outdated. Last modified date is {last_modified_date}, today is {today}")
                should_scrape = True
            else:
                logger.info("Data file is up-to-date.")
        except Exception as e:
            logger.error(f"Error checking file modification date: {e}. Assuming scrape is needed.", exc_info=True)
            should_scrape = True # Scrape if unsure
    
    if should_scrape:
        logger.info("Scraper check complete.")
        logger.info("Scraping needed.")
        logger.info("Running scraper...")
        run_scraper(limit_items=limit_items) # Run the scraper if needed
    else:
        logger.info("Scraper check complete.")
        logger.info("Skipping scraping, data is current.")


### Main Execution Block ###
if __name__ == "__main__":
    
    # print(API_KEY)

    print("Running scraper directly...")
    run_scraper(limit_items=1)
    #check_and_run_scraper_if_needed(limit_items=1) # Set limit_items to 1 for testing
    print("Scraper finished.")