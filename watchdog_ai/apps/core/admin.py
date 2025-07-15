from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import Transaction, ProcurementMethod, AnalysisReport
from apps.blockchain.integrity_service import integrity_service


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
        'get_integrity_status',
    )
    list_filter = ('transaction_date', 'supplier', 'procurement_method', 'blockchain_status')
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

    actions = ['verify_integrity', 'generate_hashes']

    def get_block_info(self, obj):
        """Display block information in a more user-friendly format."""
        if obj.block:
            return f"Block {obj.block.index} (DB ID: {obj.block.id})"
        return "Not linked to block"
    get_block_info.short_description = 'Blockchain Block'  # type: ignore
    get_block_info.admin_order_field = 'block__index'  # type: ignore

    def get_integrity_status(self, obj):
        """Display transaction integrity status with color coding."""
        if not obj.transaction_hash:
            return format_html(
                '<span style="color: orange;">⚠️ No Hash</span>'
            )
        elif obj.verify_transaction_integrity():
            return format_html(
                '<span style="color: green;">✅ Valid</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">❌ Compromised</span>'
            )
    get_integrity_status.short_description = 'Integrity Status'  # type: ignore

    def verify_integrity(self, request, queryset):
        """Admin action to verify transaction integrity."""
        integrity_results = integrity_service.verify_transaction_level_integrity(queryset)
        
        if integrity_results['compromised_transactions']:
            messages.error(
                request,
                f"⚠️ {len(integrity_results['compromised_transactions'])} transactions are compromised!"
            )
        else:
            messages.success(
                request,
                f"✅ All {len(integrity_results['valid_transactions'])} transactions are valid."
            )
        
        if integrity_results['unhashed_transactions']:
            messages.warning(
                request,
                f"⚠️ {len(integrity_results['unhashed_transactions'])} transactions don't have hashes."
            )
    
    verify_integrity.short_description = "Verify transaction integrity"

    def generate_hashes(self, request, queryset):
        """Admin action to generate transaction hashes."""
        unhashed_transactions = queryset.filter(transaction_hash__isnull=True)
        
        if not unhashed_transactions.exists():
            messages.info(request, "All selected transactions already have hashes.")
            return
        
        results = integrity_service.generate_transaction_hashes(unhashed_transactions)
        
        if results['hashes_generated'] > 0:
            messages.success(
                request,
                f"✅ Generated hashes for {results['hashes_generated']} transactions."
            )
        
        if results['errors']:
            messages.error(
                request,
                f"❌ Encountered {len(results['errors'])} errors during hash generation."
            )
    
    generate_hashes.short_description = "Generate transaction hashes"

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
            'fields': ('unit_purchase_price', 'average_price', 'total_purchase_price', 'approved_budget')
        }),
        ('Procurement Details', {
            'fields': ('supplier', 'procurement_officer', 'procurement_method', 'project_name', 'end_user_unit')
        }),
        ('Timeline', {
            'fields': (
                'invitation_to_bid_posting_date', 'bid_submission_deadline', 'bid_opening_date',
                'notice_of_award_date', 'contract_signing_date'
            )
        }),
        ('Blockchain Integration', {
            'fields': ('block', 'blockchain_status', 'blockchain_error', 'blockchain_retry_count'),
            'description': 'Blockchain integration status and error tracking'
        }),
        ('Integrity Verification', {
            'fields': ('transaction_hash', 'hash_created_at'),
            'description': 'Transaction hash for integrity verification'
        }),
    )


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


@admin.register(AnalysisReport)
class AnalysisReportAdmin(admin.ModelAdmin):
    """
    Admin view for the AnalysisReport model.
    Provides comprehensive view of AI analysis results with filtering and search capabilities.
    """
    list_display = (
        'get_transaction_id',
        'get_item_name',
        'get_supplier',
        'is_anomaly',
        'get_anomaly_score',
        'contamination_param',
        'created_at',
    )
    list_filter = (
        'is_anomaly',
        'created_at',
        'updated_at',
        'transaction__procurement_method',
        'transaction__supplier',
    )
    search_fields = (
        'transaction__transaction_id',
        'transaction__item_name',
        'transaction__supplier',
        'transaction__procurement_officer',
    )
    search_help_text = 'Search by Transaction ID, Item Name, Supplier, or Officer.'
    
    # Use raw_id_fields for transaction to handle large numbers efficiently
    raw_id_fields = ('transaction',)
    
    ordering = ('-created_at',)
    
    # Actions for bulk operations
    actions = ['mark_as_anomaly', 'mark_as_normal', 'recalculate_scores']
    
    # Read-only fields for non-superusers
    readonly_fields = ('created_at', 'updated_at')
    
    def get_transaction_id(self, obj):
        """Display transaction ID with link to transaction detail."""
        return obj.transaction.transaction_id
    get_transaction_id.short_description = 'Transaction ID'
    get_transaction_id.admin_order_field = 'transaction__transaction_id'
    
    def get_item_name(self, obj):
        """Display item name from related transaction."""
        return obj.transaction.item_name
    get_item_name.short_description = 'Item Name'
    get_item_name.admin_order_field = 'transaction__item_name'
    
    def get_supplier(self, obj):
        """Display supplier from related transaction."""
        return obj.transaction.supplier
    get_supplier.short_description = 'Supplier'
    get_supplier.admin_order_field = 'transaction__supplier'
    
    def get_anomaly_score(self, obj):
        """Display anomaly score with color coding and percentage."""
        if obj.anomaly_score is not None:
            percentage = obj.anomaly_percentage
            color = 'red' if obj.is_anomaly else 'green'
            return format_html(
                '<span style="color: {};">{:.2f} ({:.1f}%)</span>',
                color, obj.anomaly_score, percentage
            )
        return "N/A"
    get_anomaly_score.short_description = 'Anomaly Score'
    get_anomaly_score.admin_order_field = 'anomaly_score'
    
    def mark_as_anomaly(self, request, queryset):
        """Admin action to mark selected reports as anomalies."""
        updated = queryset.update(is_anomaly=True)
        messages.success(request, f"✅ Marked {updated} analysis reports as anomalies.")
    mark_as_anomaly.short_description = "Mark selected as anomalies"
    
    def mark_as_normal(self, request, queryset):
        """Admin action to mark selected reports as normal."""
        updated = queryset.update(is_anomaly=False)
        messages.success(request, f"✅ Marked {updated} analysis reports as normal.")
    mark_as_normal.short_description = "Mark selected as normal"
    
    def recalculate_scores(self, request, queryset):
        """Admin action placeholder for recalculating anomaly scores."""
        messages.info(request, "🔄 Recalculation functionality would be implemented here.")
    recalculate_scores.short_description = "Recalculate anomaly scores"
    
    def get_readonly_fields(self, request, obj=None):
        """Dynamically sets fields as read-only for non-superusers."""
        if request.user.is_superuser:
            return ('created_at', 'updated_at')
        return tuple(field.name for field in self.model._meta.fields)
    
    def has_add_permission(self, request):
        """Allow adding analysis reports only for superusers."""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting analysis reports only for superusers."""
        return request.user.is_superuser
    
    # Organize the detail view into logical sections
    fieldsets = (
        ('Transaction Information', {
            'fields': ('transaction',)
        }),
        ('Anomaly Detection Results', {
            'fields': ('is_anomaly', 'anomaly_score', 'contamination_param'),
            'description': 'AI model analysis results and parameters'
        }),
        ('Model Interpretability', {
            'fields': ('shap_values',),
            'description': 'SHAP values for feature importance analysis'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )