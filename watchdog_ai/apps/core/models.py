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
    !!! Remember to update the following if adding a new field:
        - methods:
            - to_dict()
            - clean()
            - save()
            - __str__()
        - transaction_management/services.py (if necessary)

    '''
    
    # --- Blockchain Linkage ---
    block = models.ForeignKey(
        'blockchain.Block',             # Link to the Block model
        on_delete=models.CASCADE,       # If a Block is deleted, its Transactions are also deleted
        related_name='transactions',    # Lets us do `block.transactions.all()` in Block model function
        null=True,                      # IMPORTANT: Allows the transaction to exist before adding to a block
        blank=True,                      # Also for allowing it to be unassigned
        db_index=True,
        help_text="The blockchain block that contains this transaction."
    )

    # --- Transaction Identification ---
    transaction_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True, # db_index for faster lookups
        help_text="Unique identifier for this transaction."
    ) 

    # --- Project Information ---
    project_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the project for this procurement transaction."
    )
    end_user_unit = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="End user unit or department for this procurement."
    )
    project_description = models.TextField(
        null=True,
        blank=True,
        help_text="Detailed description of the project."
    )
    

    # --- Item Details ---
    item_name = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        help_text="Name or description of the item being procured."
    )
    quantity = models.IntegerField(
        null=False, 
        blank=False,
        help_text="Number of units of the item being procured."
    )

    # --- Pricing ---
    unit_purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=False,
        blank=False,
        help_text="Price per unit of the item being procured."
    )
    average_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True, # Can be null/blank if not available
        blank=True,
        help_text="Average price per unit across similar transactions (if available)."
    ) 
    approved_budget = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Approved Budget for the Contract (ABC)."
    )

    # --- Procurement Method ---
    procurement_method = models.ForeignKey(
        'ProcurementMethod',
        on_delete=models.PROTECT,
        related_name='transactions',
        null=False, 
        blank=False,
        help_text="The method used for procurement (e.g., Public Bidding, Direct Contracting)."
    )

    # --- Supplier & Officer ---
    supplier = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        help_text="Supplier or vendor for this transaction."
    )
    procurement_officer = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Name of the procurement officer responsible for this transaction."
    )

    # --- Financial Tracking ---
    invoice_number = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        help_text="Invoice number for this transaction."
    )
    payment_receipt_number = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        help_text="Payment receipt number for this transaction."
    )

    # --- Procurement Timeline ---
    invitation_to_bid_posting_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the Invitation to Bid was posted, announcing the procurement to attract bidders."
    )
    bid_submission_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline for bidders to submit their proposals."
    )
    bid_opening_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when bids were publicly opened and reviewed."
    )
    notice_of_award_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the Notice of Award was issued to the winning bidder."
    )
    contract_signing_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the formal agreement (contract) was signed between the procuring entity and the supplier."
    )

    # --- Timestamps ---
    transaction_date = models.DateField(
        null=False, 
        blank=False,
        help_text="Date when the transaction was completed."
    ) # Date of the actual transaction
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this transaction record was created in the system."
    ) # Automatically sets on creation for auditing

    # --- Blockchain Integration Status ---
    blockchain_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Blockchain Integration'),
            ('integrated', 'Successfully Integrated'),
            ('failed', 'Blockchain Integration Failed'),
        ],
        default='pending',
        help_text="Status of blockchain integration for this transaction."
    )
    blockchain_error = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if blockchain integration failed."
    )
    blockchain_retry_count = models.IntegerField(
        default=0, # type: ignore
        help_text="Number of times blockchain integration has been retried."
    )
    last_blockchain_attempt = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last blockchain integration attempt."
    )

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
            'project_name': self.project_name,
            'end_user_unit': self.end_user_unit,
            'project_description': self.project_description,
            'approved_budget': str(self.approved_budget) if self.approved_budget is not None else None,
            'item_name': self.item_name,
            'quantity': self.quantity,
            # converting decimal to string for consistent hashing
            'unit_purchase_price': str(self.unit_purchase_price), 
            'average_price': str(self.average_price) if self.average_price is not None else None,
            # 'procurement_method': self.procurement_method,
            'procurement_method': self.procurement_method.name,
            'supplier': self.supplier,
            'procurement_officer': self.procurement_officer,
            'invoice_number': self.invoice_number,
            'payment_receipt_number': self.payment_receipt_number,
            'invitation_to_bid_posting_date': str(self.invitation_to_bid_posting_date) if self.invitation_to_bid_posting_date else None,
            'bid_submission_deadline': str(self.bid_submission_deadline) if self.bid_submission_deadline else None,
            'bid_opening_date': str(self.bid_opening_date) if self.bid_opening_date else None,
            'notice_of_award_date': str(self.notice_of_award_date) if self.notice_of_award_date else None,
            'contract_signing_date': str(self.contract_signing_date) if self.contract_signing_date else None,
            'transaction_date': str(self.transaction_date),
            'created_at': str(self.created_at) if self.created_at else None, # included created_at for full data representation, more secure if altered
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
        # Validate approved_budget if provided
        if self.approved_budget is not None and self.approved_budget <= 0:
            raise ValidationError({'approved_budget': 'Approved budget must be a positive value if provided.'})
        
    def save(self, *args, **kwargs):

        # Generate a unique transaction_id if one isn't provided
        if not self.transaction_id:
            self.transaction_id = uuid.uuid4().hex[:32]

        # ensures validation runs on every save.
        self.full_clean()

        super().save(*args, **kwargs)


    

class ProcurementMethod(models.Model):
    """Represents a method of procurement, e.g., 'Public Bidding'."""
    name = models.CharField(
        max_length=255, 
        unique=True,
        help_text="Name of the procurement method (e.g., Public Bidding, Direct Contracting)."
    )

    def __str__(self):
        return str(self.name)