"""
Blockchain Integration Views

Provides API endpoints for the Procurement Officer User Interface to interact
with the blockchain integration module.
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.core.models import Transaction
from .integration import (
    BlockchainIntegrationService,
    integrate_single_transaction,
    integrate_transaction_batch,
    verify_transaction_in_blockchain,
    BlockchainIntegrationError
)

# Setup logging for this module
logger = logging.getLogger(__name__)


def format_api_response(success, data=None, message="", status_code=200):
    """
    Formats a standardized API response for the UI.
    
    Args:
        success (bool): Whether the operation was successful
        data (dict): Response data (optional)
        message (str): Success or error message
        status_code (int): HTTP status code
        
    Returns:
        JsonResponse: Formatted response
    """
    response_data = {
        'success': success,
        'message': message,
        'data': data or {},  # Use empty dict if no data provided
        'timestamp': timezone.now().isoformat()
    }
    return JsonResponse(response_data, status=status_code)


@method_decorator(csrf_exempt, name='dispatch')
class BlockchainIntegrationView(View):
    """
    Main view for blockchain integration operations.
    Handles transaction processing and blockchain integration requests.
    """
    
    def __init__(self):
        super().__init__()
        # Initialize blockchain integration service
        self.integration_service = BlockchainIntegrationService()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def post(self, request):
        """
        Processes transactions for blockchain integration.
        
        Expected JSON payload:
        {
            "transaction_ids": ["tx1", "tx2", ...],
            "operation": "integrate" | "verify"
        }
        """
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            transaction_ids = data.get('transaction_ids', [])
            operation = data.get('operation', 'integrate')  # Default to integrate
            
            # Check if we have transaction IDs to process
            if not transaction_ids:
                return format_api_response(
                    success=False,
                    message="No transaction IDs provided",
                    status_code=400
                )
            
            # Find transactions in database
            transactions = []
            missing_ids = []
            
            for tx_id in transaction_ids:
                try:
                    transaction = Transaction.objects.get(transaction_id=tx_id)
                    transactions.append(transaction)
                except Transaction.DoesNotExist:
                    missing_ids.append(tx_id)  # Track missing transactions
            
            # Return error if any transactions were not found
            if missing_ids:
                return format_api_response(
                    success=False,
                    message=f"Transactions not found: {', '.join(missing_ids)}",
                    status_code=404
                )
            
            # Route to appropriate handler based on operation
            if operation == 'integrate':
                return self._handle_integration(transactions)
            elif operation == 'verify':
                return self._handle_verification(transactions)
            else:
                return format_api_response(
                    success=False,
                    message=f"Unknown operation: {operation}",
                    status_code=400
                )
                
        except json.JSONDecodeError:
            # Handle malformed JSON
            return format_api_response(
                success=False,
                message="Invalid JSON payload",
                status_code=400
            )
        except Exception as e:
            # Handle unexpected errors
            self.logger.error(f"Unexpected error in blockchain integration view: {str(e)}", exc_info=True)
            return format_api_response(
                success=False,
                message=f"Internal server error: {str(e)}",
                status_code=500
            )

    def _handle_integration(self, transactions):
        """
        Handles blockchain integration for a list of transactions.
        
        Args:
            transactions (list): Transactions to integrate
            
        Returns:
            JsonResponse: Integration result
        """
        try:
            # Process transactions through blockchain integration service
            success, result_data = self.integration_service.process_transaction_batch(transactions)
            
            if success:
                # Return success response with result data
                return format_api_response(
                    success=True,
                    data=result_data,
                    message=result_data.get('success_message', 'Transactions successfully integrated into blockchain'),
                    status_code=200
                )
            else:
                # Return error response with error details
                return format_api_response(
                    success=False,
                    data=result_data,
                    message=result_data.get('error_message', 'Blockchain integration failed'),
                    status_code=500
                )
                
        except BlockchainIntegrationError as e:
            # Handle specific blockchain integration errors
            self.logger.error(f"Blockchain integration error: {str(e)}")
            return format_api_response(
                success=False,
                message=f"Blockchain integration failed: {str(e)}",
                status_code=500
            )
        except Exception as e:
            # Handle unexpected integration errors
            self.logger.error(f"Unexpected error during integration: {str(e)}", exc_info=True)
            return format_api_response(
                success=False,
                message=f"Unexpected error: {str(e)}",
                status_code=500
            )

    def _handle_verification(self, transactions):
        """
        Handles blockchain verification for a list of transactions.
        
        Args:
            transactions (list): Transactions to verify
            
        Returns:
            JsonResponse: Verification result
        """
        try:
            verification_results = []
            all_verified = True
            
            # Verify each transaction individually
            for transaction in transactions:
                result = verify_transaction_in_blockchain(transaction)
                verification_results.append(result)
                
                # Track if any verification failed
                if not result.get('verified', False):
                    all_verified = False
            
            # Count successful verifications for summary message
            verified_count = len([r for r in verification_results if r.get('verified')])
            
            return format_api_response(
                success=all_verified,
                data={
                    'verification_results': verification_results,
                    'total_transactions': len(transactions),
                    'all_verified': all_verified
                },
                message=f"Verification complete: {verified_count} of {len(transactions)} transactions verified",
                status_code=200
            )
            
        except Exception as e:
            # Handle verification errors
            self.logger.error(f"Unexpected error during verification: {str(e)}", exc_info=True)
            return format_api_response(
                success=False,
                message=f"Verification error: {str(e)}",
                status_code=500
            )


@csrf_exempt
@require_http_methods(["POST"])
def integrate_single_transaction_view(request, transaction_id):
    """
    Integrates a single transaction into the blockchain.
    
    URL: /blockchain/integrate/<transaction_id>/
    """
    try:
        # Find the transaction or return 404
        transaction = get_object_or_404(Transaction, transaction_id=transaction_id)
        
        # Process the single transaction
        success, result_data = integrate_single_transaction(transaction)
        
        if success:
            # Return success response
            return format_api_response(
                success=True,
                data=result_data,
                message=f"Transaction {transaction_id} successfully integrated into blockchain"
            )
        else:
            # Return error response
            return format_api_response(
                success=False,
                data=result_data,
                message=f"Failed to integrate transaction {transaction_id} into blockchain",
                status_code=500
            )
            
    except Exception as e:
        # Log and return error
        logger.error(f"Error integrating transaction {transaction_id}: {str(e)}", exc_info=True)
        return format_api_response(
            success=False,
            message=f"Error integrating transaction: {str(e)}",
            status_code=500
        )


@csrf_exempt
@require_http_methods(["GET"])
def verify_transaction_view(request, transaction_id):
    """
    Verifies a transaction's existence and integrity in the blockchain.
    
    URL: /blockchain/verify/<transaction_id>/
    """
    try:
        # Find the transaction or return 404
        transaction = get_object_or_404(Transaction, transaction_id=transaction_id)
        
        # Verify the transaction
        verification_result = verify_transaction_in_blockchain(transaction)
        
        return format_api_response(
            success=verification_result.get('verified', False),
            data=verification_result,
            message=f"Transaction {transaction_id} verification complete"
        )
        
    except Exception as e:
        # Log and return error
        logger.error(f"Error verifying transaction {transaction_id}: {str(e)}", exc_info=True)
        return format_api_response(
            success=False,
            message=f"Error verifying transaction: {str(e)}",
            status_code=500
        )


@csrf_exempt
@require_http_methods(["GET"])
def blockchain_status_view(request):
    """
    Returns the current status of the blockchain.
    
    URL: /blockchain/status/
    """
    try:
        # Create integration service to get blockchain state
        integration_service = BlockchainIntegrationService()
        blockchain_state = integration_service._get_blockchain_state_summary()
        
        # Perform integrity check
        integrity_status = integration_service.initiate_integrity_check()
        
        # Combine state and integrity info
        status_data = {
            **blockchain_state,  # Spread blockchain state info
            'integrity_verified': integrity_status,
            'status': 'healthy' if integrity_status else 'integrity_issues'
        }
        
        return format_api_response(
            success=True,
            data=status_data,
            message="Blockchain status retrieved successfully"
        )
        
    except Exception as e:
        # Log and return error
        logger.error(f"Error retrieving blockchain status: {str(e)}", exc_info=True)
        return format_api_response(
            success=False,
            message=f"Error retrieving blockchain status: {str(e)}",
            status_code=500
        )


@csrf_exempt  
@require_http_methods(["POST"])
def batch_process_pending_transactions_view(request):
    """
    Processes all pending transactions (not yet added to blockchain) in batch.
    
    URL: /blockchain/process-pending/
    """
    try:
        # Find all transactions not yet linked to a block
        pending_transactions = Transaction.objects.filter(block__isnull=True)
        
        # Check if there are any pending transactions
        if not pending_transactions.exists():
            return format_api_response(
                success=True,
                data={'processed_count': 0},
                message="No pending transactions to process"
            )
        
        # Convert queryset to list for processing
        transactions_list = list(pending_transactions)
        
        # Process all pending transactions through blockchain integration
        success, result_data = integrate_transaction_batch(transactions_list)
        
        if success:
            # Return success response
            return format_api_response(
                success=True,
                data=result_data,
                message=f"Successfully processed {len(transactions_list)} pending transactions"
            )
        else:
            # Return error response
            return format_api_response(
                success=False,
                data=result_data,
                message=f"Failed to process {len(transactions_list)} pending transactions",
                status_code=500
            )
            
    except Exception as e:
        # Log and return error
        logger.error(f"Error processing pending transactions: {str(e)}", exc_info=True)
        return format_api_response(
            success=False,
            message=f"Error processing pending transactions: {str(e)}",
            status_code=500
        )