from django.core.management.base import BaseCommand
from apps.data_augmentation.services import test_logging
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test logging configuration for data_augmentation app'

    def handle(self, *args, **options):
        self.stdout.write("Testing logging configuration...")
        self.stdout.write("=" * 50)
        
        # Test the logging function from services
        self.stdout.write("1. Testing logging from services.py...")
        result = test_logging()
        self.stdout.write(f"   Result: {result}")
        
        # Test direct logging from this command
        self.stdout.write("2. Testing direct logging from command...")
        logger.debug("DEBUG: Direct logging from command")
        logger.info("INFO: Direct logging from command")
        logger.warning("WARNING: Direct logging from command")
        logger.error("ERROR: Direct logging from command")
        
        # Test specific data_augmentation logging
        self.stdout.write("3. Testing data_augmentation specific logging...")
        data_aug_logger = logging.getLogger('apps.data_augmentation')
        data_aug_logger.debug("DEBUG: Data augmentation app logging")
        data_aug_logger.info("INFO: Data augmentation app logging")
        data_aug_logger.warning("WARNING: Data augmentation app logging")
        data_aug_logger.error("ERROR: Data augmentation app logging")
        
        # Test services specific logging
        self.stdout.write("4. Testing services specific logging...")
        services_logger = logging.getLogger('apps.data_augmentation.services')
        services_logger.debug("DEBUG: Services module logging")
        services_logger.info("INFO: Services module logging")
        services_logger.warning("WARNING: Services module logging")
        services_logger.error("ERROR: Services module logging")
        
        self.stdout.write("=" * 50)
        self.stdout.write(self.style.SUCCESS("Logging test completed!"))
        self.stdout.write("Check console output and logs/watchdog_ai.log file for results.")