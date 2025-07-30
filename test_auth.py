#!/usr/bin/env python
"""
Simple test script to verify the authentication system is properly configured.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchdog_ai.production_settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

def test_auth_system():
    """Test the authentication system."""
    print("Testing WatchdogAI Authentication System...")
    print("=" * 50)
    
    # Test 1: Check if we can create a test user
    try:
        # Create a test user
        user, created = User.objects.get_or_create(
            username='test_auth_user',
            defaults={
                'email': 'test@example.com',
                'is_active': True
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            print("✓ Test user created successfully")
        else:
            print("✓ Test user already exists")
    except Exception as e:
        print(f"✗ Error creating test user: {e}")
        return False
    
    # Test 2: Test login functionality
    try:
        client = Client()
        login_url = reverse('users:login')
        response = client.get(login_url)
        if response.status_code == 200:
            print("✓ Login page loads correctly")
        else:
            print(f"✗ Login page returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error testing login page: {e}")
        return False
    
    # Test 3: Test successful login
    try:
        response = client.post(login_url, {
            'username': 'test_auth_user',
            'password': 'testpass123'
        })
        if response.status_code == 302:  # Redirect after successful login
            print("✓ Login functionality works")
        else:
            print(f"✗ Login failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error testing login: {e}")
        return False
    
    # Test 4: Test logout functionality
    try:
        logout_url = reverse('users:logout')
        response = client.get(logout_url)
        if response.status_code == 302:  # Redirect after logout
            print("✓ Logout functionality works")
        else:
            print(f"✗ Logout failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error testing logout: {e}")
        return False
    
    # Test 5: Test profile page (should redirect to login when not authenticated)
    try:
        profile_url = reverse('users:profile')
        response = client.get(profile_url)
        if response.status_code == 302:  # Should redirect to login
            print("✓ Profile page properly protected")
        else:
            print(f"✗ Profile page not properly protected: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error testing profile protection: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✓ All authentication tests passed!")
    print("\nAuthentication system is ready to use.")
    print("\nTo get started:")
    print("1. Create a superuser: python manage.py create_superuser")
    print("2. Start the server: python manage.py runserver")
    print("3. Visit: http://localhost:8000/users/login/")
    
    return True

if __name__ == '__main__':
    success = test_auth_system()
    sys.exit(0 if success else 1) 