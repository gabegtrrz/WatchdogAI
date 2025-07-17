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

        results = anomaly_detection.run_complete_analysis(transactions, contamination)
        
        
    

        logger.info(f"Anomaly detection completed for run {analysis_run_id}")
        return {'status': 'Completed', 'analysis_run_id': str(analysis_run_id)}
        
    except Exception as e:
        logger.error(f"Fatal error in anomaly detection task: {e}")
        return {'status': 'Failed', 'error': str(e)} 