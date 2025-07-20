from django.db import models
import uuid


from django.core.exceptions import ValidationError
import logging


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
    total_purchase_price = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True, # can be null if price or quantity are null
        blank=True,
        help_text="Total price for the transaction (quantity * unit_purchase_price)."
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

    # --- Procurement Timeline ---CRIT
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

    @property
    def calculated_total_purchase_price(self):
        """
        Calculates the total purchase price from quantity and unit price.
        """
        if self.quantity is not None and self.unit_purchase_price is not None:
            return self.quantity * self.unit_purchase_price
        return None