"""
Tests for the anomaly detection Celery task.
"""
import uuid
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from apps.core.models import Transaction, AnalysisReport, ProcurementMethod
from apps.ai_analytics.tasks import perform_anomaly_detection
from apps.ai_analytics.services import anomaly_detection


class TestAnomalyDetectionTask(TestCase):
    """Test cases for the perform_anomaly_detection Celery task."""
    
    def setUp(self):
        """Set up test data."""
        # Create a procurement method
        self.procurement_method = ProcurementMethod.objects.create(
            name="Public Bidding"
        )
        
        # Create test transactions
        self.transaction1 = Transaction.objects.create(
            transaction_id="TEST001",
            project_name="Test Project 1",
            item_name="Test Item 1",
            quantity=10,
            unit_purchase_price=Decimal("100.00"),
            total_purchase_price=Decimal("1000.00"),
            supplier="Test Supplier 1",
            procurement_officer="Test Officer 1",
            invoice_number="INV001",
            payment_receipt_number="REC001",
            transaction_date=timezone.now().date(),
            procurement_method=self.procurement_method
        )
        
        self.transaction2 = Transaction.objects.create(
            transaction_id="TEST002",
            project_name="Test Project 2",
            item_name="Test Item 2",
            quantity=5,
            unit_purchase_price=Decimal("200.00"),
            total_purchase_price=Decimal("1000.00"),
            supplier="Test Supplier 2",
            procurement_officer="Test Officer 2",
            invoice_number="INV002",
            payment_receipt_number="REC002",
            transaction_date=timezone.now().date(),
            procurement_method=self.procurement_method
        )
        
        self.transaction_ids = [self.transaction1.id, self.transaction2.id]
        self.contamination = 0.1
    
    def test_task_successful_execution(self):
        """Test that the task executes successfully with valid inputs."""
        # Mock the anomaly detection service
        mock_results = {
            'is_anomaly': True,
            'anomaly_score': 0.8,
            'shap_values_json': '{"values": [0.1, 0.2], "base_values": 0.5, "feature_names": ["feature1", "feature2"]}'
        }
        
        with patch.object(anomaly_detection, 'run_complete_analysis', return_value=mock_results) as mock_analysis:
            # Execute the task
            result = perform_anomaly_detection(self.transaction_ids, self.contamination)
            
            # Verify the task completed successfully
            self.assertEqual(result['status'], 'Completed')
            self.assertIn('analysis_run_id', result)
            
            # Verify analysis reports were created
            reports = AnalysisReport.objects.filter(
                transaction__id__in=self.transaction_ids,
                contamination_param=self.contamination
            )
            self.assertEqual(reports.count(), 2)
            
            # Verify each report has the correct data
            for report in reports:
                self.assertEqual(report.is_anomaly, True)
                self.assertEqual(report.anomaly_score, 0.8)
                self.assertIsNotNone(report.shap_values)
                self.assertEqual(report.contamination_param, self.contamination)
                self.assertIsNotNone(report.analysis_run_id)
            
            # Verify the analysis service was called for each transaction
            self.assertEqual(mock_analysis.call_count, 2)
    
    def test_task_with_existing_reports(self):
        """Test that the task handles existing reports correctly."""
        # Create an existing report
        existing_report = AnalysisReport.objects.create(
            transaction=self.transaction1,
            contamination_param=self.contamination,
            is_anomaly=False,
            anomaly_score=0.3,
            shap_values='{"existing": "data"}'
        )
        
        mock_results = {
            'is_anomaly': True,
            'anomaly_score': 0.8,
            'shap_values_json': '{"values": [0.1, 0.2], "base_values": 0.5, "feature_names": ["feature1", "feature2"]}'
        }
        
        with patch.object(anomaly_detection, 'run_complete_analysis', return_value=mock_results) as mock_analysis:
            # Execute the task
            result = perform_anomaly_detection(self.transaction_ids, self.contamination)
            
            # Verify the task completed successfully
            self.assertEqual(result['status'], 'Completed')
            
            # Verify only one new report was created (for transaction2)
            reports = AnalysisReport.objects.filter(
                transaction__id__in=self.transaction_ids,
                contamination_param=self.contamination
            )
            self.assertEqual(reports.count(), 2)
            
            # Verify the existing report was updated with the new run_id
            existing_report.refresh_from_db()
            self.assertIsNotNone(existing_report.analysis_run_id)
            
            # Verify the analysis service was only called once (for transaction2)
            self.assertEqual(mock_analysis.call_count, 1)
    
    def test_task_with_analysis_error(self):
        """Test that the task handles analysis errors gracefully."""
        # Mock the anomaly detection service to raise an exception
        with patch.object(anomaly_detection, 'run_complete_analysis', side_effect=Exception("Analysis failed")):
            # Execute the task
            result = perform_anomaly_detection(self.transaction_ids, self.contamination)
            
            # Verify the task completed successfully despite errors
            self.assertEqual(result['status'], 'Completed')
            
            # Verify error reports were created
            error_reports = AnalysisReport.objects.filter(
                transaction__id__in=self.transaction_ids,
                contamination_param=self.contamination,
                error_message__isnull=False
            )
            self.assertEqual(error_reports.count(), 2)
            
            # Verify error reports have error messages
            for report in error_reports:
                self.assertIn("Analysis failed", report.error_message)
                self.assertIsNone(report.is_anomaly)
                self.assertIsNone(report.anomaly_score)
    
    def test_task_with_empty_transaction_list(self):
        """Test that the task handles empty transaction list."""
        result = perform_anomaly_detection([], self.contamination)
        
        # Verify the task completed successfully
        self.assertEqual(result['status'], 'Completed')
        self.assertIn('analysis_run_id', result)
        
        # Verify no reports were created
        reports = AnalysisReport.objects.filter(contamination_param=self.contamination)
        self.assertEqual(reports.count(), 0)
    
    def test_task_with_invalid_transaction_ids(self):
        """Test that the task handles invalid transaction IDs gracefully."""
        invalid_ids = [99999, 88888]  # Non-existent IDs
        
        result = perform_anomaly_detection(invalid_ids, self.contamination)
        
        # Verify the task completed successfully
        self.assertEqual(result['status'], 'Completed')
        self.assertIn('analysis_run_id', result)
        
        # Verify no reports were created
        reports = AnalysisReport.objects.filter(contamination_param=self.contamination)
        self.assertEqual(reports.count(), 0)
    
    def test_task_with_fatal_error(self):
        """Test that the task handles fatal errors gracefully."""
        # Mock the Transaction.objects.filter to raise an exception
        with patch.object(Transaction.objects, 'filter', side_effect=Exception("Database error")):
            result = perform_anomaly_detection(self.transaction_ids, self.contamination)
            
            # Verify the task failed gracefully
            self.assertEqual(result['status'], 'Failed')
            self.assertIn('error', result)
            self.assertIn("Database error", result['error'])
    
    def test_analysis_run_id_uniqueness(self):
        """Test that each task execution generates a unique analysis run ID."""
        mock_results = {
            'is_anomaly': False,
            'anomaly_score': 0.5,
            'shap_values_json': '{"values": [], "base_values": 0.5, "feature_names": []}'
        }
        
        with patch.object(anomaly_detection, 'run_complete_analysis', return_value=mock_results):
            # Execute the task twice
            result1 = perform_anomaly_detection(self.transaction_ids, self.contamination)
            result2 = perform_anomaly_detection(self.transaction_ids, self.contamination)
            
            # Verify different run IDs were generated
            self.assertNotEqual(result1['analysis_run_id'], result2['analysis_run_id'])
            
            # Verify reports from different runs have different run IDs
            reports = AnalysisReport.objects.filter(contamination_param=self.contamination)
            run_ids = set(report.analysis_run_id for report in reports)
            self.assertEqual(len(run_ids), 2)
    
    def test_task_with_different_contamination_values(self):
        """Test that the task works with different contamination values."""
        mock_results = {
            'is_anomaly': True,
            'anomaly_score': 0.9,
            'shap_values_json': '{"values": [0.1], "base_values": 0.5, "feature_names": ["feature1"]}'
        }
        
        with patch.object(anomaly_detection, 'run_complete_analysis', return_value=mock_results):
            # Test with different contamination values
            contamination_values = [0.05, 0.1, 0.15, 0.2]
            
            for contamination in contamination_values:
                result = perform_anomaly_detection([self.transaction1.id], contamination)
                self.assertEqual(result['status'], 'Completed')
                
                # Verify report was created with correct contamination value
                report = AnalysisReport.objects.filter(
                    transaction=self.transaction1,
                    contamination_param=contamination
                ).first()
                self.assertIsNotNone(report)
                self.assertEqual(report.contamination_param, contamination)
    
    def test_task_performance_with_large_dataset(self):
        """Test task performance with a larger number of transactions."""
        # Create additional test transactions
        additional_transactions = []
        for i in range(10):
            transaction = Transaction.objects.create(
                transaction_id=f"PERF{i:03d}",
                project_name=f"Performance Test {i}",
                item_name=f"Test Item {i}",
                quantity=i + 1,
                unit_purchase_price=Decimal("50.00"),
                total_purchase_price=Decimal("50.00") * (i + 1),
                supplier=f"Supplier {i}",
                procurement_officer=f"Officer {i}",
                invoice_number=f"INV{i:03d}",
                payment_receipt_number=f"REC{i:03d}",
                transaction_date=timezone.now().date(),
                procurement_method=self.procurement_method
            )
            additional_transactions.append(transaction)
        
        # Add new transaction IDs to the list
        all_transaction_ids = self.transaction_ids + [t.id for t in additional_transactions]
        
        mock_results = {
            'is_anomaly': False,
            'anomaly_score': 0.5,
            'shap_values_json': '{"values": [], "base_values": 0.5, "feature_names": []}'
        }
        
        with patch.object(anomaly_detection, 'run_complete_analysis', return_value=mock_results):
            result = perform_anomaly_detection(all_transaction_ids, self.contamination)
            
            # Verify the task completed successfully
            self.assertEqual(result['status'], 'Completed')
            
            # Verify all reports were created
            reports = AnalysisReport.objects.filter(
                transaction__id__in=all_transaction_ids,
                contamination_param=self.contamination
            )
            self.assertEqual(reports.count(), len(all_transaction_ids)) 