import pandas as pd
from io import StringIO
from typing import List, Dict, Tuple
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from apps.core.models import ProcurementMethod, Transaction

# Define the columns the CSV must have for validation.
REQUIRED_COLUMNS = [
    'item_name',
    'quantity',
    'unit_purchase_price',
    'transaction_date',
    'procurement_method_name',
    'supplier',
    'invoice_number',
    'payment_receipt_number'
]

def process_transaction_csv(file_stream) -> Tuple[List[Dict], List[Dict]]:
    """
    Parses and validates a transaction CSV file against business rules.

    This function reads a file, checks for required columns, and validates
    each row for data integrity and existence of related objects (Item,

    ProcurementMethod). It's optimized to perform minimal database queries.

    Args:
        file_stream: The uploaded file object from a Django request.

    Returns:
        A tuple containing two lists:
        1. A list of validated and cleaned data dictionaries ready for creation. 
        2. A list of structured error dictionaries if validation fails.
    """
    try:
        csv_content = file_stream.read().decode('utf-8') # into UTF-8 string

        # Use StringIO to treat the decoded CSV string as an in-memory file.
        # This is efficient as it avoids writing to disk.
        df = pd.read_csv(StringIO(csv_content))

        # --- Column Validation ---
        present_columns = set(df.columns)
        required_columns = set(REQUIRED_COLUMNS)
        
        # Add debugging information
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Present columns: {sorted(list(present_columns))}")
        logger.debug(f"Required columns: {sorted(list(required_columns))}")
        logger.debug(f"Missing columns: {sorted(list(required_columns - present_columns))}")
        
        if not required_columns.issubset(present_columns):
            missing_cols = sorted(list(required_columns - present_columns)) # sorting guarantees that for the same set of missing columns, the error message will always be identical
            parsing_error = [{'type': 'File Parsing Error', 'message': f'Missing required columns: {", ".join(missing_cols)}'}]
            return [], parsing_error

    # --- Catch more specific exceptions for better error diagnostics ---
    except UnicodeDecodeError:
        parsing_error = [{'type': 'File Parsing Error', 'message': 'File is not UTF-8 encoded. Please save the file as UTF-8 and try again.'}]
        return [], parsing_error
    except pd.errors.ParserError as e:
        parsing_error = [{'type': 'File Parsing Error', 'message': f'Could not parse the CSV file. Please check the file format. Error: {str(e)}'}]
        return [], parsing_error
    except Exception as e:
        parsing_error = [{'type': 'File Parsing Error', 'message': f'An unexpected error occurred while reading the file. Error: {str(e)}'}]
        return [], parsing_error

    valid_data_list = []
    validation_errors = []

    # Pre-fetch all valid procurement methods into efficient lookups.
    procurement_methods_map = {method.name.upper(): method for method in ProcurementMethod.objects.all()}

    # The procurement_methods_map dictionary would look something like this  in memory:
        # {
        #     'DIRECT PURCHASE': <ProcurementMethod object (pk=1)>,
        #     'TENDER': <ProcurementMethod object (pk=2)>,
        #     'EMERGENCY': <ProcurementMethod object (pk=3)>
        # }


    for i, row in enumerate(df.to_dict(orient='records')): #alternate method for large files (unlikely) is itterrows() which gives overhead for processing each row at a time. to_dict() is faster but loads all data into memory.
        row_num = i + 2  # For user-friendly error reporting
        
        # Log the raw row from the CSV reader
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Row {row_num} (raw): {row}")

        errors_in_row = []
        cleaned_row_data = {}

        # --- Validate 'item_name' ---
        raw_item_name = row.get('item_name')

        # 1. Check for invalid, missing (NaN, None) or blank (empty string, whitespace) values.

        if isinstance(raw_item_name, (pd.Series, pd.DataFrame)):
            errors_in_row.append({'field': 'item_name', 'error': 'Invalid item_name value.'})
        elif pd.isna(raw_item_name) or str(raw_item_name).strip() == '':
            errors_in_row.append({'field': 'item_name', 'error': 'Item name is required and cannot be blank.'})
        else:
            cleaned_row_data['item_name'] = str(raw_item_name).strip().upper()

        # --- Validate 'procurement_method_name' ---
        raw_procurement_method_name = row.get('procurement_method_name')

        if pd.isna(raw_procurement_method_name) or str(raw_procurement_method_name).strip() == '':
            errors_in_row.append({'field': 'procurement_method_name', 'error': 'Procurement method is required and cannot be blank.'})
        else:
            # Standardize for case-insensitive lookup
            procurement_method_name = str(raw_procurement_method_name).strip().upper()
            procurement_method_obj = procurement_methods_map.get(procurement_method_name)

            if not procurement_method_obj:
                errors_in_row.append({
                    'field': 'procurement_method_name',
                    'error': f'Procurement method "{row.get("procurement_method_name")}" is not a valid method.'
                })
            else:
                # Assign the actual ProcurementMethod object for the ForeignKey relationship
                cleaned_row_data['procurement_method'] = procurement_method_obj

        # --- Validate 'quantity' (Type and Business Rule) ---
        raw_quantity = row.get('quantity')
        if pd.isna(raw_quantity):
            errors_in_row.append({'field': 'quantity', 'error': 'Quantity is required.'})
        else:
            try:
                quantity = int(raw_quantity)
                if quantity <= 0:
                    errors_in_row.append({'field': 'quantity', 'error': 'Quantity must be a positive integer.'})
                cleaned_row_data['quantity'] = quantity
            except (ValueError, TypeError):
                errors_in_row.append({'field': 'quantity', 'error': 'Quantity must be a valid whole number.'})

        # --- Validate 'unit_purchase_price' (Type and Business Rule) ---
        raw_price = row.get('unit_purchase_price')
        if pd.isna(raw_price):
            errors_in_row.append({'field': 'unit_purchase_price', 'error': 'Unit purchase price is required.'})
        else:
            try:
                price = Decimal(str(raw_price).strip())
                if price <= 0:
                    errors_in_row.append({'field': 'unit_purchase_price', 'error': 'Unit purchase price must be a positive number.'})
                else:
                    # Round to 2 decimal places to match model constraint
                    price = price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    cleaned_row_data['unit_purchase_price'] = price
            except InvalidOperation:
                errors_in_row.append({'field': 'unit_purchase_price', 'error': 'Unit purchase price must be a valid number.'})

        # --- Validate 'transaction_date' (Format) ---
        raw_date = row.get('transaction_date')
        if pd.isna(raw_date):
            errors_in_row.append({'field': 'transaction_date', 'error': 'Transaction date is required.'})
        else:
            try:
                cleaned_row_data['transaction_date'] = pd.to_datetime(raw_date).date()
            except (ValueError, TypeError):
                errors_in_row.append({'field': 'transaction_date', 'error': 'Transaction date must be in a recognizable format (e.g., YYYY-MM-DD).'})

        # --- Validate 'supplier' (is present) ---
        raw_supplier = row.get('supplier')
        if pd.isna(raw_supplier) or str(raw_supplier).strip() == '':
            errors_in_row.append({'field': 'supplier', 'error': 'Supplier is required and cannot be blank.'})
        else:
            cleaned_row_data['supplier'] = str(raw_supplier).strip()

        # --- Validate 'invoice_number' (is present) ---
        raw_invoice_number = row.get('invoice_number')
        if pd.isna(raw_invoice_number) or str(raw_invoice_number).strip() == '':
            errors_in_row.append({'field': 'invoice_number', 'error': 'Invoice number is required and cannot be blank.'})
        else:
            cleaned_row_data['invoice_number'] = str(raw_invoice_number).strip()

        # --- Validate 'payment_receipt_number' (is present) ---
        raw_payment_receipt_number = row.get('payment_receipt_number')
        if pd.isna(raw_payment_receipt_number) or str(raw_payment_receipt_number).strip() == '':
            errors_in_row.append({'field': 'payment_receipt_number', 'error': 'Payment receipt number is required and cannot be blank.'})
        else:
            cleaned_row_data['payment_receipt_number'] = str(raw_payment_receipt_number).strip()

        # --- Validate additional required fields ---
        
        # --- Validate 'transaction_id' (optional, auto-generated if not provided) ---
        raw_transaction_id = row.get('transaction_id')
        if not pd.isna(raw_transaction_id) and str(raw_transaction_id).strip() != '':
            cleaned_row_data['transaction_id'] = str(raw_transaction_id).strip()

        # --- Validate 'project_name' (required) ---
        raw_project_name = row.get('project_name')
        if pd.isna(raw_project_name) or str(raw_project_name).strip() == '':
            errors_in_row.append({'field': 'project_name', 'error': 'Project name is required and cannot be blank.'})
        else:
            cleaned_row_data['project_name'] = str(raw_project_name).strip()

        # --- Validate 'end_user_unit' (required) ---
        raw_end_user_unit = row.get('end_user_unit')
        if pd.isna(raw_end_user_unit) or str(raw_end_user_unit).strip() == '':
            errors_in_row.append({'field': 'end_user_unit', 'error': 'End user unit is required and cannot be blank.'})
        else:
            cleaned_row_data['end_user_unit'] = str(raw_end_user_unit).strip()

        # --- Validate 'project_description' (required) ---
        raw_project_description = row.get('project_description')
        if pd.isna(raw_project_description) or str(raw_project_description).strip() == '':
            errors_in_row.append({'field': 'project_description', 'error': 'Project description is required and cannot be blank.'})
        else:
            cleaned_row_data['project_description'] = str(raw_project_description).strip()

        # --- Validate 'approved_budget' (required, must be positive) ---
        raw_approved_budget = row.get('approved_budget')
        if pd.isna(raw_approved_budget) or str(raw_approved_budget).strip() == '':
            errors_in_row.append({'field': 'approved_budget', 'error': 'Approved budget is required and cannot be blank.'})
        else:
            try:
                approved_budget = Decimal(str(raw_approved_budget))
                if approved_budget <= 0:
                    errors_in_row.append({'field': 'approved_budget', 'error': 'Approved budget must be a positive number.'})
                else:
                    # Round to 2 decimal places to match model constraint
                    approved_budget = approved_budget.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    cleaned_row_data['approved_budget'] = approved_budget
            except InvalidOperation:
                errors_in_row.append({'field': 'approved_budget', 'error': 'Approved budget must be a valid number.'})

        # --- Calculate 'total_purchase_price' from quantity and unit_purchase_price ---
        if 'quantity' in cleaned_row_data and 'unit_purchase_price' in cleaned_row_data:
            try:
                total_purchase_price = cleaned_row_data['quantity'] * cleaned_row_data['unit_purchase_price']
                # Round to 2 decimal places to match model constraint
                total_purchase_price = total_purchase_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                cleaned_row_data['total_purchase_price'] = total_purchase_price
            except (TypeError, ValueError) as e:
                errors_in_row.append({'field': 'total_purchase_price', 'error': f'Could not calculate total purchase price: {str(e)}'})

        # --- Validate 'procurement_officer' (required) ---
        raw_procurement_officer = row.get('procurement_officer')
        if pd.isna(raw_procurement_officer) or str(raw_procurement_officer).strip() == '':
            errors_in_row.append({'field': 'procurement_officer', 'error': 'Procurement officer is required and cannot be blank.'})
        else:
            cleaned_row_data['procurement_officer'] = str(raw_procurement_officer).strip()

        # --- Validate required date fields ---
        
        # --- Validate 'invitation_to_bid_posting_date' (required) ---
        raw_invitation_date = row.get('invitation_to_bid_posting_date')
        if pd.isna(raw_invitation_date) or str(raw_invitation_date).strip() == '':
            errors_in_row.append({'field': 'invitation_to_bid_posting_date', 'error': 'Invitation to bid posting date is required and cannot be blank.'})
        else:
            try:
                cleaned_row_data['invitation_to_bid_posting_date'] = pd.to_datetime(raw_invitation_date).date()
            except (ValueError, TypeError):
                errors_in_row.append({'field': 'invitation_to_bid_posting_date', 'error': 'Invitation to bid posting date must be in a recognizable format (e.g., YYYY-MM-DD).'})

        # --- Validate 'bid_submission_deadline' (required) ---
        raw_bid_deadline = row.get('bid_submission_deadline')
        if pd.isna(raw_bid_deadline) or str(raw_bid_deadline).strip() == '':
            errors_in_row.append({'field': 'bid_submission_deadline', 'error': 'Bid submission deadline is required and cannot be blank.'})
        else:
            try:
                cleaned_row_data['bid_submission_deadline'] = pd.to_datetime(raw_bid_deadline).date()
            except (ValueError, TypeError):
                errors_in_row.append({'field': 'bid_submission_deadline', 'error': 'Bid submission deadline must be in a recognizable format (e.g., YYYY-MM-DD).'})

        # --- Validate 'bid_opening_date' (required) ---
        raw_bid_opening = row.get('bid_opening_date')
        if pd.isna(raw_bid_opening) or str(raw_bid_opening).strip() == '':
            errors_in_row.append({'field': 'bid_opening_date', 'error': 'Bid opening date is required and cannot be blank.'})
        else:
            try:
                cleaned_row_data['bid_opening_date'] = pd.to_datetime(raw_bid_opening).date()
            except (ValueError, TypeError):
                errors_in_row.append({'field': 'bid_opening_date', 'error': 'Bid opening date must be in a recognizable format (e.g., YYYY-MM-DD).'})

        # --- Validate 'notice_of_award_date' (required) ---
        raw_award_date = row.get('notice_of_award_date')
        if pd.isna(raw_award_date) or str(raw_award_date).strip() == '':
            errors_in_row.append({'field': 'notice_of_award_date', 'error': 'Notice of award date is required and cannot be blank.'})
        else:
            try:
                cleaned_row_data['notice_of_award_date'] = pd.to_datetime(raw_award_date).date()
            except (ValueError, TypeError):
                errors_in_row.append({'field': 'notice_of_award_date', 'error': 'Notice of award date must be in a recognizable format (e.g., YYYY-MM-DD).'})

        # --- Validate 'contract_signing_date' (required) ---
        raw_contract_date = row.get('contract_signing_date')
        if pd.isna(raw_contract_date) or str(raw_contract_date).strip() == '':
            errors_in_row.append({'field': 'contract_signing_date', 'error': 'Contract signing date is required and cannot be blank.'})
        else:
            try:
                cleaned_row_data['contract_signing_date'] = pd.to_datetime(raw_contract_date).date()
            except (ValueError, TypeError):
                errors_in_row.append({'field': 'contract_signing_date', 'error': 'Contract signing date must be in a recognizable format (e.g., YYYY-MM-DD).'})

        # --- Validate 'is_anomaly' (optional) ---
        if row.get('is_anomaly') is not None:
            cleaned_row_data['is_anomaly'] = row.get('is_anomaly')

        if errors_in_row:
            validation_errors.append({'row': row_num, 'errors': errors_in_row})
        else:
            # If the row is valid, add the cleaned and validated data to list for database creation
            valid_data_list.append(cleaned_row_data)

    return valid_data_list, validation_errors


@transaction.atomic
def create_transactions_from_data(valid_data: List[Dict]) -> List[Transaction]:
    """
    Creates Transaction objects in the database from validated data.

    This operation is wrapped in a database transaction. If any transaction
    fails to save, all previous saves from the same batch are rolled back.

    Create objects one-by-one instead of using `bulk_create` to ensure
    that the model's `.save()` and `.clean()` methods are triggered,
    critical for generating `transaction_id` and running final validations.

    Args:
        valid_data: A list of validated transaction data dictionaries from
                    the `process_transaction_csv` function.

    Returns:
        A list of the transaction records successfully created.
    """
    created_transactions = []
    for data in valid_data:
        # Using .create() ensures the model's .save() method is called.
        new_transaction = Transaction.objects.create(**data)
        created_transactions.append(new_transaction)

    return created_transactions