from django.db import models
from django.utils import timezone

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

# --------------------------

class BlockchainTransactionData(models.Model):
    # Core Blockchain fields

    block_hash = models.CharField(max_length=64, primary_key=True)
    block_number = models.IntegerField(db_index=True, unique=True, help_text="Sequential block number (index).") 
    previous_hash = models.CharField(max_length=64, db_index=True)
    timestamp = models.DateTimeField(db_index=True, default=timezone.now)

    # Stored Transaction Data (used for hashing and retrieval). storing the exact data used for hashing to ensure verification works reliably
    transaction_data_json = models.JSONField(help_text="The transaction data exactly as it was hashed (JSON format).") 

    ### Mirror fields for fast querying ###
    transaction_id_query = models.IntegerField(db_index=True, null=True, blank=True)
    item_name_query = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    supplier_query = models.CharField(max_length=100, db_index=True, null=True, blank=True)
    transaction_date_query = models.DateField(db_index=True, null=True, blank=True)
    procurement_method_query = models.CharField(db_index=True, max_length=50, null=True, blank=True,) #change later to procurement_method_id

    def __str__(self):
        # Ensure transaction_id exists in the JSON before accessing
        tid = self.transaction_data_json.get('transaction_id', 'N/A') 
        return f"Block {self.block_number} (Tx ID: {tid})"
    
    class Meta:
        ordering = ['block_number'] # Default ordering when fetching multiple blocks
        verbose_name = "Blockchain Record"
        verbose_name_plural = "Blockchain Records"



    






# --------------------------

class Anomaly(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    anomaly_score = models.CharField(max_length=255)
    detected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anomaly for {self.transaction.transaction_id}"