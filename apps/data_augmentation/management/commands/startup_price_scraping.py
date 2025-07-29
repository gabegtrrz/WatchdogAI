from django.core.management.base import BaseCommand
from django.conf import settings
from apps.data_augmentation.services import startup_price_scraping
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Runs startup price scraping for all unique items in the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force scraping even if scraping is disabled in settings',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be scraped without actually scraping',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting startup price scraping process...')
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
            # TODO: Implement dry run functionality
            return
        
        try:
            # Run the startup price scraping
            startup_price_scraping()
            
            self.stdout.write(
                self.style.SUCCESS('Startup price scraping completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during startup price scraping: {e}')
            )
            logger.error(f'Startup price scraping failed: {e}')
            raise 