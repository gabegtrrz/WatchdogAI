from django.urls import path
from .views import TransactionUploadAPIView, transaction_upload_ui, single_transaction_upload

urlpatterns = [
    # URL for the user-facing upload page
    path('upload/', transaction_upload_ui, name='transaction-upload-ui'),

    # URL for the backend API endpoint
    path('api/upload/', TransactionUploadAPIView.as_view(), name='transaction-upload-api'),
    
    # URL for single transaction upload (demo)
    path('single-upload/', single_transaction_upload, name='single-transaction-upload'),
]