from django.core.management.base import BaseCommand
from watchdog_ai.apps.data_augmentation import services

class Command(BaseCommand):
    help = 'Enriches transactions with average price data by scraping the web.'

    def handle(self, *args, **kwargs):
        # entry point
        self.stdout.write(self.style.SUCCESS('Starting transaction enrichment process...'))
        try:
            services.enrich_transactions()
            self.stdout.write(self.style.SUCCESS('Transaction enrichment process completed successfully.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An error occurred during the enrichment process: {e}'))