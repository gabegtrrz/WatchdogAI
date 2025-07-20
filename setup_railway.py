#!/usr/bin/env python3
"""
Railway Deployment Setup Script
This script helps prepare your Django project for Railway deployment.
"""

import os
import secrets
import string
from pathlib import Path

def generate_secret_key():
    """Generate a secure Django secret key."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return ''.join(secrets.choice(alphabet) for _ in range(50))

def create_env_template():
    """Create a template .env file for Railway deployment."""
    env_template = f"""# Django Settings
SECRET_KEY={generate_secret_key()}
DEBUG=False

# Database (Railway will provide these automatically)
# PGDATABASE=your-database-name
# PGUSER=your-database-user
# PGPASSWORD=your-database-password
# PGHOST=your-database-host
# PGPORT=5432

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis (for Celery - Railway will provide if you add Redis service)
# REDIS_URL=redis://localhost:6379/0

# Frontend URL (if applicable)
FRONTEND_URL=https://your-frontend-domain.com

# Admin Email
ADMIN_EMAIL=admin@yourdomain.com
"""
    
    with open('.env.template', 'w') as f:
        f.write(env_template)
    
    print("✅ Created .env.template file")
    print("📝 Please copy this to Railway environment variables")

def check_requirements():
    """Check if all required packages are in requirements.txt."""
    required_packages = [
        'gunicorn',
        'whitenoise',
        'psycopg2-binary',
        'django-cors-headers',
        'python-dotenv'
    ]
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        missing = []
        for package in required_packages:
            if package not in requirements:
                missing.append(package)
        
        if missing:
            print(f"❌ Missing packages in requirements.txt: {', '.join(missing)}")
            return False
        else:
            print("✅ All required packages are in requirements.txt")
            return True
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False

def check_files():
    """Check if all required deployment files exist."""
    required_files = [
        'Procfile',
        'runtime.txt',
        'railway.json',
        'watchdog_ai/watchdog_ai/settings_production.py'
    ]
    
    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)
    
    if missing:
        print(f"❌ Missing files: {', '.join(missing)}")
        return False
    else:
        print("✅ All required deployment files exist")
        return True

def main():
    """Main setup function."""
    print("🚀 Railway Deployment Setup")
    print("=" * 40)
    
    # Check current directory
    if not Path('watchdog_ai/manage.py').exists():
        print("❌ Please run this script from the project root directory")
        return
    
    print("\n📋 Checking deployment requirements...")
    
    # Check files
    files_ok = check_files()
    
    # Check requirements
    requirements_ok = check_requirements()
    
    # Create env template
    create_env_template()
    
    print("\n🎯 Next Steps:")
    print("1. Copy the contents of .env.template to Railway environment variables")
    print("2. Add PostgreSQL database service in Railway")
    print("3. Add Redis service in Railway (optional, for Celery)")
    print("4. Deploy your repository to Railway")
    print("5. Run migrations: railway run python manage.py migrate")
    print("6. Create superuser: railway run python manage.py createsuperuser")
    
    if files_ok and requirements_ok:
        print("\n✅ Your project is ready for Railway deployment!")
    else:
        print("\n⚠️  Please fix the issues above before deploying")

if __name__ == "__main__":
    main() 