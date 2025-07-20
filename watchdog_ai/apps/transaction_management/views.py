from django.shortcuts import render, redirect
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from decimal import Decimal
from datetime import datetime
from django.db import transaction

from .serializers import TransactionCSVUploadSerializer
from .forms import SingleTransactionUploadForm
from .services import process_transaction_csv, create_transactions_from_data
from apps.data_augmentation.services import enrich_transaction_list
from apps.blockchain.integration import integrate_transaction_batch, retry_failed_blockchain_integrations, get_blockchain_status_summary
from apps.blockchain.integrity_service import integrity_service
from apps.core.models import Transaction, ProcurementMethod

def transaction_upload_ui(request):
    """
    Renders a UI for procurement officers to upload transaction CSV files.
    Handles POST to process the file by calling the service layer directly.
    """
    if request.method == 'POST':
        # Handle retry action
        if 'retry_blockchain' in request.POST:
            return handle_blockchain_retry(request)
        
        uploaded_file = request.FILES.get('csv_file')
        # Check if the 'dry_run' checkbox was selected in the form
        is_dry_run = request.POST.get('dry_run') == 'true'

        if not uploaded_file:
            messages.error(request, 'No file selected.')
            return redirect('transaction-upload-ui')

        if not uploaded_file.name.endswith('.csv'):
            messages.error(request, 'The uploaded file must be a CSV.')
            return redirect('transaction-upload-ui')

        # Delegate to the service layer for processing and validation
        valid_data, errors = process_transaction_csv(uploaded_file)

        if errors:
            messages.error(request, 'Upload failed. Please fix the following issues:')
            
            # Build and add each specific error message.
            for error_detail in errors:
                if 'row' in error_detail:
                    row_errors = [f"'{e['field']}': {e['error']}" for e in error_detail.get('errors', [])]
                    error_message = f"Row {error_detail['row']}: {', '.join(row_errors)}"
                    messages.error(request, error_message)
                else:
                    messages.error(request, error_detail.get('message', 'An unknown file error occurred.'))
            
            return redirect('transaction-upload-ui')

        if not valid_data:
            messages.warning(request, 'The CSV file is empty or contains no valid data rows.')
            return redirect('transaction-upload-ui')

        # If it's a dry run, report success and stop before saving to the database.
        if is_dry_run:
            messages.success(request, f"Test successful! The file is valid and contains {len(valid_data)} data rows. No data was saved.")
            return redirect('transaction-upload-ui')

        # If not a dry run, proceed to save the data.
        try:
            created_transactions = create_transactions_from_data(valid_data)
            messages.success(request, f'Successfully created {len(created_transactions)} transactions.')
            '''
            # Enrich the newly created transactions
            enrichment_stats = enrich_transaction_list(created_transactions)
            
            updated_count = enrichment_stats.get('updated', 0)
            skipped_count = enrichment_stats.get('skipped', 0)

            messages.info(
                request, 
                f"Data enrichment complete: {updated_count} transactions updated, {skipped_count} skipped."
            )
'''
            messages.info(
                request,
                f'Appending to Blockchain...'
            )

            ### Integrate to Blockchain with Integrity Checks
            blockchain_success, blockchain_result = integrate_transaction_batch(created_transactions)
            
            # Check integrity results
            integrity_checks = blockchain_result.get('integrity_checks', {})
            
            if blockchain_success:
                messages.success(request, f"Successfully integrated {blockchain_result['integrated_count']} transactions into blockchain.")
                if blockchain_result.get('block_info'):
                    block_info = blockchain_result['block_info']
                    messages.info(request, f"Block {block_info['index']} created with hash {block_info['hash'][:16]}...")
                
                # Report integrity check results
                if integrity_checks.get('before', {}).get('alert_sent'):
                    messages.warning(request, "⚠️ Blockchain integrity alert sent before integration.")
                if integrity_checks.get('after', {}).get('alert_sent'):
                    messages.warning(request, "⚠️ Blockchain integrity alert sent after integration.")
                    
            else:
                error_message = blockchain_result.get('error_message', 'Failed to append transactions to blockchain.')
                messages.error(request, error_message)
                
                # Check if failure was due to integrity issues
                if integrity_checks.get('before', {}).get('alert_sent'):
                    messages.error(request, "❌ Integration blocked due to blockchain integrity issues.")
                else:
                    messages.warning(request, "You can retry blockchain integration using the button below.")

        except Exception as e:
            messages.error(request, f'An unexpected error occurred during database creation: {str(e)}')

        return redirect('transaction-upload-ui')

    # Get blockchain status for display
    blockchain_status = get_blockchain_status_summary()
    
    return render(request, 'transaction_management/upload.html', {
        'blockchain_status': blockchain_status
    })


