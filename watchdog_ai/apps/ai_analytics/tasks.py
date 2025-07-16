from celery import shared_task
import uuid
import logging
from apps.core.models import Transaction, AnalysisReport
from .services import anomaly_detection

logger = logging.getLogger(__name__)

@shared_task
def perform_anomaly_detection(transaction_ids, contamination):
    """
    Celery task to run the full anomaly detection pipeline asynchronously.
    """
    try:
        logger.info(f"Starting anomaly detection for {len(transaction_ids)} transactions with contamination {contamination}")
        
        analysis_run_id = uuid.uuid4() # Groups this set of analyses
        
        transactions = Transaction.objects.filter(id__in=transaction_ids)
        logger.info(f"Found {transactions.count()} transactions to analyze")
        
        # Note: This is a simplified loop. For high performance, consider
        # batch processing of transactions instead of one-by-one.
        for transaction in transactions:
            logger.info(f"Processing transaction {transaction.id}")
            
            # Check if an identical analysis already exists to avoid re-computation
            existing_report = AnalysisReport.objects.filter(
                transaction=transaction,
                contamination_param=contamination
            ).first()

            if existing_report:
                # We can update the run_id to include it in this new "run"
                existing_report.analysis_run_id = analysis_run_id
                existing_report.save()
                logger.info(f"Updated existing report for transaction {transaction.id}")
                continue

            # If no existing report, run the full pipeline
            try:
                results = anomaly_detection.run_complete_analysis(transaction, contamination)
                logger.info(f"Analysis completed for transaction {transaction.id}: anomaly={results['is_anomaly']}, score={results['anomaly_score']}")
                
                AnalysisReport.objects.create(
                    transaction=transaction,
                    analysis_run_id=analysis_run_id,
                    contamination_param=contamination,
                    is_anomaly=results['is_anomaly'],
                    anomaly_score=results['anomaly_score'],
                    shap_values=results['shap_values_json']
                )
                logger.info(f"Created analysis report for transaction {transaction.id}")
                
            except Exception as e:
                # Log the error and continue with other transactions
                logger.error(f"Error processing transaction {transaction.id}: {e}")
                # Optionally, create a report with an error status
                AnalysisReport.objects.create(
                    transaction=transaction,
                    analysis_run_id=analysis_run_id,
                    contamination_param=contamination,
                    error_message=str(e)
                )
                logger.info(f"Created error report for transaction {transaction.id}")

        logger.info(f"Anomaly detection completed for run {analysis_run_id}")
        return {'status': 'Completed', 'analysis_run_id': str(analysis_run_id)}
        
    except Exception as e:
        logger.error(f"Fatal error in anomaly detection task: {e}")
        return {'status': 'Failed', 'error': str(e)} 