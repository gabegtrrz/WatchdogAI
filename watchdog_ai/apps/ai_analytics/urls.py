
from django.urls import path
from . import views

urlpatterns = [
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('analysis/select-transactions/', views.select_transactions, name='select_transactions'),
    path('analysis/configure/', views.analysis_configuration, name='analysis_configuration'),
    path('analysis/run/', views.run_analysis, name='run_analysis'),
    path('analysis/task-status/<str:task_id>/', views.get_task_status, name='get_task_status'),
    path('analysis/results/<uuid:analysis_run_id>/', views.analysis_results, name='analysis_results'),
    path('analysis/report/<int:report_id>/', views.analysis_report_detail, name='analysis_report_detail'),
]