from django.views import View
from django.views.generic import ListView

from django.core.paginator import Paginator

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages

# File Handling
from django.db import transaction, IntegrityError

import pandas as pd
from decimal import Decimal

from datetime import datetime, date, timedelta
from django.utils import timezone

# Local imports
from .models import Transaction, Anomaly, BlockchainTransactionData
from .blockchain import create_new_block_instance

class UploadView(View):
    def get(self, request):
        return render(request, 'viewer/upload.html')

    @transaction.atomic
    def post(self, request):

       # validating file upload 
        if 'file' not in request.FILES:
            messages.error(request, "No CSV file uploaded.")
            return redirect('upload')

        # validating file type
        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            messages.error(request, "Please upload a valid csv file.")
            return redirect('upload')
        
        
        try:
            # Read CSV file
            df = pd.read_csv(file)

            # validating columns
            required_columns = { 
                "transaction_id", "item_name", "quantity", "procurement_method",
                "unit_price", "average_price", "supplier", "procurement_officer", 
                "transaction_date" 
            }
            missing_cols = required_columns - set(df.columns)
            if missing_cols:
                messages.error(request, f"CSV is missing required columns: {', '.join(missing_cols)}")
                return redirect('upload')
            extra_cols = set(df.columns) - required_columns
            if extra_cols:
                 messages.warning(request, f"CSV contains extra columns (will be ignored): {', '.join(extra_cols)}")
            
            ### Integrating Blockchain ###
            # get latest block's state reliably
            try:
                latest_block_from_db = BlockchainTransactionData.objects.latest('block_number')
                last_hash = latest_block_from_db.block_hash
                last_index = latest_block_from_db.block_number
            except BlockchainTransactionData.DoesNotExist:
                # Genesis case: No blocks in the database yet
                last_hash = "0" * 64 #full-length zero hash for consistency
                last_index = -1 


            ### collect new block data before saving ###
            blocks_to_create = [] # 
            row_num = 1 # For user-friendly error messages

            for index, row in df.iterrows():
                row_num += 1 #starting from row 2 assuming that column names = row 1
                try:
                    # 2. prepare and validate row data (add more validation and erro handlng later)
                    
                    #convrt row to dict, handle potential NaN/None, enforce types
                    transaction_details = {
                        "transaction_id": int(pd.to_numeric(row["transaction_id"])),
                        "item_name": str(row["item_name"]).strip(),
                        "quantity": int(pd.to_numeric(row['quantity'])),
                        "procurement_method": str(row["procurement_method"]).strip(),
                        # Use Decimal for prices, handle potential errors/NaN bcause decimal only acccepts string/numerical values
                        "unit_price": Decimal(str(row["unit_price"])) if pd.notna(row["unit_price"]) else None,
                        "average_price": Decimal(str(row["average_price"])) if pd.notna(row["average_price"]) else None,
                        "supplier": str(row["supplier"]).strip() if pd.notna(row["supplier"]) else None,
                        "procurement_officer": str(row["procurement_officer"]).strip() if pd.notna(row["procurement_officer"]) else None,
                        # Parsing date robustly
                        "transaction_date": datetime.strptime(str(row["transaction_date"]).strip(), "%Y-%m-%d").date() if pd.notna(row["transaction_date"]) else None
                    }

                    if transaction_details['unit_price'] is None or transaction_details['unit_price'] < 0:
                         raise ValueError(f"Unit price cannot be empty or negative. Check {transaction_details['transaction_id']}")
                    if transaction_details['transaction_date'] is None:
                        raise ValueError(f"Transaction date cannot be empty. Check {transaction_details['transaction_id']}")
                    
                    # !!!3. create new block instance (in-memory)
                    for key, value in transaction_details.items():
                        if isinstance(value, Decimal):
                            transaction_details[key] = float(value)
                        elif isinstance(value, date):
                            transaction_details[key] = value.isoformat()

                    

                    new_block_obj = create_new_block_instance(
                        validated_transaction_data=transaction_details,
                        last_block_index=last_index,
                        last_block_hash=last_hash
                        )
                    
                    # 4. Prepare BlockchainTransactionData model instance for saving
                    block_transaction_db_instance = BlockchainTransactionData(
                        block_hash=new_block_obj.hash,
                        block_number=new_block_obj.index,
                        previous_hash=new_block_obj.previous_hash,
                        timestamp=new_block_obj.timestamp, # Use timestamp from Block object
                        transaction_data_json=new_block_obj.transaction_data, # Store the exact data used for hashing

                        #populating mirrored query fields
                        transaction_id_query=transaction_details.get("transaction_id"),
                        item_name_query=transaction_details.get("item_name"),
                        supplier_query=transaction_details.get("supplier"),
                        transaction_date_query=transaction_details.get("transaction_date"),
                       procurement_method_query =transaction_details.get("procurement_method")
                    )

                    # 5. append to blocks_to_create
                    blocks_to_create.append(block_transaction_db_instance)

                    # !!! Update for next block in the loop
                    last_hash = new_block_obj.hash
                    last_index = new_block_obj.index



                except (ValueError, TypeError, KeyError) as validation_error:
                    #catch error for specific row
                    messages.error(request, f"Error processing CSV row {row_num}: {validation_error}. Upload cancelled and rolled-back.")
                    raise IntegrityError(f"CSV Row {row_num} validation failed.") from validation_error

            ### !!! 6 Bulk Create 
            if blocks_to_create:
                BlockchainTransactionData.objects.bulk_create(blocks_to_create)
                messages.success(request, f"{len(blocks_to_create)} transactions successfully processed and added to the blockchain ledger.")
            else:
                 messages.warning(request, "CSV file processed, but no valid transaction rows were found to add.")


        except IntegrityError:
            pass # The transaction.atomic ensures rollback happened

        except Exception as e:
            messages.error(request, f"An unexpected error occured: {e}")
             # Rollback is handled by @transaction.atomic
        
        return redirect('upload') 

