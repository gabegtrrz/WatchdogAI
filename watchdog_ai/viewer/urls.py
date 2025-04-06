from django.urls import path
from .views import UploadView, TransactionView, AnomalyDetectionView, ExportAnomaliesView, ReportsView, ResetTransactionsView

urlpatterns = [
    path('upload/', UploadView.as_view(), name='upload'),
    path('reset-transactions/', ResetTransactionsView.as_view(), name='reset_transactions'),
    path('transactions/', TransactionView.as_view(), name='transactions'),
    path('anomaly-detection/', AnomalyDetectionView.as_view(), name='anomaly_detection'),
    path('export-anomalies/', ExportAnomaliesView.as_view(), name='export_anomalies'),
    path('reports/', ReportsView.as_view(), name='reports'),
]