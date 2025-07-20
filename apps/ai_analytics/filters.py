
import django_filters
from django.forms import DateInput
from apps.core.models import Transaction, ProcurementMethod

class TransactionFilter(django_filters.FilterSet):
    """
    A filter set for the Transaction model, providing comprehensive filtering options for the UI.
    It supports range-based filtering for numeric and date fields, and choice-based filtering for foreign keys.
    """
    # --- Text Field Filters ---
    transaction_id = django_filters.CharFilter(lookup_expr='icontains', label='Transaction ID')
    project_name = django_filters.CharFilter(lookup_expr='icontains', label='Project Name')
    end_user_unit = django_filters.CharFilter(lookup_expr='icontains', label='End User Unit')
    item_name = django_filters.CharFilter(lookup_expr='icontains', label='Item Name')
    supplier = django_filters.CharFilter(lookup_expr='icontains', label='Supplier')
    procurement_officer = django_filters.CharFilter(lookup_expr='icontains', label='Procurement Officer')
    invoice_number = django_filters.CharFilter(lookup_expr='icontains', label='Invoice Number')
    payment_receipt_number = django_filters.CharFilter(lookup_expr='icontains', label='Payment Receipt Number')
    
    # --- Numeric Range Filters ---
    unit_purchase_price = django_filters.RangeFilter()
    total_purchase_price = django_filters.RangeFilter()
    quantity = django_filters.RangeFilter()
    average_price = django_filters.RangeFilter()
    approved_budget = django_filters.RangeFilter()

    # --- Date Range Filter ---
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

    # --- Foreign Key Filters ---
    procurement_method = django_filters.ModelChoiceFilter(
        queryset=ProcurementMethod.objects.all(),
        field_name='procurement_method',
        label='Procurement Method'
    )
    block__index = django_filters.NumberFilter(
        field_name='block__index',
        label='Block Index'
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
            'unit_purchase_price': ['exact'],
            'total_purchase_price': ['exact'],
            'quantity': ['exact'],
            'approved_budget': ['exact'],
            'average_price': ['exact'],
            'blockchain_status': ['exact'],
        }