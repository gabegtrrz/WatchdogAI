
from django.urls import path
from .views import TransactionListView, analysis_configuration_view, run_analysis_view, analysis_results_view

urlpatterns = [
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('analysis/configure/', analysis_configuration_view, name='analysis_configuration'),
    path('analysis/run/', run_analysis_view, name='run_analysis'),
    path('analysis/results/', analysis_results_view, name='analysis_results'),
]