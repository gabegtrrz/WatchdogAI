"""
Simple tests for the anomaly detection service.

Covers:
- DataFrame conversion from Transaction
- Fallback result structure
"""
import json
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.core.models import Transaction, ProcurementMethod
from apps.ai_analytics.services import anomaly_detection

class TestAnomalyDetectionService(TestCase):
    """Minimal tests for anomaly_detection service."""
    def setUp(self):
        self.procurement_method = ProcurementMethod.objects.create(name="Public Bidding")
        self.transaction = Transaction.objects.create(
            transaction_id="TEST001",
            project_name="Test Project",
            item_name="Test Item",
            quantity=10,
            unit_purchase_price=Decimal("100.00"),
            total_purchase_price=Decimal("1000.00"),
            supplier="Test Supplier",
            procurement_officer="Test Officer",
            invoice_number="INV001",
            payment_receipt_number="REC001",
            transaction_date=timezone.now().date(),
            procurement_method=self.procurement_method,
            approved_budget=Decimal("1200.00")
        )

    def test_model_to_dataframe(self):
        """Test converting a Transaction to DataFrame."""
        df = anomaly_detection.model_to_dataframe(self.transaction)
        self.assertEqual(df.shape[0], 1)
        self.assertIn('transaction_id', df.columns)
        self.assertEqual(df.iloc[0]['transaction_id'], "TEST001")
        self.assertEqual(df.iloc[0]['project_name'], "Test Project")
        self.assertEqual(df.iloc[0]['item_name'], "Test Item")
        self.assertEqual(df.iloc[0]['quantity'], 10)
        self.assertEqual(df.iloc[0]['supplier'], "Test Supplier")

    def test_get_fallback_result(self):
        """Test fallback result structure."""
        result = anomaly_detection._get_fallback_result()
        self.assertIn('is_anomaly', result)
        self.assertIn('anomaly_score', result)
        self.assertIn('shap_values_json', result)
        shap_data = json.loads(result['shap_values_json'])
        self.assertIn('values', shap_data)
        self.assertIn('base_values', shap_data)
        self.assertIn('feature_names', shap_data) 