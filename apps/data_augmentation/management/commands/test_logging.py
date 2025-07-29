from django.core.management.base import BaseCommand
from apps.data_augmentation.services import test_logging
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test logging configuration for data_augmentation app'

    def handle(self, *args, **options):
        self.stdout.write("Testing logging configuration...")
        
        # Check logger levels
        self.stdout.write(f"Logger level: {logger.level}")
        self.stdout.write(f"Logger effective level: {logger.getEffectiveLevel()}")
        
        # Force logger to DEBUG level
        logger.setLevel(logging.DEBUG)
        self.stdout.write(f"Logger level after setting to DEBUG: {logger.level}")
        
        # Test the logging function
        result = test_logging()
        self.stdout.write(f"Result: {result}")
        
        # Test direct logging from this command
        logger.debug("DEBUG: Direct logging from command")
        logger.info("INFO: Direct logging from command")
        logger.warning("WARNING: Direct logging from command")
        logger.error("ERROR: Direct logging from command")
        
        self.stdout.write(self.style.SUCCESS("Logging test completed!"))