"""
Test script to demonstrate rate limiting functionality.
This is for testing purposes only - not part of the main application.
"""

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from .. views import check_rate_limit, apply_rate_limit

def test_rate_limiting():
    """
    Demonstrate how rate limiting works with different actions.
    """
    # Create a mock request
    factory = RequestFactory()
    request = factory.post('/fake-url/')
    request.user = AnonymousUser()
    
    print("🧪 Testing Rate Limiting Functionality")
    print("=" * 50)
    
    # Test 1: Selection requests (5 attempts per minute)
    print("\n📋 Test 1: Selection Requests (5 attempts per minute)")
    for i in range(7):  # Try 7 times (should fail after 5)
        is_allowed, remaining, reset_time = check_rate_limit(request, 'select_transactions')
        status = "✅ ALLOWED" if is_allowed else "❌ BLOCKED"
        print(f"  Attempt {i+1}: {status} (Remaining: {remaining}, Reset in: {reset_time}s)")
    
    # Test 2: Analysis requests (2 attempts per 5 minutes)
    print("\n🔬 Test 2: Analysis Requests (2 attempts per 5 minutes)")
    for i in range(4):  # Try 4 times (should fail after 2)
        is_allowed, remaining, reset_time = check_rate_limit(request, 'run_analysis')
        status = "✅ ALLOWED" if is_allowed else "❌ BLOCKED"
        print(f"  Attempt {i+1}: {status} (Remaining: {remaining}, Reset in: {reset_time}s)")
    
    # Test 3: Different users have separate limits
    print("\n👥 Test 3: Different Users Have Separate Limits")
    request2 = factory.post('/fake-url/')
    request2.user = AnonymousUser()  # Different user
    
    is_allowed1, _, _ = check_rate_limit(request, 'select_transactions')
    is_allowed2, _, _ = check_rate_limit(request2, 'select_transactions')
    print(f"  User 1 allowed: {is_allowed1}")
    print(f"  User 2 allowed: {is_allowed2}")
    
    print("\n✅ Rate limiting test completed!")

if __name__ == "__main__":
    # Clear cache before testing
    cache.clear()
    test_rate_limiting() 