from django.contrib import admin
from .models import Transaction, Item, ProcurementMethod


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin view for the Transaction model. All fields are read-only to prevent
    manual changes, as transactions should be immutable once created.
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
        'get_block_info',
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

    def get_block_info(self, obj):
        """Display block information in a more user-friendly format."""
        if obj.block:
            return f"Block {obj.block.index} (DB ID: {obj.block.id})"
        return "Not linked to block"
    get_block_info.short_description = 'Blockchain Block'  # type: ignore
    get_block_info.admin_order_field = 'block__index'  # type: ignore

    def get_readonly_fields(self, request, obj=None):
        """Dynamically sets fields as read-only for non-superusers."""
        if request.user.is_superuser:
            return ()
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        """Allow adding transactions only for superusers."""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Allow deleting transactions only for superusers."""
        return request.user.is_superuser

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
            'fields': ('block',),
            'description': 'Block ID (first figure) shows database primary key, Block name (second figure) shows blockchain index'
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

    def get_readonly_fields(self, request, obj=None):
        """
        Makes all fields read-only for non-superusers.
        """
        if request.user.is_superuser:
            return ()
        return tuple(f.name for f in self.model._meta.fields)

    def has_add_permission(self, request):
        """
        Allows only superusers to add procurement methods.
        """
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """
        Allows only superusers to delete procurement methods.
        """
        return request.user.is_superuser