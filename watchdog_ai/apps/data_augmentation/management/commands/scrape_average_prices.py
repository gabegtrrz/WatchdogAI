import os
import yaml
from django.core.management.base import BaseCommand, CommandError
from apps.data_augmentation.services import scrape_average_price_for_item
from apps.data_augmentation.models import ItemAveragePrice
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    A Django management command to scrape average prices for items and save them to the database.
    
    This command reads a YAML configuration file to get the list of items and scrapes
    their average prices from web sources (currently Amazon). The results are cached
    in the ItemAveragePrice model for use by the data generation process.
    
    Usage:
    python manage.py scrape_average_prices <path_to_config.yml>
    """
    help = 'Scrapes average prices for items and saves them to the database.'

    def add_arguments(self, parser):
        """Adds command-line arguments: a required config path."""
        parser.add_argument(
            'config_path',
            type=str,
            help='The path to the YAML configuration file containing item list.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-scraping even if prices exist for today.'
        )

    def handle(self, *args, **options):
        """Main execution logic for the command."""
        config_path = options['config_path']
        force = options['force']

        # Load configuration and items
        self.stdout.write(self.style.SUCCESS("Loading configuration..."))
        items = self._load_items(config_path)
        
        if not items:
            raise CommandError("No items found in the configuration file.")

        self.stdout.write(f"Found {len(items)} items to scrape.")
        
        # Get today's date for caching
        today = timezone.now().date()
        
        # Track statistics
        scraped_count = 0
        cached_count = 0
        failed_count = 0
        
        for i, item_name in enumerate(items, 1):
            self.stdout.write(f"Processing item {i}/{len(items)}: {item_name}")
            
            # Check if we already have today's price for this item
            if not force:
                try:
                    existing_price = ItemAveragePrice.objects.get(
                        item_name__iexact=item_name,
                        date=today
                    )
                    self.stdout.write(f"  ✓ Cached price found: {existing_price.average_price}")
                    cached_count += 1
                    continue
                except ItemAveragePrice.DoesNotExist:
                    pass
            
            # Scrape the price
            try:
                average_price = scrape_average_price_for_item(item_name)
                
                if average_price:
                    # Save to database
                    ItemAveragePrice.objects.create(
                        item_name=item_name,
                        date=today,
                        average_price=average_price,
                        details={'source': 'Amazon', 'scraped_at': timezone.now().isoformat()}
                    )
                    self.stdout.write(f"  ✓ Scraped price: {average_price}")
                    scraped_count += 1
                else:
                    self.stdout.write(f"  ✗ No price found for: {item_name}")
                    failed_count += 1
                    
            except Exception as e:
                self.stdout.write(f"  ✗ Error scraping {item_name}: {e}")
                failed_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f"\nScraping completed:"))
        self.stdout.write(f"  - Scraped: {scraped_count}")
        self.stdout.write(f"  - Cached: {cached_count}")
        self.stdout.write(f"  - Failed: {failed_count}")
        self.stdout.write(f"  - Total: {len(items)}")

    def _load_items(self, config_path):
        """Loads the item list from the configuration file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise CommandError(f"Could not load or parse configuration file: {e}")

        # Extract the data_generator section
        data_generator = config.get('data_generator', {})
        
        # Get the item source file path
        item_source_file = data_generator.get('item_source_file')
        if not item_source_file:
            raise CommandError("No 'item_source_file' specified in the configuration.")

        # Load items from the source file
        try:
            with open(item_source_file, 'r', encoding='utf-8') as f:
                items = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise CommandError(f"Item source file not found at: {item_source_file}")
        except UnicodeDecodeError as e:
            raise CommandError(f"Error reading item source file encoding: {e}. Please ensure the file is UTF-8 encoded.")
        
        return items 