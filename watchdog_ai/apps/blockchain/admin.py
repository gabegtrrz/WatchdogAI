from django.contrib import admin
from django.utils.html import format_html
from .models import Block, IntegrityCheck


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    """
    Admin view for the Block model.
    """
    list_display = ('index', 'timestamp', 'hash', 'previous_hash')
    search_fields = (
        '^hash',
        '^previous_hash',
        'transactions__transaction_id',
        'transactions__item_name',
    )
    search_help_text = 'Search by current/previous hash, or by transaction ID/item name within the block.'
    ordering = ('-index',)


@admin.register(IntegrityCheck)
class IntegrityCheckAdmin(admin.ModelAdmin):
    """Admin interface for blockchain integrity checks."""
    
    list_display = [
        'timestamp', 
        'check_type', 
        'status_colored', 
        'transaction_count',
        'alert_sent_display',
        'integration_success_display'
    ]
    
    list_filter = [
        'check_type',
        'integrity_valid',
        'alert_sent',
        'integration_success',
        'timestamp'
    ]
    
    search_fields = [
        'transaction_ids',
        'error_message'
    ]
    
    readonly_fields = [
        'timestamp',
        'created_at',
        'status_colored',
        'transaction_list_display'
    ]
    
    fieldsets = (
        ('Check Information', {
            'fields': (
                'check_type',
                'timestamp',
                'status_colored'
            )
        }),
        ('Results', {
            'fields': (
                'integrity_valid',
                'alert_sent',
                'integration_success'
            )
        }),
        ('Transaction Details', {
            'fields': (
                'transaction_count',
                'transaction_ids',
                'transaction_list_display'
            )
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('System Info', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    def status_colored(self, obj):
        """Display status with color coding."""
        if obj.integrity_valid:
            color = 'green'
            icon = '✅'
            text = 'VALID'
        else:
            color = 'red'
            icon = '❌'
            text = 'COMPROMISED'
        
        alert_icon = ' 🚨' if obj.alert_sent else ''
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}{}</span>',
            color, icon, text, alert_icon
        )
    status_colored.short_description = 'Status'
    
    def alert_sent_display(self, obj):
        """Display alert status with icon."""
        if obj.alert_sent:
            return format_html('<span style="color: red;">🚨 YES</span>')
        return format_html('<span style="color: green;">✅ NO</span>')
    alert_sent_display.short_description = 'Alert Sent'
    
    def integration_success_display(self, obj):
        """Display integration success status."""
        if obj.integration_success is None:
            return format_html('<span style="color: gray;">N/A</span>')
        elif obj.integration_success:
            return format_html('<span style="color: green;">✅ SUCCESS</span>')
        else:
            return format_html('<span style="color: red;">❌ FAILED</span>')
    integration_success_display.short_description = 'Integration'
    
    def transaction_list_display(self, obj):
        """Display transaction IDs in a readable format."""
        transaction_list = obj.get_transaction_list()
        if not transaction_list:
            return "No transactions"
        
        if len(transaction_list) <= 5:
            return ", ".join(transaction_list)
        else:
            first_five = ", ".join(transaction_list[:5])
            return f"{first_five} ... (+{len(transaction_list)-5} more)"
    transaction_list_display.short_description = 'Transaction IDs'
    
    def has_add_permission(self, request):
        """Prevent manual creation of integrity checks."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make integrity checks read-only."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return request.user.is_superuser
