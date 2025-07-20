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


def validate_transaction_db_ids(transaction_ids_raw: List[str]) -> List[int]:
    """
    Validate and convert raw transaction IDs to database IDs.
    
    Args:
        transaction_ids_raw: List of transaction ID strings
        
    Returns:
        List of valid transaction database IDs
    """
    valid_ids = []
    for id_str in transaction_ids_raw:
        try:
            if str(id_str).isdigit():
                valid_ids.append(int(id_str))
        except (ValueError, TypeError):
            logger.debug(f"Invalid transaction ID format: {id_str}")
            continue
    
    return valid_ids


def validate_session_transaction_ids(transaction_ids: List[int]) -> Tuple[bool, List[int], Optional[str]]:
    """
    Validate that session transaction IDs still exist in the database.
    
    Args:
        transaction_ids: List of transaction database IDs from session
        
    Returns:
        Tuple of (is_valid, valid_ids, error_message)
    """
    if not transaction_ids:
        return False, [], "No transaction IDs provided."
    
    try:
        # Check if IDs exist in database
        existing_ids = set(Transaction.objects.filter(id__in=transaction_ids).values_list('id', flat=True))
        missing_ids = set(transaction_ids) - existing_ids
        
        if missing_ids:
            logger.warning(f"Session transaction IDs not found in database: {missing_ids}")
        
        valid_ids = [id for id in transaction_ids if id in existing_ids]
        
        if not valid_ids:
            return False, [], "No valid transaction IDs remain in database."
        
        logger.info(f"Session validation: {len(transaction_ids)} submitted, {len(valid_ids)} valid")
        return True, valid_ids, None
        
    except Exception as e:
        logger.error(f"Error validating session transaction IDs: {e}")
        return False, [], f"Error validating session transaction IDs: {str(e)}"


def validate_transaction_ids(ids: List, check_existence: bool = True) -> Tuple[bool, List[int], Optional[str]]:
    """
    Unified validation for transaction IDs.
    
    Args:
        ids: List of transaction IDs to validate
        check_existence: Whether to verify IDs exist in database (default: True)
        
    Returns:
        Tuple of (is_valid, valid_ids, error_message)
    """
    if not ids:
        logger.info("No transaction IDs provided for validation")
        return False, [], "No transaction IDs provided."
    
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
            logger.warning(f"Filtered out {invalid_count} invalid transaction IDs")
        
        if not valid_ids:
            logger.warning("No valid transaction IDs found after validation")
            return False, [], "No valid transaction IDs found."
        
        # Check if IDs exist in database (if requested)
        if check_existence:
            existing_ids = set(Transaction.objects.filter(id__in=valid_ids).values_list('id', flat=True))
            missing_ids = set(valid_ids) - existing_ids
            
            if missing_ids:
                logger.warning(f"Transaction IDs not found in database: {missing_ids}")
                valid_ids = [id for id in valid_ids if id in existing_ids]
            
            if not valid_ids:
                return False, [], "No valid transaction IDs remain in database."
        
        logger.info(f"Validation complete: {len(ids)} submitted, {len(valid_ids)} valid")
        return True, valid_ids, None
        
    except Exception as e:
        logger.error(f"Error validating transaction IDs: {e}")
        return False, [], f"Error validating transaction IDs: {str(e)}"


def validate_analysis_parameters(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Comprehensive validation for analysis parameters.
    
    Args:
        data: Dictionary containing analysis parameters
        
    Returns:
        Tuple of (is_valid, validated_data, error_message)
    """
    # Extract parameters
    raw_contamination = data.get('contamination')
    transaction_ids = data.get('transaction_ids')
    
    # Basic validation
    if not all([raw_contamination, transaction_ids]):
        return False, None, 'Missing parameters.'
    
    # Validate contamination
    try:
        contamination_float = float(raw_contamination)
        if not (0.0 <= contamination_float <= 0.5):
            return False, None, 'Contamination must be between 0.0 and 0.5.'
    except (ValueError, TypeError):
        return False, None, 'Invalid contamination value.'


    # Validate transaction IDs format
    if not isinstance(transaction_ids, list):
        return False, None, 'Transaction IDs must be a list.'
   
    
    # Validate and clean transaction IDs
    is_valid, valid_transaction_ids, error_msg = validate_transaction_ids(transaction_ids)
    if not is_valid:
        return False, None, error_msg
    
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
