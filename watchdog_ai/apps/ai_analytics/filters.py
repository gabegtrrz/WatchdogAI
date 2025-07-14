
import django_filters
from django.forms import DateInput
from apps.core.models import Transaction, ProcurementMethod

class TransactionFilter(django_filters.FilterSet):
    """
    A filter set for the Transaction model that allows filtering transactions
    based on various fields. This class provides a comprehensive set of filters
    for the Transaction model, including range filters for numeric and date fields,
    and choice filters for fields with predefined options.
    """
    
    # Filter for the block index, accessed through the block foreign key.
    # This allows filtering transactions by the index of the block they belong to.
    block__index = django_filters.NumberFilter(
        field_name='block__index',
        label='Block Index'
    )

    # A range filter for the quantity field, allowing filtering by a min and max value.
    quantity = django_filters.RangeFilter()
    
    # Range filters for all decimal fields to allow filtering by a min and max value.
    unit_purchase_price = django_filters.RangeFilter()
    total_purchase_price = django_filters.RangeFilter()
    average_price = django_filters.RangeFilter()
    approved_budget = django_filters.RangeFilter()

    # Date range filters for all date fields.
    # Uses a DateInput widget for a better user experience in the browser.
    transaction_date = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )
    invitation_to_bid_posting_date = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )
    bid_submission_deadline = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )
    bid_opening_date = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )
    notice_of_award_date = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )
    contract_signing_date = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )
    created_at = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )
    last_blockchain_attempt = django_filters.DateFromToRangeFilter(
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date'})
    )

    # A choice filter for the procurement method, using a dropdown with all available methods.
    procurement_method = django_filters.ModelChoiceFilter(
        queryset=ProcurementMethod.objects.all()
    )

    # A choice filter for the blockchain status, using the choices defined in the model.
    blockchain_status = django_filters.ChoiceFilter(
        choices=Transaction.blockchain_status.field.choices
    )

    class Meta:
        model = Transaction
        fields = {
            'transaction_id': ['icontains'],
            'project_name': ['icontains'],
            'end_user_unit': ['icontains'],
            'item_name': ['icontains'],
            'supplier': ['icontains'],
            'procurement_officer': ['icontains'],
            'invoice_number': ['icontains'],
            'payment_receipt_number': ['icontains'],
            'blockchain_error': ['icontains'],
            'blockchain_retry_count': ['exact'],
        }