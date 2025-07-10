from django.db import models
import uuid


from django.core.exceptions import ValidationError
import logging

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from apps.blockchain.models import Block

# logging config
logger = logging.getLogger(__name__)


class Transaction(models.Model):
    '''
    Represents a single transaction record in the blockchain.
    Transactions are linked to a specific Block.
    '''


    '''
    Remember to update the following if adding a new field:
        - methods:
            - to_dict()
            - clean()
            - save()
            - __str__()
        - transaction_management services.py (if necessary)

    '''
    
    # --- Blockchain Linkage ---
    block = models.ForeignKey(
        'blockchain.Block',             # Link to the Block model
        on_delete=models.CASCADE,       # If a Block is deleted, its Transactions are also deleted
        related_name='transactions',    # Lets us do `block.transactions.all()` in Block model function
        null=True,                      # IMPORTANT: Allows the transaction to exist before adding to a block
        blank=True,                      # Also for allowing it to be unassigned
        db_index=True
    )

    # --- Transaction Identification ---
    transaction_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True, # db_index for faster lookups
    ) 

    # --- Item Details ---
    item_name = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )
    quantity = models.IntegerField(null=False, blank=False)

    # --- Pricing ---
    unit_purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=False,
        blank=False
    )
    average_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True, # Can be null/blank if not available
        blank=True
    ) 

    # --- Procurement Method ---
    procurement_method = models.ForeignKey(
        'ProcurementMethod',
        on_delete=models.PROTECT,
        related_name='transactions',
        null=False, blank=False
    )

    # --- Supplier & Officer ---
    supplier = models.CharField(
        max_length=100,
        null=False,
        blank=False
    )
    procurement_officer = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    # --- Timestamps ---
    transaction_date = models.DateField(null=False, blank=False) # Date of the actual transaction
    created_at = models.DateTimeField(auto_now_add=True) # Automatically sets on creation for auditing

    class Meta:
        ordering = ['-transaction_date', 'transaction_id']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"Transaction {self.transaction_id} for {self.item_name} ({self.quantity} units)"

    def to_dict(self):
        """
        Converts the Transaction object to a dictionary for hashing purposes.
        Ensures consistent data types and formats.
        """
        return {
            'transaction_id': self.transaction_id,
            'item_name': self.item_name,
            'quantity': self.quantity,
            # converting decimal to string for consistent hashing
            'unit_purchase_price': str(self.unit_purchase_price), 
            'average_price': str(self.average_price) if self.average_price is not None else None,
            # 'procurement_method': self.procurement_method,
            'procurement_method': self.procurement_method.name,
            'supplier': self.supplier,
            'procurement_officer': self.procurement_officer,
            'transaction_date': self.transaction_date.isoformat(),
            'created_at': self.created_at.isoformat() if self.created_at else None, # included created_at for full data representation, more secure if altered
        }

    def clean(self):
        """
        Custom validation for the Transaction model before saving.
        Ensures quantity and prices are positive.
        """
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be a positive integer.'})
        if self.unit_purchase_price is not None and self.unit_purchase_price <= 0:
            raise ValidationError({'unit_purchase_price': 'Unit purchase price must be a positive value.'})
        # Note: average_price can be null, so only validate if it's not null
        if self.average_price is not None and self.average_price <= 0:
            raise ValidationError({'average_price': 'Average price must be a positive value if provided.'})
        
    def save(self, *args, **kwargs):

        # Generate a unique transaction_id if one isn't provided
        if not self.transaction_id:
            self.transaction_id = uuid.uuid4().hex[:32]

        # ensures validation runs on every save.
        self.full_clean()

        super().save(*args, **kwargs)


class Item(models.Model):
    """Represents an item that can be procured."""
    # manual ID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} (ID: {self.id})"
    

class ProcurementMethod(models.Model):
    """Represents a method of procurement, e.g., 'Public Bidding'."""
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name