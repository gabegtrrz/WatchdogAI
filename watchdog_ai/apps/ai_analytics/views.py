
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
from django.http import JsonResponse
import json
import numpy as np
from sklearn.ensemble import IsolationForest
from apps.core.models import Transaction
from .filters import TransactionFilter

class TransactionListView(ListView):
    """
    A view that displays a list of transactions with filtering and sorting.
    This view uses the TransactionFilter to allow users to filter the transaction
    list based on various criteria, and supports sorting by different columns.
    Server-side pagination has been disabled to show all transactions at once.
    """
    model = Transaction
    template_name = 'ai_analytics/transaction_list.html'
    # paginate_by = 25  # Removed to disable server-side pagination

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
        Since pagination is disabled, we create a mock paginator object for template compatibility.
        """
        context = super().get_context_data(**kwargs)
        
        # Add the filterset to the context to be used in the template
        context['filter'] = self.filterset
        
        # Add sorting information
        context['current_sort'] = self.request.GET.get('sort', 'transaction_date')
        context['current_order'] = self.request.GET.get('order', 'desc')
        
        # Since we're not using pagination, we need to create a mock paginator object
        # for template compatibility
        queryset = self.get_queryset()
        
        # Create a proper mock page object that's iterable
        class MockPage:
            def __init__(self, object_list, count):
                self.object_list = object_list
                self.paginator = MockPaginator(count)
                self.number = 1
                self.has_previous = False
                self.has_next = False
                self.previous_page_number = None
                self.next_page_number = None
                self.has_other_pages = False
            
            def __iter__(self):
                return iter(self.object_list)
            
            def __len__(self):
                return len(self.object_list)
        
        class MockPaginator:
            def __init__(self, count):
                self.count = count
                self.num_pages = 1
                self.page_range = [1]
        
        context['page_obj'] = MockPage(queryset, queryset.count())
        
        return context

def analysis_configuration_view(request):
    """
    Renders the analysis configuration page.
    """
    return render(request, 'ai_analytics/analysis_configuration.html')

def run_analysis_view(request):
    """
    Runs the anomaly detection analysis.

    This view takes a POST request with transaction IDs and a contamination
    percentage, runs an Isolation Forest model, and returns the results
    as JSON.
    """
    

def analysis_results_view(request):
    """
    Displays the anomaly detection results.

    This view retrieves the analysis results from the session and renders
    them in a template. If no results are found, it redirects to the
    transaction list.
    """
    