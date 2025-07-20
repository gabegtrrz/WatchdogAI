from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import AnalysisReport
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command to delete all AnalysisReport items.
    
    Usage:
        python manage.py delete_analysis_reports
        
    Options:
        --force: Skip confirmation prompt
        --dry-run: Show count without actually deleting
    """
    
    help = 'Delete all AnalysisReport items from the database'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt and delete immediately'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show count of items that would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        # Get count of existing analysis reports
        total_count = AnalysisReport.objects.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No AnalysisReport items found in the database.')
            )
            return
        
        # Show count and ask for confirmation
        self.stdout.write(
            f'Found {total_count} AnalysisReport item(s) in the database.'
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN: Would delete {total_count} AnalysisReport item(s)'
                )
            )
            return
        
        if not options['force']:
            # Ask for confirmation
            confirm = input(
                f'Are you sure you want to delete all {total_count} AnalysisReport item(s)? (yes/no): '
            )
            
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write(
                    self.style.WARNING('Operation cancelled by user.')
                )
                return
        
        try:
            # Use transaction to ensure atomicity
            with transaction.atomic():
                deleted_count = AnalysisReport.objects.all().delete()[0]
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully deleted {deleted_count} AnalysisReport item(s)'
                    )
                )
                
                logger.info(f'Deleted {deleted_count} AnalysisReport items via management command')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error deleting AnalysisReport items: {str(e)}')
            )
            logger.error(f'Failed to delete AnalysisReport items: {str(e)}')
            raise 