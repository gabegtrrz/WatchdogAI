import logging
from typing import List, Tuple, Optional, Dict, Any
from django.http import JsonResponse
from apps.core.models import Transaction

logger = logging.getLogger(__name__)


def validate_contamination(contamination: Any) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate contamination parameter for anomaly detection.
    
    Args:
        contamination: The contamination value to validate
        
    Returns:
        Tuple of (is_valid, contamination_float, error_message)
    """
    try:
        contamination_float = float(contamination)
        if not (0.0 <= contamination_float <= 1.0):
            return False, None, 'Contamination must be between 0.0 and 1.0.'
        return True, contamination_float, None
    except (ValueError, TypeError):
        return False, None, 'Invalid contamination value.'


def validate_transaction_ids_format(transaction_ids: Any) -> Tuple[bool, Optional[List], Optional[str]]:
    """
    Validate that transaction_ids is a list format.
    
    Args:
        transaction_ids: The transaction IDs to validate
        
    Returns:
        Tuple of (is_valid, transaction_ids_list, error_message)
    """
    if not isinstance(transaction_ids, list):
        return False, None, 'Transaction IDs must be a list.'
    return True, transaction_ids, None


def validate_transaction_db_ids(ids: List) -> List[int]:
    """
    Validate transaction database IDs are valid integers and exist in database.
    
    Args:
        ids: List of transaction IDs to validate
        
    Returns:
        List of valid integer IDs that exist in the database
    """
    if not ids:
        logger.info("No transaction IDs provided for validation")
        return []
    
    try:
        # Convert to integers, filtering out invalid values
        valid_ids = []
        invalid_count = 0
        
        for id_str in ids:
            try:
                if str(id_str).isdigit():
                    valid_ids.append(int(id_str))
                else:
                    invalid_count += 1
                    logger.debug(f"Invalid transaction ID format: {id_str}")
            except (ValueError, TypeError):
                invalid_count += 1
                logger.debug(f"Failed to convert transaction ID: {id_str}")
        
        if invalid_count > 0:
            logger.warning(f"Filtered out {invalid_count} invalid transaction database IDs")
        
        if not valid_ids:
            logger.warning("No valid transaction IDs found after validation")
            return []
        
        # Check if IDs exist in database
        existing_ids = set(Transaction.objects.filter(id__in=valid_ids).values_list('id', flat=True))
        missing_ids = set(valid_ids) - existing_ids
        
        if missing_ids:
            logger.warning(f"Transaction database IDs not found in database: {missing_ids}")
            valid_ids = [id for id in valid_ids if id in existing_ids]
        
        logger.info(f"Validation complete: {len(ids)} submitted, {len(valid_ids)} valid and existing")
        return valid_ids
        
    except Exception as e:
        logger.error(f"Error validating transaction database IDs: {e}")
        return []


def validate_session_transaction_ids(transaction_ids: List[int]) -> Tuple[bool, List[int], Optional[str]]:
    """
    Validate that session transaction IDs still exist in the database.
    
    Args:
        transaction_ids: List of transaction IDs from session
        
    Returns:
        Tuple of (is_valid, valid_ids, error_message)
    """
    try:
        existing_count = Transaction.objects.filter(id__in=transaction_ids).count()
        if existing_count != len(transaction_ids):
            logger.warning(f"Session contains {len(transaction_ids)} IDs but only {existing_count} exist in database")
            # Get only existing IDs
            existing_ids = list(Transaction.objects.filter(id__in=transaction_ids).values_list('id', flat=True))
            
            if not existing_ids:
                return False, [], "No valid transaction IDs remain in database."
            
            return True, existing_ids, None
        
        return True, transaction_ids, None
        
    except Exception as e:
        logger.error(f"Error validating session transaction IDs: {e}")
        return False, [], f"Error validating session transaction IDs: {str(e)}"


def validate_analysis_parameters(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Comprehensive validation for analysis parameters.
    
    Args:
        data: Dictionary containing analysis parameters
        
    Returns:
        Tuple of (is_valid, validated_data, error_message)
    """
    # Extract parameters
    contamination = data.get('contamination')
    transaction_ids = data.get('transaction_ids')
    
    # Basic validation
    if not all([contamination, transaction_ids]):
        return False, None, 'Missing parameters.'
    
    # Validate contamination
    is_valid_contamination, contamination_float, contamination_error = validate_contamination(contamination)
    if not is_valid_contamination:
        return False, None, contamination_error
    
    # Validate transaction IDs format
    is_valid_format, transaction_ids_list, format_error = validate_transaction_ids_format(transaction_ids)
    if not is_valid_format:
        return False, None, format_error
    
    # Validate and clean transaction IDs
    valid_transaction_ids = validate_transaction_db_ids(transaction_ids_list)
    if not valid_transaction_ids:
        return False, None, 'No valid transactions found.'
    
    # Double-check that all IDs exist in database
    existing_count = Transaction.objects.filter(id__in=valid_transaction_ids).count()
    if existing_count != len(valid_transaction_ids):
        logger.warning(f"Analysis requested for {len(valid_transaction_ids)} IDs but only {existing_count} exist")
        return False, None, 'Some transaction IDs are no longer valid.'
    
    logger.info(f"Analysis parameters validated: {len(valid_transaction_ids)} transactions with contamination {contamination_float}")
    
    validated_data = {
        'contamination': contamination_float,
        'transaction_ids': valid_transaction_ids
    }
    
    return True, validated_data, None


def create_validation_error_response(error_message: str, status: int = 400) -> JsonResponse:
    """
    Create a standardized error response for validation failures.
    
    Args:
        error_message: The error message to include
        status: HTTP status code (default: 400)
        
    Returns:
        JsonResponse with error details
    """
    return JsonResponse({
        'success': False,
        'error': error_message
    }, status=status)
