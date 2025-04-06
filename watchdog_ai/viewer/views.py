# viewer/views.py
import pandas as pd
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from datetime import datetime
from decimal import Decimal
from .models import Transaction, Anomaly

class UploadView(View):
    def get(self, request):
        return render(request, 'viewer/upload.html')

    def post(self, request):
        if 'file' not in request.FILES:
            messages.error(request, "Please upload a CSV file.")
            return redirect('upload')

        file = request.FILES['file']
        try:
            # Read CSV file
            df = pd.read_csv(file)
            required_columns = [
                "transaction_id", "item_name", "quantity", "procurement_method",
                "unit_price", "average_price", "supplier", "procurement_officer", "transaction_date"
            ]
            if not all(col in df.columns for col in required_columns):
                messages.error(request, "CSV file must contain columns: transaction_id, item_name, quantity, procurement_method, unit_price, average_price, supplier, procurement_officer, transaction_date")
                return redirect('upload')

            # Store transactions in the database(will update soon to delete the transactions when reloading the page)
            for _, row in df.iterrows():
                Transaction.objects.update_or_create(
                    transaction_id=row["transaction_id"],
                    defaults={
                        "item_name": row["item_name"],
                        "quantity": row["quantity"],
                        "procurement_method": row["procurement_method"],
                        "unit_price": row["unit_price"],
                        "average_price": row["average_price"],
                        "supplier": row["supplier"],
                        "procurement_officer": row["procurement_officer"],
                        "transaction_date": datetime.strptime(row["transaction_date"], "%Y-%m-%d").date()
                    }
                )
            messages.success(request, "File successfully parsed, validated, and added to blockchain.")
        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
        return redirect('upload')

        # Transaction reset
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
        start_date = request.GET.get("start_date", "2025-03-01")
        end_date = request.GET.get("end_date", "2025-04-04")
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