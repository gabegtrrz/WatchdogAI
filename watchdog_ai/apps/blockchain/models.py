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
    Represents a block in the blockchain.
    Each block contains an index, timestamp, a hash of the previous block,
    and its own hash which is calculated based on its contents (including transactions).
    """
    index = models.PositiveIntegerField(unique=True, null=False, blank=False, db_index=True)
    # unique=True on index. If the chain is ever reset or allowed forks, be aware of potential collisions.

    timestamp = models.DateTimeField(default=timezone.now, null=False, blank=False)
    previous_hash = models.CharField(max_length=64, null=False, blank=False) 
    hash = models.CharField(max_length=64, null=False, blank=False) 
    
    transactions: Manager['Transaction']

    class Meta:
        ordering = ['index'] 
        verbose_name = "Block"
        verbose_name_plural = "Blocks"


    def __str__(self):
        return f"Block {self.index} (Hash: {self.hash[:10]}...)" # truncate hash for readability

    def calculate_hash(self):
        """
        Calculates the SHA-256 hash of the block's contents.
        The hash is dependent on the block's index, timestamp, previous hash,
        and all transactions associated with this block.
        """
        try:
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