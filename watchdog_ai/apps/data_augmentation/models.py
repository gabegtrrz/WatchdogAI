
from django.db import models
from django.utils import timezone

class ItemAveragePrice(models.Model):
    """
    Stores the calculated average price for an item on a specific day.
    This acts as a daily cache to avoid re-scraping the same item.
    """
    item_name = models.CharField(max_length=255, db_index=True)
    date = models.DateField(default=timezone.now, db_index=True)
    average_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Stores supplementary information like source URLs, number of sources, etc.
    details = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensures that we only have one price per item per day.
        unique_together = ('item_name', 'date')
        ordering = ['-date', 'item_name']

    def __str__(self):
        return f"{self.item_name} - {self.date}: {self.average_price}" 