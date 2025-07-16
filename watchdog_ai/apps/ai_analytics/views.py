
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import numpy as np
from sklearn.ensemble import IsolationForest
from apps.core.models import Transaction
from .filters import TransactionFilter
from django.urls import reverse
from celery.result import AsyncResult

from apps.core.models import AnalysisReport
from .forms import AnalysisConfigurationForm
from .tasks import perform_anomaly_detection

class TransactionListView(ListView):
    """
    A view that displays a list of transactions with filtering, sorting, and pagination.
    This view uses the TransactionFilter to allow users to filter the transaction
    list based on various criteria, and supports sorting by different columns.
    Pagination is enabled for performance, but "Select All" works across all pages.
    """
    model = Transaction
    template_name = 'ai_analytics/transaction_list.html'
    paginate_by = 25  # Show 25 transactions per page

    def get_queryset(self):
        """
        Returns the queryset of transactions to be displayed.
        This method applies the filters from the TransactionFilter and sorting to the
        base queryset of all transactions.
        """
        queryset = super().get_queryset().select_related('block', 'procurement_method')
        self.filterset = TransactionFilter(self.request.GET, queryset=queryset)
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-transaction_date')  # Default sort by transaction date descending
        order = self.request.GET.get('order', 'desc')
        
        # Validate sort field to prevent injection
        allowed_sort_fields = {
            'transaction_id': 'transaction_id',
            'item_name': 'item_name',
            'total_purchase_price': 'total_purchase_price',
            'supplier': 'supplier',
            'transaction_date': 'transaction_date',
            'blockchain_status': 'blockchain_status',
            'project_name': 'project_name',
            'end_user_unit': 'end_user_unit',
            'quantity': 'quantity',
            'unit_purchase_price': 'unit_purchase_price',
            'average_price': 'average_price',
            'approved_budget': 'approved_budget',
            'procurement_method': 'procurement_method__name',
            'procurement_officer': 'procurement_officer',
            'invoice_number': 'invoice_number',
            'payment_receipt_number': 'payment_receipt_number',
            'invitation_to_bid_posting_date': 'invitation_to_bid_posting_date',
            'bid_submission_deadline': 'bid_submission_deadline',
            'bid_opening_date': 'bid_opening_date',
            'notice_of_award_date': 'notice_of_award_date',
            'contract_signing_date': 'contract_signing_date',
            'created_at': 'created_at',
        }
        
        if sort_by in allowed_sort_fields:
            sort_field = allowed_sort_fields[sort_by]
            if order == 'asc':
                queryset = self.filterset.qs.order_by(sort_field)
            else:
                queryset = self.filterset.qs.order_by(f'-{sort_field}')
        else:
            # Default sorting if invalid sort field
            queryset = self.filterset.qs.order_by('-transaction_date')
        
        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds the filterset and sorting information to the template context.
        This method ensures that the filter form and sorting state are available in the template.
        Also provides data for cross-page selection functionality.
        """
        context = super().get_context_data(**kwargs)
        
        # Add the filterset to the context to be used in the template
        context['filter'] = self.filterset
        
        # Add sorting information
        context['current_sort'] = self.request.GET.get('sort', 'transaction_date')
        context['current_order'] = self.request.GET.get('order', 'desc')
        
        # Get the total count of all filtered transactions (across all pages)
        # This is used for the "Select All" functionality
        context['total_filtered_count'] = self.filterset.qs.count()
        
        return context

@require_POST
def select_transactions(request):
    """
    Receives selected transaction IDs and handles both individual selections
    and "select all minus deselected" scenarios.
    """
    # Check if this is a "select all" request
    select_all = request.POST.get('select_all') == 'true'
    deselected_ids = request.POST.getlist('deselected_ids[]')
    
    if select_all:
        # Get all filtered transaction IDs
        # We need to apply the same filters as the list view
        queryset = Transaction.objects.all()
        
        # Create a mock request with GET parameters for filtering
        # The filter parameters are sent as POST data with the same names as GET parameters
        mock_get = request.POST.copy()
        # Remove the select_all and deselected_ids parameters
        if 'select_all' in mock_get:
            del mock_get['select_all']
        for key in list(mock_get.keys()):
            if key.startswith('deselected_ids'):
                del mock_get[key]
        
        filterset = TransactionFilter(mock_get, queryset=queryset)
        all_filtered_ids = list(filterset.qs.values_list('id', flat=True))
        
        # Remove deselected IDs
        deselected_ids = [int(id) for id in deselected_ids]
        transaction_ids = [id for id in all_filtered_ids if id not in deselected_ids]
    else:
        # Individual selections
        transaction_ids = request.POST.getlist('transaction_ids[]')
        transaction_ids = [int(id) for id in transaction_ids]
    
    request.session['selected_transaction_ids'] = transaction_ids
    print(f"DEBUG: Stored {len(transaction_ids)} transaction IDs in session")
    return redirect('analysis_configuration')

def analysis_configuration(request):
    """
    Displays the analysis configuration form.
    """
    transaction_ids = request.session.get('selected_transaction_ids', [])
    print(f"DEBUG: Retrieved {len(transaction_ids)} transaction IDs from session")
    
    if not transaction_ids:
        # Redirect if no transactions were selected
        return redirect('transaction_list')

    # Get the actual count of transactions (not just the IDs list length)
    # This handles the case where we have all filtered transactions selected
    if isinstance(transaction_ids, list) and len(transaction_ids) > 0:
        # Check if this might be a "select all" scenario by looking at the count
        # If we have a large number of IDs, it's likely select all
        transaction_count = len(transaction_ids)
    else:
        transaction_count = 0

    if request.method == 'POST':
        form = AnalysisConfigurationForm(request.POST)
        if form.is_valid():
            # This logic is now handled by run_analysis view via fetch
            pass
    else:
        form = AnalysisConfigurationForm(initial={
            'transaction_ids': json.dumps(transaction_ids)
        })

    return render(request, 'ai_analytics/analysis_configuration.html', {
        'form': form,
        'transaction_count': transaction_count
    })

@require_POST
def run_analysis(request):
    """
    Initiates the asynchronous analysis task via a fetch request.
    """
    try:
        data = json.loads(request.body)
        contamination = data.get('contamination')
        transaction_ids = data.get('transaction_ids')

        # Basic validation
        if not all([contamination, transaction_ids]):
             return JsonResponse({'success': False, 'error': 'Missing parameters.'}, status=400)

        # Validate transaction IDs exist
        try:
            transaction_count = Transaction.objects.filter(id__in=transaction_ids).count()
            if transaction_count == 0:
                return JsonResponse({'success': False, 'error': 'No valid transactions found.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error validating transactions: {str(e)}'}, status=400)

        # Start the Celery task
        try:
            task = perform_anomaly_detection.delay(transaction_ids, float(contamination))
            return JsonResponse({'success': True, 'task_id': task.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error starting analysis task: {str(e)}'}, status=500)
            
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return JsonResponse({'success': False, 'error': f'Invalid request data: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'}, status=500)

def get_task_status(request, task_id):
    """
    Pollable endpoint to check the status of a Celery task.
    """
    try:
        task_result = AsyncResult(task_id)
        result = {
            'task_id': task_id,
            'status': task_result.status,
        }
        if task_result.ready():
            # If task is finished, include the result
            task_output = task_result.get()
            result['result'] = task_output
            # Provide a URL to the results page
            if task_output and isinstance(task_output, dict) and task_output.get('status') == 'Completed':
                analysis_run_id = task_output.get('analysis_run_id')
                if analysis_run_id:
                    result['redirect_url'] = reverse('analysis_results', args=[analysis_run_id])

        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            'task_id': task_id,
            'status': 'FAILURE',
            'error': str(e)
        }, status=500)

def analysis_results(request, analysis_run_id):
    """
    Displays the results of a specific analysis run.
    """
    anomalous_reports = AnalysisReport.objects.filter(
        analysis_run_id=analysis_run_id,
        is_anomaly=True
    ).select_related('transaction').order_by('-anomaly_score')
    
    return render(request, 'ai_analytics/analysis_results.html', {
        'reports': anomalous_reports,
        'analysis_run_id': analysis_run_id
    })

def analysis_report_detail(request, report_id):
    """
    Displays the detailed report for a single transaction analysis.
    """
    report = get_object_or_404(AnalysisReport.objects.select_related('transaction'), pk=report_id)
    
    # SHAP values are stored as a JSON string in the model
    shap_values_data = json.loads(report.shap_values) if report.shap_values else None
    
    return render(request, 'ai_analytics/analysis_report_detail.html', {
        'report': report,
        'shap_values_data': shap_values_data
    })
    