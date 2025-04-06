# viewer/views.py
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.contrib import messages

class UploadView(View):
    def get(self, request):
        return render(request, 'viewer/upload.html')

    def post(self, request):
        messages.success(request, "File successfully parsed, validated, and added to blockchain.")
        return redirect('upload')

class TransactionView(View):
    def get(self, request):
        # Placeholder data
        start_date = request.GET.get("start_date", "2025-03-01")
        end_date = request.GET.get("end_date", "2025-04-04")
        supplier = request.GET.get("supplier", "")
        procurement_method = request.GET.get("procurement_method", "")
        page = int(request.GET.get("page", 1))

        # Sample transactions (to be replaced with real data)
        transactions = [
            {"transaction_id": "10001", "item_name": "Compound Microscope (1000x)", "quantity": 10, "unit_price": 58000.00, "procurement_method": "Competitive Bidding", "supplier": "LabCorp"},
            {"transaction_id": "10002", "item_name": "Breaker 50mL", "quantity": 10, "unit_price": 100.00, "procurement_method": "Competitive Bidding", "supplier": "LabCorp"},
            # Add more sample data as needed
        ]
        suppliers = ["LabCorp"]
        methods = ["Competitive Bidding"]
        total_pages = 5  # Placeholder

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
        # Placeholder response
        anomalies = [
            {"transaction_id": "10001", "item_name": "Compound Microscope (1000x)", "unit_price": 58000.00, "procurement_method": "Competitive Bidding", "anomaly_score": "Unit price 25% above real-time average"},
            {"transaction_id": "10002", "item_name": "Breaker 50mL", "unit_price": 100.00, "procurement_method": "Competitive Bidding", "anomaly_score": "Unit price 20% above real-time average"},
        ]
        return JsonResponse({"status": "success", "anomalies": anomalies})

class ExportAnomaliesView(View):
    def get(self, request):
        return HttpResponse("Placeholder: Export anomalies as CSV", content_type="text/plain")

class ReportsView(View):
    def get(self, request):
        return render(request, 'viewer/reports.html')