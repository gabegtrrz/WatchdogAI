from django.contrib import admin
from .models import ItemAveragePrice


@admin.register(ItemAveragePrice)
class ItemAveragePriceAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'date', 'average_price', 'created_at')
    list_filter = ('date',)
    search_fields = ('item_name',)
    ordering = ('-date', 'item_name')

