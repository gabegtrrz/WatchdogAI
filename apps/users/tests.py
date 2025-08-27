from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.auth import get_user

class AuthenticationTestCase(TestCase):
    """Test cases for authentication functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_view_get(self):
        """Test that login page loads correctly."""
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')
    
    def test_login_success(self):
        """Test successful login."""
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('home'))
        
        # Check that user is logged in
        user = get_user(self.client)
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, 'testuser')
    
    def test_login_failure(self):
        """Test login with wrong credentials."""
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        
        # Check that user is not logged in
        user = get_user(self.client)
        self.assertFalse(user.is_authenticated)
    
    def test_logout_view(self):
        """Test logout functionality."""
        # First login
        self.client.login(username='testuser', password='testpass123')
        user = get_user(self.client)
        self.assertTrue(user.is_authenticated)
        
        # Then logout
        response = self.client.get(reverse('users:logout'))
        self.assertRedirects(response, reverse('home'))
        
        # Check that user is logged out
        user = get_user(self.client)
        self.assertFalse(user.is_authenticated)
    
    def test_profile_view_authenticated(self):
        """Test profile view when user is authenticated."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html')
    
    def test_profile_view_unauthenticated(self):
        """Test profile view when user is not authenticated."""
        response = self.client.get(reverse('users:profile'))
        self.assertRedirects(response, f"{reverse('users:login')}?next={reverse('users:profile')}")
    
    def test_login_redirect_when_already_authenticated(self):
        """Test that authenticated users are redirected from login page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('users:login'))
        self.assertRedirects(response, reverse('home'))
    
    def test_next_parameter_redirect(self):
        """Test that login redirects to next parameter after successful login."""
        # Try to access profile without being logged in
        response = self.client.get(reverse('users:profile'))
        self.assertRedirects(response, f"{reverse('users:login')}?next={reverse('users:profile')}")
        
        # Now login
        response = self.client.post(f"{reverse('users:login')}?next={reverse('users:profile')}", {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('users:profile')) 