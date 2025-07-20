from celery import shared_task
import uuid
import logging
from apps.core.models import Transaction, AnalysisReport
from .services import anomaly_detection

logger = logging.getLogger(__name__)

@shared_task
def perform_anomaly_detection(transaction_ids, contamination):
    """
    Celery task to run the full anomaly detection pipeline.
    """
    try:
        logger.info(f"Starting anomaly detection for {len(transaction_ids)} transactions with contamination {contamination}")
        
        analysis_run_id = uuid.uuid4() # Groups this set of analyses
        
        transactions_qs = Transaction.objects.filter(id__in=transaction_ids)
        logger.info(f"Found {transactions_qs.count()} transactions to analyze")

        results = anomaly_detection.run_complete_analysis(
            transactions_qs=transactions_qs,
            contamination=contamination, 
            analysis_run_id=analysis_run_id
        )
        # Results template:
        # {
        #     'status': 'success',
        #     'analysis_run_id': str(analysis_run_id),
        #     'transactions_analyzed': len(transactions_list),
        #     'anomalies_found': int(np.sum(anomaly_labels))
        # }


        logger.info(f"Anomaly detection completed for run {analysis_run_id}")
        
        # Return success response with analysis_run_id for redirection
        return {
            'status': 'Completed',
            'analysis_run_id': str(analysis_run_id),
            'transactions_analyzed': results.get('transactions_analyzed', 0),
            'anomalies_found': results.get('anomalies_found', 0)
        }
        
    except Exception as e:
        logger.error(f"Fatal error in anomaly detection task: {e}")
        return {'status': 'Failed', 'error': str(e)} 