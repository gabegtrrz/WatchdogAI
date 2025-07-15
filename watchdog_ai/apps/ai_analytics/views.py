
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
    A view that displays a list of transactions with filtering, sorting, and pagination.
    This view uses the TransactionFilter to allow users to filter the transaction
    list based on various criteria, and supports sorting by different columns.
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
        """
        context = super().get_context_data(**kwargs)
        
        # Add the filterset to the context to be used in the template
        context['filter'] = self.filterset
        
        # Add sorting information
        context['current_sort'] = self.request.GET.get('sort', 'transaction_date')
        context['current_order'] = self.request.GET.get('order', 'desc')
        
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
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            transaction_ids = data.get('transaction_ids', [])
            contamination = float(data.get('contamination', 0.05))

            transactions = Transaction.objects.filter(id__in=transaction_ids)
            
            if not transactions:
                return JsonResponse({'error': 'No transactions found for analysis.'}, status=400)

            # A subset of numerical features are used for the model.
            feature_names = [
                'total_purchase_price', 'quantity', 'unit_purchase_price', 
                'approved_budget', 'average_price'
            ]
            
            X, valid_transactions = [], []
            for t in transactions:
                features = [float(getattr(t, name) or 0) for name in feature_names]
                X.append(features)
                valid_transactions.append(t)

            if not X:
                return JsonResponse({'error': 'Not enough data for analysis.'}, status=400)

            # An Isolation Forest model is used to detect anomalies.
            rng = np.random.RandomState(42)
            model = IsolationForest(contamination=contamination, random_state=rng)
            predictions = model.fit_predict(np.array(X))
            
            # Anomalies are marked as -1 by the model.
            anomaly_indices = np.where(predictions == -1)[0]
            
            results = {
                'total_transactions': len(valid_transactions),
                'anomalies_detected': len(anomaly_indices),
                'contamination_factor': contamination,
                'analyzed_transactions': []
            }
            
            for i, t in enumerate(valid_transactions):
                results['analyzed_transactions'].append({
                    'id': t.id,
                    'transaction_id': t.transaction_id,
                    'item_name': t.item_name,
                    'total_purchase_price': t.total_purchase_price,
                    'supplier': t.supplier,
                    'transaction_date': t.transaction_date.strftime('%Y-%m-%d'),
                    'is_anomaly': bool(i in anomaly_indices)
                })
            
            request.session['analysis_results'] = results
            return JsonResponse({'success': True, 'redirect_url': '/ai_analytics/analysis/results/'})

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            return JsonResponse({'error': f'Invalid request data: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
            
    return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)

def analysis_results_view(request):
    """
    Displays the anomaly detection results.

    This view retrieves the analysis results from the session and renders
    them in a template. If no results are found, it redirects to the
    transaction list.
    """
    results = request.session.get('analysis_results')
    if not results:
        return redirect('transaction_list')
        
    return render(request, 'ai_analytics/analysis_results.html', {'results': results})