
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
from typing import TYPE_CHECKING, Dict, Any
import json
import csv
from datetime import datetime

if TYPE_CHECKING:
    from apps.core.models import Transaction, AnalysisReport
else:
    from apps.core.models import Transaction, AnalysisReport
from .filters import TransactionFilter
from django.urls import reverse
from celery.result import AsyncResult
from .forms import AnalysisConfigurationForm
from .tasks import perform_anomaly_detection
from .services.validation import (
    validate_transaction_db_ids,
    validate_session_transaction_ids,
    validate_analysis_parameters,
    create_validation_error_response
)

import logging
logger = logging.getLogger(__name__)

# Rate limiting constants
SELECT_RATE_LIMIT_SECONDS = 2  # Minimum seconds between selection requests
SELECT_RATE_LIMIT_MAX_ATTEMPTS = 5  # Max attempts per time window
SELECT_RATE_LIMIT_WINDOW = 40  # Time window in seconds for max attempts

# Analysis rate limiting (more restrictive due to resource intensity)
ANALYSIS_RATE_LIMIT_MAX_ATTEMPTS = 100  # Max analysis attempts per time window
ANALYSIS_RATE_LIMIT_WINDOW = 200  # 200-sec window for analysis requests

def check_rate_limit(request, action_name):
    """
    Check if user has exceeded rate limits for the given action.
    Returns (is_allowed, remaining_attempts, reset_time)
    """
    # Create unique key for this user and action
    user_id = getattr(request.user, 'id', 'anonymous')
    cache_key = f"rate_limit_{action_name}_{user_id}"
    
    # Determine rate limits based on action
    if action_name == 'run_analysis':
        max_attempts = ANALYSIS_RATE_LIMIT_MAX_ATTEMPTS
        window = ANALYSIS_RATE_LIMIT_WINDOW
    else:
        max_attempts = SELECT_RATE_LIMIT_MAX_ATTEMPTS
        window = SELECT_RATE_LIMIT_WINDOW
    
    # Get current attempts
    attempts = cache.get(cache_key, 0)
    
    if attempts >= max_attempts:
        # Try to get remaining time until reset
        # Note: ttl() is not available in all cache backends (e.g., LocMemCache)
        try:
            ttl = cache.ttl(cache_key)
            reset_time = ttl if ttl else window
        except AttributeError:
            # Fallback for cache backends that don't support ttl()
            reset_time = window
        
        return False, 0, reset_time
    
    # Increment attempts
    cache.set(cache_key, attempts + 1, window)
    return True, max_attempts - attempts - 1, window

def apply_rate_limit(request, action_name):
    """
    Apply rate limiting and return appropriate response if limit exceeded.
    """
    is_allowed, remaining_attempts, reset_time = check_rate_limit(request, action_name)
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for user {getattr(request.user, 'id', 'anonymous')} on {action_name}")
        return JsonResponse({
            'success': False,
            'error': 'Too many requests. Please wait before trying again.',
            'rate_limit_reset': reset_time
        }, status=429)  # 429 Too Many Requests
    
    return None  # Continue with normal processing

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
        queryset = super().get_queryset().select_related('block', 'procurement_method') #holds the complete, unfiltered set of transactions, with the related objects pre-fetched.

        self.filterset = TransactionFilter(self.request.GET, queryset=queryset) #takes the unfiltered queryset and applies any filters present in self.request.GET. The resulting filtered queryset is now stored in the self.filterset.qs attribute. The original queryset variable is still unchanged
        
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
        
        # Validate sort field to prevent injection
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
    # Apply rate limiting
    rate_limit_response = apply_rate_limit(request, 'select_transactions')
    if rate_limit_response:
        return rate_limit_response
    
    try:
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
            
            # Safely convert deselected IDs to integers
            deselected_ids_int = []
            for id_str in deselected_ids:
                try:
                    deselected_ids_int.append(int(id_str))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid deselected ID format: {id_str}")
                    continue
            
            # Remove deselected IDs from the filtered list
            transaction_ids = [id for id in all_filtered_ids if id not in deselected_ids_int]
            
            logger.info(f"Select all mode: {len(all_filtered_ids)} total filtered, {len(deselected_ids_int)} deselected, {len(transaction_ids)} selected")
        else:
            # Individual selections
            transaction_ids_raw = request.POST.getlist('transaction_ids[]')
            transaction_ids = validate_transaction_db_ids(transaction_ids_raw)
            
            logger.info(f"Individual selection mode: {len(transaction_ids_raw)} submitted, {len(transaction_ids)} valid")
        
        # Store in session only if we have valid transaction IDs
        if transaction_ids:
            request.session['selected_transaction_ids'] = transaction_ids
            logger.info(f"Stored {len(transaction_ids)} transaction database IDs in session")
        else:
            # Clear any existing selection if no valid IDs
            request.session.pop('selected_transaction_ids', None)
            logger.warning("No valid transaction IDs found, clearing session selection")
        
        return redirect('analysis_configuration')
        
    except Exception as e:
        logger.error(f"Error in select_transactions: {e}")
        # Clear session on error to prevent stale data
        request.session.pop('selected_transaction_ids', None)
        return redirect('transaction_list')



