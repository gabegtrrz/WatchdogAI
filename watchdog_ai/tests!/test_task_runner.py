#!/usr/bin/env python
"""
Simple test runner for the anomaly detection task.
This script runs the tests to verify the task works correctly.
"""
import os
import sys
import django
from django.conf import settings

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'watchdog_ai.settings')
django.setup()

from django.test.utils import get_runner
from django.conf import settings


def run_tests():
    """Run the anomaly detection task tests."""
    print("Running anomaly detection task tests...")
    print("=" * 50)
    
    # Get the test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run the specific test file
    test_labels = ['apps.ai_analytics.tests.test_tasks']
    
    # Run the tests
    failures = test_runner.run_tests(test_labels)
    
    if failures:
        print(f"\n❌ Tests failed: {failures}")
        return False
    else:
        print("\n✅ All tests passed!")
        return True


def test_task_directly():
    """Test the task function directly with mock data."""
    print("\nTesting task function directly...")
    print("-" * 30)
    
    try:
        from apps.ai_analytics.tasks import perform_anomaly_detection
        from apps.core.models import Transaction, AnalysisReport, ProcurementMethod
        from decimal import Decimal
        from django.utils import timezone
        
        # Create test data
        procurement_method = ProcurementMethod.objects.create(name="Test Method")
        
        transaction = Transaction.objects.create(
            transaction_id="DIRECT_TEST",
            project_name="Direct Test Project",
            item_name="Test Item",
            quantity=5,
            unit_purchase_price=Decimal("100.00"),
            total_purchase_price=Decimal("500.00"),
            supplier="Test Supplier",
            procurement_officer="Test Officer",
            invoice_number="INV_TEST",
            payment_receipt_number="REC_TEST",
            transaction_date=timezone.now().date(),
            procurement_method=procurement_method
        )
        
        # Test the task
        result = perform_anomaly_detection([transaction.id], 0.1)
        
        print(f"Task result: {result}")
        
        # Check if report was created
        reports = AnalysisReport.objects.filter(transaction=transaction)
        print(f"Reports created: {reports.count()}")
        
        if reports.exists():
            report = reports.first()
            print(f"Report details:")
            print(f"  - Is anomaly: {report.is_anomaly}")
            print(f"  - Anomaly score: {report.anomaly_score}")
            print(f"  - Contamination: {report.contamination_param}")
            print(f"  - Error message: {report.error_message}")
            print(f"  - Analysis run ID: {report.analysis_run_id}")
        
        # Clean up
        transaction.delete()
        procurement_method.delete()
        
        print("✅ Direct task test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Direct task test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("WatchdogAI - Anomaly Detection Task Test Runner")
    print("=" * 50)
    
    # Run the Django tests
    test_success = run_tests()
    
    # Run direct task test
    direct_success = test_task_directly()
    
    print("\n" + "=" * 50)
    if test_success and direct_success:
        print("🎉 All tests passed! The anomaly detection task is working correctly.")
    else:
        print("❌ Some tests failed. Please check the output above for details.")
    
    sys.exit(0 if (test_success and direct_success) else 1) 