# viewer/models.py
from django.db import models

class Transaction(models.Model):
    transaction_id = models.CharField(max_length=50, unique=True)
    item_name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    average_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # New field
    procurement_method = models.CharField(max_length=100)
    supplier = models.CharField(max_length=100)
    procurement_officer = models.CharField(max_length=100, null=True, blank=True)  # New field
    transaction_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.item_name}"

class Anomaly(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    anomaly_score = models.CharField(max_length=255)
    detected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anomaly for {self.transaction.transaction_id}"