# -------------------

class BlockchainTransactionListView(ListView):
    model = BlockchainTransactionData
    template_name = 'viewer/blockchain_view.html'
    #Name of the variable in the template context
    context_object_name = 'blockchain_blocks' 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_blocks'] = self.model.objects.count()

        return context


# -------------------
        
class ResetTransactionsView(View):
    def post(self, request):
        try:
            Transaction.objects.all().delete()
            Anomaly.objects.all().delete()
            messages.success(request, "All transactions and anomalies have been successfully reset.")
        except Exception as e:
            messages.error(request, f"Error resetting transactions: {str(e)}")
        return redirect('upload')

class TransactionView(View):
    def get(self, request):
        # Filters
        today = date.today()
        one_month_ago = today - timedelta(days=30)


        start_date = request.GET.get("start_date", one_month_ago.strftime("%Y-%m-%d"))
        end_date = request.GET.get("end_date", today.strftime("%Y-%m-%d"))
        supplier = request.GET.get("supplier", "")
        procurement_method = request.GET.get("procurement_method", "")

        # Query transactions
        transactions = Transaction.objects.all()
        if start_date:
            try:
                transactions = transactions.filter(transaction_date__gte=datetime.strptime(start_date, "%Y-%m-%d").date())
            except ValueError:
                messages.error(request, "Invalid start date format.")
        if end_date:
            try:
                transactions = transactions.filter(transaction_date__lte=datetime.strptime(end_date, "%Y-%m-%d").date())
            except ValueError:
                messages.error(request, "Invalid end date format.")
        if supplier:
            transactions = transactions.filter(supplier=supplier)
        if procurement_method:
            transactions = transactions.filter(procurement_method=procurement_method)

        # Pagination
        page = int(request.GET.get("page", 1))
        per_page = 10
        total = transactions.count()
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = page * per_page
        transactions = transactions[start:end]

        # Suppliers and methods for dropdowns
        suppliers = Transaction.objects.values_list("supplier", flat=True).distinct()
        methods = Transaction.objects.values_list("procurement_method", flat=True).distinct()

        return render(request, 'viewer/transactions.html', {
            "transactions": transactions,
            "suppliers": suppliers,
            "methods": methods,
            "start_date": start_date,
            "end_date": end_date,
            "current_page": page,
            "total_pages": total_pages,
            "selected_supplier": supplier,
            "selected_method": procurement_method,
            "today": today,
            "one_month_ago": one_month_ago,
        })

class AnomalyDetectionView(View):
    def post(self, request):
        # Validate contamination
        try:
            contamination = float(request.POST.get("contamination", 0.1))
            if not 0 <= contamination <= 0.5:
                return JsonResponse({"error": "Contamination must be between 0.0 and 0.5"}, status=400)
        except ValueError as e:
            return JsonResponse({"error": "Contamination must be a valid number"}, status=400)

        # Fetch transactions
        transactions = Transaction.objects.all()
        if not transactions.exists():
            return JsonResponse({"status": "success", "anomalies": []}, status=200)

        # Run anomaly detection
        Anomaly.objects.all().delete()  # Clear previous anomalies
        anomalies = []
        for transaction in transactions:
            if transaction.average_price is None:
                continue

            try:
                unit_price = Decimal(str(transaction.unit_price))
                avg_price = Decimal(str(transaction.average_price))
            except (ValueError, TypeError):
                continue

            if avg_price == 0:
                continue

            try:
                percentage_diff = ((unit_price - avg_price) / avg_price) * 100
            except Exception:
                continue

            if abs(percentage_diff) > 20:
                try:
                    anomaly = Anomaly.objects.create(
                        transaction=transaction,
                        anomaly_score=f"Unit price {abs(percentage_diff):.1f}% {'above' if percentage_diff > 0 else 'below'} average"
                    )
                    anomalies.append({
                        "transaction_id": transaction.transaction_id,
                        "item_name": transaction.item_name,
                        "unit_price": float(transaction.unit_price),
                        "procurement_method": transaction.procurement_method,
                        "anomaly_score": anomaly.anomaly_score
                    })
                except Exception:
                    continue

        return JsonResponse({"status": "success", "anomalies": anomalies}, status=200)

class ExportAnomaliesView(View):
    def get(self, request):
        anomalies = Anomaly.objects.all()
        if not anomalies:
            return HttpResponse("No anomalies found.", content_type="text/plain")

        
        import csv
        from io import StringIO
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Transaction ID", "Item Name", "Unit Price", "Procurement Method", "Anomaly Score"])
        for anomaly in anomalies:
            writer.writerow([
                anomaly.transaction.transaction_id,
                anomaly.transaction.item_name,
                anomaly.transaction.unit_price,
                anomaly.transaction.procurement_method,
                anomaly.anomaly_score
            ])
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="anomalies.csv"'
        return response

class ReportsView(View):
    def get(self, request):
        return render(request, 'viewer/reports.html')