def analysis_configuration(request):
    """
    Displays the analysis configuration form.
    """
    transaction_ids = request.session.get('selected_transaction_ids', [])
    logger.info(f"Retrieved {len(transaction_ids)} transaction IDs from session")
    
    if not transaction_ids:
        # Redirect if no transactions were selected
        logger.warning("No transaction IDs found in session, redirecting to transaction list")
        return redirect('transaction_list')

    # Validate that the stored IDs still exist in the database
    is_valid, valid_ids, error_message = validate_session_transaction_ids(transaction_ids)
    
    if not is_valid:
        logger.warning(f"Session validation failed: {error_message}")
        # Clear invalid session data
        request.session.pop('selected_transaction_ids', None)
        return redirect('transaction_list')
    
    # Update session with unique, validated IDs
    unique_ids = list(set(valid_ids))
    request.session['selected_transaction_ids'] = unique_ids
    transaction_count = len(unique_ids)
    logger.info(f"Configuration page loaded with {transaction_count} unique, valid transactions")

    form = AnalysisConfigurationForm(initial={
        'contamination': 5,  # Default to 5%
        'transaction_ids': json.dumps(unique_ids)
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
    # Temporary debugging
    print(f"DEBUG: run_analysis called")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Content-Type: {request.headers.get('Content-Type')}")
    print(f"DEBUG: Request body: {request.body}")
    
    # Apply rate limiting for analysis requests (more restrictive)
    rate_limit_response = apply_rate_limit(request, 'run_analysis')
    if rate_limit_response:
        print(f"DEBUG: Rate limited")
        return rate_limit_response
    
    try:
        data = json.loads(request.body)
        
        # Validate all analysis parameters
        is_valid, validated_data, error_message = validate_analysis_parameters(data)
        
        if not is_valid:
            return create_validation_error_response(error_message or "Validation failed")
        
        # validated_data is guaranteed to be a dict when is_valid is True
        validated_data: Dict[str, Any] = validated_data  # type: ignore
        contamination_float = validated_data['contamination']
        valid_transaction_ids = validated_data['transaction_ids']
        
        logger.info(f"Starting analysis for {len(valid_transaction_ids)} transactions with contamination {contamination_float}")

    # Start anomaly detection
        try:
            task = perform_anomaly_detection.delay(valid_transaction_ids, contamination_float)
            logger.info(f"Analysis task started with ID: {task.id}")
            
            # In eager mode, the task completes immediately
            if task.ready():
                result = task.get()
                if result.get('status') == 'Completed':
                    analysis_run_id = result.get('analysis_run_id')
                    return JsonResponse({
                        'success': True, 
                        'task_id': task.id,
                        'completed': True,
                        'redirect_url': reverse('analysis_results', args=[analysis_run_id]),
                        'contamination': contamination_float
                    })
                else:
                    return JsonResponse({
                        'success': False, 
                        'error': result.get('error', 'Analysis failed')
                    }, status=500)
            else:
                return JsonResponse({'success': True, 'task_id': task.id})
                
        except Exception as e:
            logger.error(f"Error starting analysis task: {e}")
            return JsonResponse({'success': False, 'error': f'Error starting analysis task: {str(e)}'}, status=500)
            
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.error(f"Invalid request data in run_analysis: {e}")
        return JsonResponse({'success': False, 'error': f'Invalid request data: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in run_analysis: {e}")
        return JsonResponse({'success': False, 'error': f'Unexpected error: {str(e)}'}, status=500)

def get_task_status(request, task_id):
    """
    Pollable endpoint to check the status of a Celery task with timeout and comprehensive error handling.
    """
    try:
        task_result = AsyncResult(task_id)
        result = {
            'task_id': task_id,
            'status': task_result.status,
        }
        
        if task_result.ready():
            try:
                task_output = task_result.get(timeout=5)  # 5 second timeout
                result['result'] = task_output
                # Provide a URL to the results page
                if task_output and isinstance(task_output, dict) and task_output.get('status') == 'Completed':
                    analysis_run_id = task_output.get('analysis_run_id')
                    if analysis_run_id:
                        result['redirect_url'] = reverse('analysis_results', args=[analysis_run_id])
            except TimeoutError:
                result['status'] = 'TIMEOUT'
                result['error'] = 'Task result retrieval timed out'
                logger.warning(f"Task {task_id} result retrieval timed out")
            except Exception as e:
                result['status'] = 'FAILURE'
                result['error'] = f'Task result error: {str(e)}'
                logger.error(f"Error retrieving task {task_id} result: {e}")

        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Task status check failed for {task_id}: {e}")
        return JsonResponse({
            'task_id': task_id,
            'status': 'FAILURE',
            'error': str(e)
        }, status=500)

def analysis_results(request, analysis_run_id):
    """
    Displays the results of a specific analysis run.
    Provides comprehensive context including summary statistics.
    """
    # Get all reports for this analysis run (both anomalous and normal)
    all_reports = AnalysisReport.objects.filter(
        analysis_run_id=analysis_run_id
    ).select_related('transaction')
    
    # Get only anomalous reports for display
    anomalous_reports = all_reports.filter(is_anomaly=True).order_by('-anomaly_score')
    
    # Calculate summary statistics
    total_transactions = all_reports.count()
    anomaly_count = anomalous_reports.count()
    
    # Get contamination parameter from the first report (all reports in a run use the same contamination)
    contamination_param = None
    if all_reports.exists():
        first_report = all_reports.first()
        contamination_param = first_report.contamination_param

    context = {
        'reports': anomalous_reports,
        'analysis_run_id': analysis_run_id,
        'total_transactions': total_transactions,
        'anomaly_count': anomaly_count,
        'contamination_param': contamination_param,
    }
    
    return render(request, 'ai_analytics/analysis_results.html', context)

def analysis_report_detail(request, report_id):
    """
    Displays the detailed report for a single transaction analysis.
    """
    report = get_object_or_404(AnalysisReport.objects.select_related('transaction'), pk=report_id)
    
    # SHAP values are stored as a JSONField in the model (automatically deserialized to dict)
    shap_values_data = report.shap_values if report.shap_values else None
    
    return render(request, 'ai_analytics/analysis_report_detail.html', {
        'report': report,
        'shap_values_data': shap_values_data
    })

def export_analysis_results_csv(request, analysis_run_id):
    """
    Export all analysis results for a specific analysis run to CSV format.
    Includes both anomalous and normal transactions with their analysis details and top anomalous features.
    """
    # Get all reports for this analysis run
    all_reports = AnalysisReport.objects.filter(
        analysis_run_id=analysis_run_id
    ).select_related('transaction')
    
    if not all_reports.exists():
        return HttpResponse("No analysis results found for this run.", status=404)
    
    # Create the HTTP response with CSV content type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="analysis_results_{analysis_run_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Define feature name mapping for better readability
    feature_name_mapping = {
        'unit_purchase_price': 'Unit Purchase Price',
        'total_purchase_price': 'Total Purchase Price',
        'quantity': 'Quantity',
        'average_price': 'Market Average Price',
        'price_deviation': 'Price Deviation',
        'procurement_method_encoded': 'Procurement Method',
        'supplier_encoded': 'Supplier',
        'item_category_encoded': 'Item Category',
        'procurement_officer_encoded': 'Procurement Officer',
        'end_user_unit_encoded': 'End User Unit',
        'transaction_date_encoded': 'Transaction Date',
        'price_to_average_ratio': 'Price to Average Ratio',
        'quantity_price_interaction': 'Quantity-Price Interaction'
    }
    
    # Write header row with top 5 anomalous features
    header_row = [
        'Transaction ID',
        'Item Name',
        'Supplier',
        'Procurement Method',
        'Quantity',
        'Unit Price',
        'Total Price',
        'Average Price',
        'Approved Budget',
        'Project Name',
        'End User Unit',
        'Procurement Officer',
        'Transaction Date',
        'Is Anomaly',
        'Anomaly Score',
        'Risk Score (%)',
        'Contamination Parameter',
        'Analysis Date',
        'Error Message'
    ]
    
    # Add top 5 anomalous features columns
    for i in range(1, 6):
        header_row.extend([
            f'Top {i} Feature',
            f'Top {i} Feature Score',
            f'Top {i} Feature Impact'
        ])
    
    writer.writerow(header_row)
    
    # Write data rows
    for report in all_reports:
        transaction = report.transaction
        
        # Calculate risk score percentage (absolute value * 100)
        risk_score_percentage = abs(report.anomaly_score * 100) if report.anomaly_score else 0
        
        # Get SHAP values for this report
        shap_values = report.shap_values if report.shap_values else {}
        
        # Process SHAP values to get top anomalous features
        top_features = []
        if shap_values and isinstance(shap_values, dict):
            try:
                # Convert to list of tuples (feature_name, shap_value) and sort by SHAP value (descending)
                feature_data = [(k, v) for k, v in shap_values.items() if isinstance(v, (int, float))]
                # Sort by SHAP value (descending) - higher values = more anomalous
                feature_data.sort(key=lambda x: x[1], reverse=True)
                
                # Take top 5 features
                for feature_name, shap_value in feature_data[:5]:
                    # Scale SHAP value by 100 for consistency with UI
                    scaled_value = shap_value * 100
                    # Determine impact direction
                    impact = "Increases Anomaly" if shap_value > 0 else "Decreases Anomaly"
                    # Get readable feature name
                    readable_name = feature_name_mapping.get(feature_name, feature_name.replace('_', ' ').title())
                    
                    top_features.extend([readable_name, f"{scaled_value:.2f}", impact])
            except (TypeError, ValueError) as e:
                # Log error but continue with empty features
                logger.warning(f"Error processing SHAP values for report {report.id}: {e}")
        
        # Pad with empty values if less than 5 features
        while len(top_features) < 15:  # 5 features * 3 columns each
            top_features.extend(['', '', ''])
        
        writer.writerow([
            transaction.transaction_id,
            transaction.item_name,
            transaction.supplier,
            transaction.procurement_method.name if transaction.procurement_method else '',
            transaction.quantity,
            float(transaction.unit_purchase_price) if transaction.unit_purchase_price else '',
            float(transaction.total_purchase_price) if transaction.total_purchase_price else '',
            float(transaction.average_price) if transaction.average_price else '',
            float(transaction.approved_budget) if transaction.approved_budget else '',
            transaction.project_name or '',
            transaction.end_user_unit or '',
            transaction.procurement_officer or '',
            transaction.transaction_date.strftime('%Y-%m-%d') if transaction.transaction_date else '',
            'Yes' if report.is_anomaly else 'No',
            report.anomaly_score or '',
            f"{risk_score_percentage:.2f}",
            report.contamination_param or '',
            report.created_at.strftime('%Y-%m-%d %H:%M:%S') if report.created_at else '',
            report.error_message or ''
        ] + top_features)
    
    return response
    