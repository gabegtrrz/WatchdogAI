"""
URL Configuration for Blockchain Integration Module

Defines the API endpoints for blockchain integration operations
that can be used by the Procurement Officer User Interface.
"""

from django.urls import path
from . import views

# App namespace for blockchain operations
app_name = 'blockchain'

urlpatterns = [
    # Main blockchain integration endpoint
    # POST with JSON payload containing transaction_ids and operation type
    path('integrate/', views.BlockchainIntegrationView.as_view(), name='integrate'),
    
    # Single transaction integration
    # POST to integrate a specific transaction by ID
    path('integrate/<str:transaction_id>/', views.integrate_single_transaction_view, name='integrate_single'),
    
    # Transaction verification
    # GET to verify a specific transaction by ID
    path('verify/<str:transaction_id>/', views.verify_transaction_view, name='verify_transaction'),
    
    # Blockchain status and health check
    # GET to retrieve current blockchain status and integrity
    path('status/', views.blockchain_status_view, name='status'),
    
    # Batch process all pending transactions
    # POST to process all transactions not yet in blockchain
    path('process-pending/', views.batch_process_pending_transactions_view, name='process_pending'),
]

"""
Example Usage:

1. Integrate multiple transactions:
   POST /blockchain/integrate/
   Body: {"transaction_ids": ["tx1", "tx2"], "operation": "integrate"}

2. Integrate single transaction:
   POST /blockchain/integrate/tx123/

3. Verify transaction:
   GET /blockchain/verify/tx123/

4. Check blockchain status:
   GET /blockchain/status/

5. Process all pending transactions:
   POST /blockchain/process-pending/
"""