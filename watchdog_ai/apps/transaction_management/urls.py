from django.urls import path
from django.shortcuts import redirect
from .views import TransactionUploadAPIView, transaction_upload_ui

urlpatterns = [
    # Redirect the root URL to the transaction upload UI page for a better user experience.
    path('', lambda request: redirect('transaction-upload-ui', permanent=False), name='home'),

    # URL for the user-facing upload page
    path('upload/', transaction_upload_ui, name='transaction-upload-ui'),

    # URL for the backend API endpoint
    path('api/transactions/upload/', TransactionUploadAPIView.as_view(), name='transaction-upload-api'),
]