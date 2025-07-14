from django.urls import path
from .views import TransactionUploadAPIView, transaction_upload_ui

urlpatterns = [
    # URL for the user-facing upload page
    path('upload/', transaction_upload_ui, name='transaction-upload-ui'),

    # URL for the backend API endpoint
    path('api/upload/', TransactionUploadAPIView.as_view(), name='transaction-upload-api'),
]