from django.contrib import admin
from .models import Block


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
