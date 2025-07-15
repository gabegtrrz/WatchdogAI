from celery import shared_task
import uuid
from watchdog_ai.core.models import Transaction, AnalysisReport
from .services import anomaly_detection

@shared_task
def perform_anomaly_detection(transaction_ids, contamination):
    """
    Celery task to run the full anomaly detection pipeline asynchronously.
    """
    analysis_run_id = uuid.uuid4() # Groups this set of analyses
    
    transactions = Transaction.objects.filter(id__in=transaction_ids)
    
    # Note: This is a simplified loop. For high performance, consider
    # batch processing of transactions instead of one-by-one.
    for transaction in transactions:
        # Check if an identical analysis already exists to avoid re-computation
        existing_report = AnalysisReport.objects.filter(
            transaction=transaction,
            contamination_param=contamination
        ).first()

        if existing_report:
            # We can update the run_id to include it in this new "run"
            existing_report.analysis_run_id = analysis_run_id
            existing_report.save()
            continue

        # If no existing report, run the full pipeline
        try:
            results = anomaly_detection.run_complete_analysis(transaction, contamination)
            
            AnalysisReport.objects.create(
                transaction=transaction,
                analysis_run_id=analysis_run_id,
                contamination_param=contamination,
                is_anomaly=results['is_anomaly'],
                anomaly_score=results['anomaly_score'],
                shap_values=results['shap_values_json']
            )
        except Exception as e:
            # Log the error and continue with other transactions
            print(f"Error processing transaction {transaction.id}: {e}")
            # Optionally, create a report with an error status
            AnalysisReport.objects.create(
                transaction=transaction,
                analysis_run_id=analysis_run_id,
                contamination_param=contamination,
                error_message=str(e)
            )

    return {'status': 'Completed', 'analysis_run_id': str(analysis_run_id)} 