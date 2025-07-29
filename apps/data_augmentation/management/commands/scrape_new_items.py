from django.core.management.base import BaseCommand
from django.conf import settings
from apps.data_augmentation.services import detect_new_items, scrape_average_price_for_item
from apps.data_augmentation.models import ItemAveragePrice
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Detects and scrapes prices for new items that don\'t have price cache entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force scraping even if scraping is disabled in settings',
        )
        parser.add_argument(
            '--background',
            action='store_true',
            help='Use background tasks for scraping (requires Celery)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be scraped without actually scraping',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting new item detection and scraping...')
        )
        
        # Check if scraping is enabled
        if not getattr(settings, 'ENABLE_PRICE_SCRAPING', False) and not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    'Price scraping is disabled in settings. Use --force to override.'
                )
            )
            return
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE: No actual scraping will be performed')
            )
        
        try:
            # Detect new items
            new_items = detect_new_items()
            
            if not new_items:
                self.stdout.write(
                    self.style.SUCCESS('No new items detected. All items have price cache entries.')
                )
                return
            
            self.stdout.write(
                self.style.SUCCESS(f'Found {len(new_items)} new items: {new_items}')
            )
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.INFO('DRY RUN: Would scrape prices for the above items')
                )
                return
            
            # Handle background task option
            if options['background']:
                try:
                    from apps.data_augmentation.tasks import scrape_item_price_task
                    
                    self.stdout.write('Using background tasks for scraping...')
                    tasks = []
                    
                    for item_name in new_items:
                        task = scrape_item_price_task.delay(item_name)
                        tasks.append(task)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {len(tasks)} background scraping tasks')
                    )
                    
                except ImportError:
                    self.stdout.write(
                        self.style.ERROR('Background tasks not available. Falling back to synchronous scraping.')
                    )
                    self._scrape_items_synchronously(new_items)
            else:
                # Scrape items synchronously
                self._scrape_items_synchronously(new_items)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during new item scraping: {e}')
            )
            logger.error(f'New item scraping failed: {e}')
            raise
    
    def _scrape_items_synchronously(self, new_items):
        """Scrape items synchronously and provide progress updates."""
        today = timezone.now().date()
        scraped_count = 0
        error_count = 0
        
        for i, item_name in enumerate(new_items, 1):
            self.stdout.write(f'Processing {i}/{len(new_items)}: {item_name}')
            
            try:
                # Scrape the price
                scraped_price = scrape_average_price_for_item(item_name)
                
                if scraped_price:
                    # Save to cache
                    ItemAveragePrice.objects.create(
                        item_name=item_name,
                        date=today,
                        average_price=scraped_price,
                        details={'source': 'Amazon', 'new_item_scraping': True}
                    )
                    scraped_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Scraped price for "{item_name}": {scraped_price}')
                    )
                else:
                    error_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'✗ Could not scrape price for "{item_name}"')
                    )
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Error scraping "{item_name}": {e}')
                )
                logger.error(f'Error scraping item "{item_name}": {e}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'New item scraping completed. Scraped: {scraped_count}, Errors: {error_count}'
            )
        ) 