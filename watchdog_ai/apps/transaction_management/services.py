import pandas as pd
from io import StringIO
from typing import List, Dict, Tuple
from decimal import Decimal, InvalidOperation

from django.db import transaction
from apps.core.models import Item, ProcurementMethod, Transaction

# Define the columns the CSV must have for validation.
REQUIRED_COLUMNS = [
    'item_name',  # Changed from item_id
    'quantity',
    'unit_purchase_price',
    'transaction_date',
    'procurement_method_name',
    'supplier'
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
    # valid_item_names = set(name.upper() for name in Item.objects.values_list('name', flat=True))
    procurement_methods_map = {method.name.upper(): method for method in ProcurementMethod.objects.all()}

    # The procurement_methods_map dictionary would look something like this  in memory:
        # {
        #     'DIRECT PURCHASE': <ProcurementMethod object (pk=1)>,
        #     'TENDER': <ProcurementMethod object (pk=2)>,
        #     'EMERGENCY': <ProcurementMethod object (pk=3)>
        # }


    for i, (index, row) in enumerate(df.iterrows()):
        row_num = i + 2  # For user-friendly error reporting
        errors_in_row = []
        cleaned_row_data = {}

        # --- Validate 'item_name' ---
        raw_item_name = row.get('item_name')

        # 1. Check for missing (NaN, None) or blank (empty string, whitespace) values first.
        if pd.isna(raw_item_name) or str(raw_item_name).strip() == '':
            errors_in_row.append({'field': 'item_name', 'error': 'Item name is required and cannot be blank.'})

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
                price = Decimal(str(raw_price))
                if price <= 0:
                    errors_in_row.append({'field': 'unit_purchase_price', 'error': 'Unit purchase price must be a positive number.'})
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

        if errors_in_row:
            validation_errors.append({'row': row_num, 'errors': errors_in_row})
        else:
            # If the row is valid, add the cleaned and validated data to list for database creation
            valid_data_list.append(cleaned_row_data)

    return valid_data_list, validation_errors


@transaction.atomic
def create_transactions_from_data(valid_data: List[Dict]) -> int:
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
        The number of transaction records successfully created.
    """
    created_count = 0
    for data in valid_data:
        # Using .create() ensures the model's .save() method is called.
        Transaction.objects.create(**data)
        created_count += 1

    return created_count