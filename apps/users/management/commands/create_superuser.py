from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.management import call_command
import getpass

class Command(BaseCommand):
    """Custom command to create a superuser with interactive prompts."""
    
    help = 'Create a superuser account for WatchdogAI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the superuser',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the superuser',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the superuser (not recommended for security)',
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        
        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING('A superuser already exists. Use Django admin or create another user.')
            )
            return
        
        # Get username
        username = options['username']
        if not username:
            username = input('Enter username: ').strip()
            if not username:
                self.stdout.write(self.style.ERROR('Username is required.'))
                return
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR(f'User with username "{username}" already exists.')
            )
            return
        
        # Get email
        email = options['email']
        if not email:
            email = input('Enter email (optional): ').strip()
        
        # Get password
        password = options['password']
        if not password:
            password = getpass.getpass('Enter password: ')
            if not password:
                self.stdout.write(self.style.ERROR('Password is required.'))
                return
            
            password_confirm = getpass.getpass('Confirm password: ')
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match.'))
                return
        
        # Create superuser
        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser "{username}" created successfully!\n'
                    f'You can now login at /users/login/ or access admin at /admin/'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            ) 