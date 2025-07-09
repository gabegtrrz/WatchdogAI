from django.contrib import admin
from .models import Transaction, Item, ProcurementMethod


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin view for the Transaction model, providing a comprehensive interface
    for viewing and managing transactions.
    """
    list_display = (
        'transaction_id',
        'item_name',
        'quantity',
        'unit_purchase_price',
        'average_price', # Here for tracking only.
        'procurement_officer',
        'procurement_method',
        'supplier',
        'transaction_date',
        'block',
    )
    list_filter = ('transaction_date', 'supplier', 'procurement_method')
    search_fields = (
        'transaction_id',
        'item_name',
        'supplier',
        'procurement_officer',
        'procurement_method__name',
        'block__hash',
    )
    search_help_text = 'Search by Transaction ID, Item Name, Supplier, Officer, Method, or Block Hash.'
    
    # Use raw_id_fields for 'block' to handle large numbers of blocks efficiently.
    raw_id_fields = ('block',)
    # Use autocomplete for 'procurement_method' for a better user experience.
    autocomplete_fields = ('procurement_method',)
    
    ordering = ('-created_at',)
    readonly_fields = (
        'transaction_id', 'created_at', 'block', 'average_price', 'unit_purchase_price'
        )

    # Organize the detail view into logical sections.
    fieldsets = (
        ('Core Information', {
            'fields': ('transaction_id', 'item_name', 'quantity', 'transaction_date')
        }),
        ('Financials', {
            'fields': ('unit_purchase_price', 'average_price')
        }),
        ('Procurement Details', {
            'fields': ('supplier', 'procurement_officer', 'procurement_method')
        }),
        ('Blockchain Link', {
            'classes': ('collapse',),
            'fields': ('block', 'created_at'),
        }),
    )

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Item model.
    - Displays the name, ID, and a snippet of the description.
    - Allows searching by name.
    - Orders items alphabetically by name.
    """
    list_display = ('name', 'id', 'description')
    search_fields = ('name', 'id__iexact') # search by name or for an exact UUID
    ordering = ('name',)

@admin.register(ProcurementMethod)
class ProcurementMethodAdmin(admin.ModelAdmin):
    """

    Admin configuration for the ProcurementMethod model.
    - Displays the procurement method name.
    - Allows searching by name.
    """
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)