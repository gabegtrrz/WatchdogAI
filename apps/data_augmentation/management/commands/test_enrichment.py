from django.core.management.base import BaseCommand
from django.conf import settings
from apps.core.models import Transaction
from apps.data_augmentation.services import enrich_transaction_list
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test the transaction enrichment process'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Number of transactions to test (default: 5)'
        )
        parser.add_argument(
            '--enable-scraping',
            action='store_true',
            help='Enable price scraping (overrides settings)'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        enable_scraping = options['enable_scraping']
        
        # Temporarily override settings if requested
        if enable_scraping:
            settings.ENABLE_PRICE_SCRAPING = True
            self.stdout.write(self.style.WARNING('Price scraping enabled for this test'))
        
        # Get some transactions to test
        transactions = Transaction.objects.all()[:limit]
        
        if not transactions:
            self.stdout.write(self.style.ERROR('No transactions found in database'))
            return
        
        self.stdout.write(f'Testing enrichment with {len(transactions)} transactions...')
        
        # Test the enrichment process
        try:
            stats = enrich_transaction_list(transactions)
            
            self.stdout.write(self.style.SUCCESS('Enrichment completed successfully!'))
            self.stdout.write(f'Updated: {stats.get("updated", 0)}')
            self.stdout.write(f'Skipped: {stats.get("skipped", 0)}')
            self.stdout.write(f'Errors: {stats.get("errors", 0)}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Enrichment failed: {e}'))
            logger.exception('Enrichment test failed') 