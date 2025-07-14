
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.core.models import Transaction
from .filters import TransactionFilter

class TransactionListView(ListView):
    """
    A view that displays a list of transactions with filtering and pagination.
    This view uses the TransactionFilter to allow users to filter the transaction
    list based on various criteria. The results are paginated to ensure good
    performance with large datasets.
    """
    model = Transaction
    template_name = 'ai_analytics/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 25  # Show 25 transactions per page

    def get_queryset(self):
        """
        Returns the queryset of transactions to be displayed.
        This method applies the filters from the TransactionFilter to the
        base queryset of all transactions.
        """
        queryset = super().get_queryset().select_related('block', 'procurement_method')
        self.filterset = TransactionFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        """
        Adds the filterset and paginated queryset to the template context.
        This method ensures that the filter form and pagination controls
        are available in the template.
        """
        context = super().get_context_data(**kwargs)
        
        # Add the filterset to the context to be used in the template
        context['filter'] = self.filterset

        # Handle pagination
        paginator = Paginator(self.get_queryset(), self.paginate_by)
        page = self.request.GET.get('page')
        try:
            transactions = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            transactions = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            transactions = paginator.page(paginator.num_pages)

        context['transactions'] = transactions
        return context