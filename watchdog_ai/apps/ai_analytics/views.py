
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
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

import logging
logger = logging.getLogger(__name__)

# Rate limiting constants
SELECT_RATE_LIMIT_SECONDS = 2  # Minimum seconds between selection requests
SELECT_RATE_LIMIT_MAX_ATTEMPTS = 5  # Max attempts per time window
SELECT_RATE_LIMIT_WINDOW = 40  # Time window in seconds for max attempts

# Analysis rate limiting (more restrictive due to resource intensity)
ANALYSIS_RATE_LIMIT_MAX_ATTEMPTS = 2  # Max analysis attempts per time window
ANALYSIS_RATE_LIMIT_WINDOW = 300  # 5 minutes window for analysis requests

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

def validate_transaction_db_ids(ids):
    """
    Validate transaction database IDs are valid integers and exist in database.
    Returns a list of valid integer IDs.
    """
    if not ids:
        logger.info("No transaction IDs provided for validation")
        return []
    
    try:
        # Convert to integers, filtering out invalid values
        valid_ids = []
        invalid_count = 0
        
        for id_str in ids:
            try:
                if str(id_str).isdigit():
                    valid_ids.append(int(id_str))
                else:
                    invalid_count += 1
                    logger.debug(f"Invalid transaction ID format: {id_str}")
            except (ValueError, TypeError):
                invalid_count += 1
                logger.debug(f"Failed to convert transaction ID: {id_str}")
        
        if invalid_count > 0:
            logger.warning(f"Filtered out {invalid_count} invalid transaction database IDs")
        
        if not valid_ids:
            logger.warning("No valid transaction IDs found after validation")
            return []
        
        # Check if IDs exist in database
        existing_ids = set(Transaction.objects.filter(id__in=valid_ids).values_list('id', flat=True))
        missing_ids = set(valid_ids) - existing_ids
        
        if missing_ids:
            logger.warning(f"Transaction database IDs not found in database: {missing_ids}")
            valid_ids = [id for id in valid_ids if id in existing_ids]
        
        logger.info(f"Validation complete: {len(ids)} submitted, {len(valid_ids)} valid and existing")
        return valid_ids
        
    except Exception as e:
        logger.error(f"Error validating transaction database IDs: {e}")
        return []

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
    try:
        existing_count = Transaction.objects.filter(id__in=transaction_ids).count()
        if existing_count != len(transaction_ids):
            logger.warning(f"Session contains {len(transaction_ids)} IDs but only {existing_count} exist in database")
            # Update session with only existing IDs
            existing_ids = list(Transaction.objects.filter(id__in=transaction_ids).values_list('id', flat=True))
            request.session['selected_transaction_ids'] = existing_ids
            transaction_ids = existing_ids
            
            if not transaction_ids:
                logger.warning("No valid transaction IDs remain, redirecting to transaction list")
                return redirect('transaction_list')
        
        transaction_count = len(transaction_ids)
        logger.info(f"Configuration page loaded with {transaction_count} valid transactions")
        
    except Exception as e:
        logger.error(f"Error validating session transaction IDs: {e}")
        # Clear invalid session data
        request.session.pop('selected_transaction_ids', None)
        return redirect('transaction_list')

# Analysis Configuration Form
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
        contamination = data.get('contamination')
        transaction_ids = data.get('transaction_ids')

    # Basic validation
        if not all([contamination, transaction_ids]):
             return JsonResponse({'success': False, 'error': 'Missing parameters.'}, status=400)

    # Validate contamination value
        try:
            contamination_float = float(contamination)
            if not (0.0 <= contamination_float <= 1.0):
                return JsonResponse({'success': False, 'error': 'Contamination must be between 0.0 and 1.0.'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid contamination value.'}, status=400)

        # Validate transaction IDs format and existence
        try:
            if not isinstance(transaction_ids, list):
                return JsonResponse({'success': False, 'error': 'Transaction IDs must be a list.'}, status=400)
            
            # Validate and clean transaction IDs
            valid_transaction_ids = validate_transaction_db_ids(transaction_ids)
            
            if not valid_transaction_ids:
                return JsonResponse({'success': False, 'error': 'No valid transactions found.'}, status=400)
            
            # Double-check that all IDs exist in database
            existing_count = Transaction.objects.filter(id__in=valid_transaction_ids).count()
            if existing_count != len(valid_transaction_ids):
                logger.warning(f"Analysis requested for {len(valid_transaction_ids)} IDs but only {existing_count} exist")
                return JsonResponse({'success': False, 'error': 'Some transaction IDs are no longer valid.'}, status=400)
                
            logger.info(f"Starting analysis for {len(valid_transaction_ids)} transactions with contamination {contamination_float}")
            
        except Exception as e:
            logger.error(f"Error validating transaction IDs for analysis: {e}")
            return JsonResponse({'success': False, 'error': f'Error validating transactions: {str(e)}'}, status=400)

    # Start the Celery task
        try:
            task = perform_anomaly_detection.delay(valid_transaction_ids, contamination_float)
            logger.info(f"Analysis task started with ID: {task.id}")
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
    