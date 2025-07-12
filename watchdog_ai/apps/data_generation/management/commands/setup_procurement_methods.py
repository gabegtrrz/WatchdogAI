from django.core.management.base import BaseCommand
from apps.core.models import ProcurementMethod


class Command(BaseCommand):
    """
    A Django management command to set up procurement methods in the database.
    
    This command creates the procurement methods with their proper names
    as specified in the procurement requirements.
    """
    help = 'Sets up procurement methods in the database with proper names'

    def handle(self, *args, **options):
        """Main execution logic for the command."""
        self.stdout.write(self.style.SUCCESS("Setting up procurement methods..."))  # type: ignore
        
        # Define the procurement methods
        procurement_methods = [
            'Competitive Bidding',
            'Negotiated Procurement',
            'Negotiated Procurement (Small Value Procurement)',
            'Negotiated Procurement (Agency-to-Agency)',
            'Negotiated Procurement (Two Failed Biddings)',
            'Repeat Order',
            'Direct Contracting'
        ]
        
        created_count = 0
        
        for method_name in procurement_methods:
            # Try to get existing method or create new one
            method, created = ProcurementMethod.objects.get_or_create(name=method_name)
            
            if created:
                self.stdout.write(f"Created: {method_name}")
                created_count += 1
            else:
                self.stdout.write(f"Already exists: {method_name}")
        
        self.stdout.write(self.style.SUCCESS(f"Setup complete! Created: {created_count} new methods"))  # type: ignore
        
        # Display all procurement methods
        all_methods = ProcurementMethod.objects.all().order_by('name')
        self.stdout.write("\nCurrent procurement methods in database:")
        for method in all_methods:
            self.stdout.write(f"  - {method.name}") 