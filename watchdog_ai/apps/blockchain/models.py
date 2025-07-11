from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import json
import hashlib
from django.utils import timezone
import logging
from django.db.models.manager import Manager
from typing import TYPE_CHECKING



if TYPE_CHECKING:
    from .models import Block
    from apps.core.models import Transaction

# logging config
logger = logging.getLogger(__name__)



class Block(models.Model):
    """
    Represents a single block in the blockchain.
    
    Each block contains:
    - index: Sequential number in the chain
    - previous_hash: Hash of the previous block (creates the chain)
    - timestamp: When the block was created
    - hash: This block's unique hash
    """
    
    index = models.PositiveIntegerField(
        unique=True,
        null=False,
        blank=False,
        help_text="Sequential block number"
    )
    previous_hash = models.CharField(
        max_length=64,
        null=False,
        blank=False,
        help_text="Hash of the previous block"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        null=False,
        blank=False,
        help_text="When the block was created"
    )
    hash = models.CharField(max_length=64, unique=True, null=False, blank=False, help_text="This block's unique hash")
    
    class Meta:
        ordering = ['index'] 
        verbose_name = "Block"
        verbose_name_plural = "Blocks"


    def __str__(self):
        return f"Block {self.index} (Hash: {self.hash[:10]}...)" # truncate hash for readability

    def calculate_hash(self):
        """
        Calculates the SHA-256 hash for this block based on its content and linked transactions.
        
        The hash includes:
        - Block index
        - Previous block hash
        - Block timestamp
        - All transactions linked to this block
        
        Returns:
            str: The calculated SHA-256 hash
        """
        # Get all transactions associated with this block
        try:
            # If the block hasn't been saved yet (no primary key), return empty transaction list
            if self.pk is None:
                transaction_list = []
            else:
                transaction_list = [t.to_dict() for t in self.transactions.all().order_by('id')]
            # list comprehension correctly handles the case where there are no transactions,
            # resulting in an empty list, which is the desired behavior for hashing.

            block_content = {
                "index": self.index,
                "timestamp": self.timestamp.isoformat(),
                "transactions": transaction_list,
                "previous_hash": self.previous_hash
            }

            # used sort_keys=True and ensure all values are consistently typed for reproducible hashing

            # used separators because hashing is sensitive to every single byte of the input data
            # consistency is highly crucial in integrity verification
            # separator args: (item_separator, key_value_separator)

            block_string = json.dumps(block_content, sort_keys=True, separators=(',', ':')).encode('utf-8')
            
            return hashlib.sha256(block_string).hexdigest()
        
        except Exception as e:
            logger.error(f"Error calculating hash for Block {self.index}: {e}")

            raise ValueError(f"Failed to calculate hash for Block {self.index}: {e}")


class IntegrityCheck(models.Model):
    """
    Stores blockchain integrity verification results.
    
    This model tracks:
    - When integrity checks were performed
    - Results of the checks
    - Which transactions were involved
    - Whether alerts were sent
    """
    
    CHECK_TYPES = [
        ('BEFORE', 'Before Integration'),
        ('AFTER', 'After Integration'),
        ('SCHEDULED', 'Scheduled Check'),
        ('MANUAL', 'Manual Check'),
    ]
    
    # Basic information
    check_type = models.CharField(
        max_length=20, 
        choices=CHECK_TYPES,
        help_text="Type of integrity check performed"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the integrity check was performed"
    )
    
    # Check results
    integrity_valid = models.BooleanField(
        help_text="Whether blockchain integrity was valid"
    )
    alert_sent = models.BooleanField(
        default=False,  # type: ignore
        help_text="Whether an email alert was sent"
    )
    
    # Transaction information
    transaction_count = models.PositiveIntegerField(
        default=0,  # type: ignore
        help_text="Number of transactions involved in the check"
    )
    transaction_ids = models.TextField(
        blank=True,
        help_text="Comma-separated list of transaction IDs involved"
    )
    
    # Additional details
    error_message = models.TextField(
        blank=True,
        help_text="Error message if integrity check failed"
    )
    integration_success = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether the associated integration was successful (for AFTER checks)"
    )
    
    # Admin fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Integrity Check"
        verbose_name_plural = "Integrity Checks"
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['check_type']),
            models.Index(fields=['integrity_valid']),
        ]
    
    def __str__(self):
        status = "✅ VALID" if self.integrity_valid else "❌ COMPROMISED"
        alert = "🚨" if self.alert_sent else ""
        return f"{self.check_type} - {status} {alert} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
    
    def get_transaction_list(self):
        """Return transaction IDs as a list."""
        if not self.transaction_ids:
            return []
        return [tid.strip() for tid in self.transaction_ids.split(',') if tid.strip()]
    
    def set_transaction_list(self, transaction_ids):
        """Set transaction IDs from a list."""
        self.transaction_ids = ', '.join(str(tid) for tid in transaction_ids if tid)
    
    @property
    def status_display(self):
        """Human-readable status for admin display."""
        if self.integrity_valid:
            return "✅ Valid"
        else:
            return "❌ Compromised" + (" 🚨" if self.alert_sent else "")
    
    @classmethod
    def get_recent_checks(cls, days=7):
        """Get integrity checks from the last N days."""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=days)
        return cls.objects.filter(timestamp__gte=cutoff)
    
    @classmethod
    def get_failed_checks(cls):
        """Get all failed integrity checks."""
        return cls.objects.filter(integrity_valid=False)