import time
import requests
import csv
from dataclasses import dataclass, field, fields, asdict
from bs4 import BeautifulSoup
import logging, os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
import os.path
import sys

# Add the 'data' subfolder to the Python module search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data')))

# Import METHODS_DATA from procurement_data_config.py
from procurement_data_config import METHODS_DATA

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = '39460d69-2a10-482d-bd64-5e96132d14f1'
USD_TO_PHP = 56.0  # Conversion rate: 1 USD = 56 PHP (adjust as needed)

@dataclass
class ProductData:
    category: str = ""
    pricing_unit: str = "₱"
    avg_price: float = None

    def __post_init__(self):
        self.check_string_fields()
    
    def check_string_fields(self):
        for field in fields(self):
            if isinstance(getattr(self, field.name), str):
                value = getattr(self, field.name).strip()
                if not value:
                    setattr(self, field.name, f"No {field.name}")
                else:
                    setattr(self, field.name, value)

class DataPipeline:
    def __init__(self, csv_filename="", folder_path=""):
        self.price_sums = {method: 0.0 for method in METHODS_DATA.keys()}
        self.price_counts = {method: 0 for method in METHODS_DATA.keys()}
        os.makedirs(folder_path, exist_ok=True)
        self.csv_filename = os.path.join(folder_path, csv_filename) if folder_path else csv_filename
    
    def add_data(self, category, price):
        if price > 0:
            self.price_sums[category] += price
            self.price_counts[category] += 1
    
    def save_to_csv(self):
        data_to_save = []
        for category in self.price_sums:
            if self.price_counts[category] > 0:
                avg_price = self.price_sums[category] / self.price_counts[category]
                data_to_save.append(ProductData(category=category, avg_price=avg_price))
        
        if not data_to_save:
            logger.info("No data to save to CSV")
            return

        keys = [field.name for field in fields(data_to_save[0])]
        with open(self.csv_filename, mode="w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=keys)
            writer.writeheader()
            writer.writerows([asdict(item) for item in data_to_save])
        
        logger.info(f"Saved average prices to {self.csv_filename}")

def get_scrapeops_url(url, location="us"):
    payload = {
        "api_key": API_KEY,
        "url": url,
        "country": location
    }
    return "https://proxy.scrapeops.io/v1/?" + urlencode(payload)

def clean_price(price_str, pricing_unit):
    if not price_str or pricing_unit not in price_str:
        return 0.0
    try:
        cleaned = price_str.replace(pricing_unit, "").replace(",", "").strip()
        cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '.')
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        logger.warning(f"Could not convert price '{price_str}' to float")
        return 0.0

def search_products(product_name: str, category: str, page_number=1, location="us", retries=3, data_pipeline=None):
    tries = 0
    success = False

    while tries < retries and not success:
        try:
            url = get_scrapeops_url(
                f"https://www.amazon.com/s?k={product_name}&page={page_number}", 
                location=location,
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            
            logger.info(f"Successfully fetched page {page_number} for {product_name}")
            soup = BeautifulSoup(resp.text, 'html.parser')

            for ad in soup.find_all("div", class_="Adholder"):
                ad.decompose()

            divs = soup.find_all('div')
            last_title = ""

            for div in divs:
                h2 = div.find('h2')
                if not h2 or not h2.text.strip() or h2.text.strip() == last_title:
                    continue

                last_title = h2.text.strip()

                symbol_element = div.find('span', class_="a-price-symbol")
                usd_symbol = symbol_element.text if symbol_element else "$"
                
                prices = div.find_all('span', class_="a-offscreen")
                if prices:
                    usd_price = clean_price(prices[0].text, usd_symbol)
                    php_price = usd_price * USD_TO_PHP if usd_price else 0.0
                    data_pipeline.add_data(category, php_price)

            success = True

        except Exception as e:
            tries += 1
            logger.warning(f"Failed to scrape page {page_number}: {str(e)}, tries left: {retries-tries}")
            time.sleep(1)

    if not success:
        logger.error(f"Failed to scrape page {page_number} for {product_name}, retries exceeded: {retries}")

    print(f"Completed scrape_products for: {product_name}, page: {page_number}")

def threaded_search(product_name, category, pages, data_pipeline, max_workers=5, location="us", retries=3):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                search_products, product_name, category, page, location, retries, data_pipeline
            ) for page in range(1, pages + 1)
        ]
        for future in futures:
            future.result()

if __name__ == "__main__":
    MAX_RETRIES = 2
    PAGES = 5
    MAX_THREADS = 3
    LOCATION = "us"
    OUTPUT_FOLDER = "scraped_data"
    OUTPUT_CSV = "average_prices.csv"

    pipeline = DataPipeline(csv_filename=OUTPUT_CSV, folder_path=OUTPUT_FOLDER)

    for method, details in METHODS_DATA.items():
        for item in details["items"].keys():
            threaded_search(
                product_name=item,
                category=method,
                pages=PAGES,
                data_pipeline=pipeline,
                max_workers=MAX_THREADS,
                retries=MAX_RETRIES,
                location=LOCATION
            )

    pipeline.save_to_csv()