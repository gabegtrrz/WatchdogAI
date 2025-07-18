#!/usr/bin/env python
"""
Simple test script to verify the anomaly detection service works correctly.
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

from decimal import Decimal
from django.utils import timezone
from apps.core.models import Transaction, AnalysisReport, ProcurementMethod
from apps.ai_analytics.services import anomaly_detection


def test_anomaly_detection():
    """Test the anomaly detection service with a sample transaction."""
    print("Testing anomaly detection service...")
    print("=" * 50)
    
    try:
        # Create test data
        procurement_method = ProcurementMethod.objects.create(name="Public Bidding")
        
        transaction = Transaction.objects.create(
            transaction_id="TEST_ANOMALY_001",
            project_name="Test Anomaly Project",
            item_name="Test Item",
            quantity=10,
            unit_purchase_price=Decimal("100.00"),
            total_purchase_price=Decimal("1000.00"),
            supplier="Test Supplier",
            procurement_officer="Test Officer",
            invoice_number="INV_TEST_001",
            payment_receipt_number="REC_TEST_001",
            transaction_date=timezone.now().date(),
            procurement_method=procurement_method,
            approved_budget=Decimal("1200.00"),
            # Add some timeline data
            invitation_to_bid_posting_date=timezone.now().date(),
            bid_submission_deadline=timezone.now().date(),
            bid_opening_date=timezone.now().date(),
            notice_of_award_date=timezone.now().date(),
            contract_signing_date=timezone.now().date(),
        )
        
        print(f"Created test transaction: {transaction.transaction_id}")
        
        # Test the anomaly detection
        print("Running anomaly detection...")
        result = anomaly_detection.run_complete_analysis(transaction, 0.1)
        
        print(f"Anomaly detection result:")
        print(f"  - Is anomaly: {result['is_anomaly']}")
        print(f"  - Anomaly score: {result['anomaly_score']}")
        print(f"  - SHAP values: {result['shap_values_json'][:100]}...")
        
        # Clean up
        transaction.delete()
        procurement_method.delete()
        
        print("✅ Anomaly detection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Anomaly detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_function():
    """Test the task function directly."""
    print("\nTesting task function...")
    print("-" * 30)
    
    try:
        from apps.ai_analytics.tasks import perform_anomaly_detection
        
        # Create test data
        procurement_method = ProcurementMethod.objects.create(name="Task Test Method")
        
        transaction = Transaction.objects.create(
            transaction_id="TASK_TEST_001",
            project_name="Task Test Project",
            item_name="Task Test Item",
            quantity=5,
            unit_purchase_price=Decimal("50.00"),
            total_purchase_price=Decimal("250.00"),
            supplier="Task Test Supplier",
            procurement_officer="Task Test Officer",
            invoice_number="INV_TASK_001",
            payment_receipt_number="REC_TASK_001",
            transaction_date=timezone.now().date(),
            procurement_method=procurement_method,
            approved_budget=Decimal("300.00"),
        )
        
        print(f"Created test transaction: {transaction.transaction_id}")
        
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
        
        print("✅ Task function test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Task function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("WatchdogAI - Anomaly Detection Test")
    print("=" * 50)
    
    # Test anomaly detection service
    service_success = test_anomaly_detection()
    
    # Test task function
    task_success = test_task_function()
    
    print("\n" + "=" * 50)
    if service_success and task_success:
        print("🎉 All tests passed! The anomaly detection is working correctly.")
    else:
        print("❌ Some tests failed. Please check the output above for details.")
    
    sys.exit(0 if (service_success and task_success) else 1) 