def handle_blockchain_retry(request):
    """
    Handles retry of failed blockchain integrations.
    """
    try:
        retry_result = retry_failed_blockchain_integrations()
        
        if retry_result['success']:
            if retry_result['retried_count'] > 0:
                messages.success(request, f"Retry completed: {retry_result['integrated_count']} transactions integrated, {retry_result['failed_count']} still failed.")
            else:
                messages.info(request, "No failed transactions to retry.")
        else:
            error_msg = retry_result.get('error_message', 'Retry failed')
            messages.error(request, f"Retry failed: {error_msg}")
            
    except Exception as e:
        messages.error(request, f"Error during retry: {str(e)}")
    
    return redirect('transaction-upload-ui')


class TransactionUploadAPIView(APIView):
    """
    API endpoint for uploading a CSV file to create multiple transactions.
    
    Accepts a POST request with 'multipart/form-data' containing a 'csv_file'.
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        """
        Handles the POST request with an uploaded CSV file.
        
        The process is as follows:
        1. Validates the file upload using is_valid(raise_exception=True).
        2. Calls the `process_transaction_csv` service to parse and validate CSV content.
        3. If validation errors are found, returns a 400 response with detailed errors.
        4. If the data is valid, calls `create_transactions_from_data` to create transactions.
        5. Returns a 201 response with the count of created transactions.
        """
        serializer = TransactionCSVUploadSerializer(data=request.data)
        
        # Use raise_exception=True to automatically handle validation errors.
        # DRF will return a 400 Bad Request response if the data is invalid.
        serializer.is_valid(raise_exception=True)

        csv_file = serializer.validated_data.get('csv_file')# type: ignore
        
        # Call the service layer to process the CSV
        valid_data, errors = process_transaction_csv(csv_file)

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        if not valid_data:
            return Response(
                {'message': 'The CSV file is empty or contains no valid data rows.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Call the service layer to create the transactions
            created_transactions = create_transactions_from_data(valid_data)
            
            # Enrich the newly created transactions
            enrichment_stats = enrich_transaction_list(created_transactions)

            # Integrate to Blockchain
            blockchain_success, blockchain_result = integrate_transaction_batch(created_transactions)
            
            response_data = {
                'message': f'Successfully created {len(created_transactions)} transactions.',
                'created_count': len(created_transactions),
                'enrichment_stats': enrichment_stats,
                'blockchain_integration': {
                    'success': blockchain_success,
                    'message': blockchain_result.get('success_message' if blockchain_success else 'error_message', 
                                                   'Blockchain integration completed' if blockchain_success else 'Blockchain integration failed'),
                    'details': blockchain_result
                }
            }

            return Response(
                response_data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            # Catch potential exceptions during database transaction
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def single_transaction_upload(request):
    """
    Handles single transaction upload form for demo purposes using Django forms.
    Creates a single transaction from form data and integrates it with blockchain.
    """
    if request.method == 'POST':
        form = SingleTransactionUploadForm(request.POST)
        if form.is_valid():
            try:
                # Save the transaction
                new_transaction = form.save()
                
                # Calculate total purchase price
                new_transaction.total_purchase_price = new_transaction.calculated_total_purchase_price
                new_transaction.save()
                
                # Integrate with blockchain
                blockchain_success, blockchain_result = integrate_transaction_batch([new_transaction])
                
                if blockchain_success:
                    messages.success(request, f'Transaction created successfully and integrated with blockchain!')
                    if blockchain_result.get('block_info'):
                        block_info = blockchain_result['block_info']
                        messages.info(request, f"Block {block_info['index']} created with hash {block_info['hash'][:16]}...")
                else:
                    messages.warning(request, f'Transaction created but blockchain integration failed. You can retry later.')
                
                messages.success(request, f'Transaction ID: {new_transaction.transaction_id}')
                
            except Exception as e:
                messages.error(request, f'An error occurred while creating the transaction: {str(e)}')
        else:
            # Form has errors, they will be displayed in the template
            pass
    else:
        form = SingleTransactionUploadForm()
    
    return render(request, 'transaction_management/single_upload.html', {'form': form})