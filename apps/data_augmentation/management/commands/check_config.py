from django.core.management.base import BaseCommand
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Check current configuration settings for debugging'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Configuration Check ==='))
        
        # Data Augmentation Settings
        self.stdout.write('\n--- Data Augmentation Settings ---')
        self.stdout.write(f'ENABLE_PRICE_SCRAPING: {getattr(settings, "ENABLE_PRICE_SCRAPING", "Not set")}')
        self.stdout.write(f'SCRAPING_TIMEOUT: {getattr(settings, "SCRAPING_TIMEOUT", "Not set")} seconds')
        
        # Railway Settings
        self.stdout.write('\n--- Railway Settings ---')
        self.stdout.write(f'RAILWAY_STATIC_URL: {getattr(settings, "RAILWAY_STATIC_URL", "Not set")}')
        self.stdout.write(f'RAILWAY_PUBLIC_DOMAIN: {getattr(settings, "RAILWAY_PUBLIC_DOMAIN", "Not set")}')
        
        # Environment Variables
        self.stdout.write('\n--- Environment Variables ---')
        self.stdout.write(f'PORT: {os.environ.get("PORT", "Not set")}')
        self.stdout.write(f'DATABASE_URL: {"Set" if os.environ.get("DATABASE_URL") else "Not set"}')
        self.stdout.write(f'DEBUG: {os.environ.get("DEBUG", "Not set")}')
        
        # ScrapeOps API Key
        scrapeops_key = os.environ.get("SCRAPEOPS_API_KEY")
        if scrapeops_key:
            self.stdout.write(f'SCRAPEOPS_API_KEY: {"Set" if scrapeops_key != "YOUR_API_KEY_HERE" else "Default placeholder"}')
        else:
            self.stdout.write('SCRAPEOPS_API_KEY: Not set')
        
        # Database Configuration
        self.stdout.write('\n--- Database Configuration ---')
        db_engine = getattr(settings, 'DATABASES', {}).get('default', {}).get('ENGINE', 'Not configured')
        self.stdout.write(f'Database Engine: {db_engine}')
        
        # Static Files
        self.stdout.write('\n--- Static Files ---')
        static_root = getattr(settings, 'STATIC_ROOT', 'Not set')
        self.stdout.write(f'STATIC_ROOT: {static_root}')
        
        # Allowed Hosts
        self.stdout.write('\n--- Security ---')
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        self.stdout.write(f'ALLOWED_HOSTS: {allowed_hosts}')
        
        self.stdout.write(self.style.SUCCESS('\n=== Configuration Check Complete ===')) 