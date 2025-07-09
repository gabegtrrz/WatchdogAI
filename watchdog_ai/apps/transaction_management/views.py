from django.shortcuts import render, redirect
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from .serializers import TransactionCSVUploadSerializer
from .services import process_transaction_csv, create_transactions_from_data
from apps.data_augmentation.services import enrich_transaction_list

def transaction_upload_ui(request):
    """
    Renders a UI for procurement officers to upload transaction CSV files.
    Handles POST to process the file by calling the service layer directly.
    """
    if request.method == 'POST':
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
            
            # Enrich the newly created transactions
            enrich_transaction_list(created_transactions)
            messages.info(request, 'Started data enrichment for new transactions.')

        except Exception as e:
            messages.error(request, f'An unexpected error occurred during database creation: {str(e)}')

        return redirect('transaction-upload-ui')

    return render(request, 'transaction_management/upload.html')

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
            enrich_transaction_list(created_transactions)

            return Response(
                {
                    'message': f'Successfully created {len(created_transactions)} transactions. Enrichment started.',
                    'created_count': len(created_transactions)
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            # Catch potential exceptions during database transaction
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )