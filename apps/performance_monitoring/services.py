"""
Performance monitoring service for tracking execution times
of critical operations like blockchain saves and anomaly detection.

**Features:**
- Decorator-based timing for easy integration
- Automatic metric storage and retrieval
- Performance alerting for threshold violations
- Context-aware logging with user/session tracking
"""

import time
import functools
import logging
from typing import Optional, Dict, Any, Callable
from django.utils import timezone
from django.db import transaction
from .models import PerformanceMetric, PerformanceAlert

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Service class for monitoring performance of critical operations.
    
    **Purpose:** Provides decorators and utilities for tracking
    execution times and generating performance metrics.
    """
    
    # Default thresholds in milliseconds
    DEFAULT_THRESHOLDS = {
        'blockchain_save': 5000.0,      # 5 seconds
        'anomaly_detection': 30000.0,   # 30 seconds
        'transaction_upload': 10000.0,   # 10 seconds
        'data_preprocessing': 5000.0,    # 5 seconds
        'feature_engineering': 8000.0,   # 8 seconds
        'model_prediction': 15000.0,     # 15 seconds
        'end_to_end_upload': 15000.0,   # 15 seconds (complete pipeline)
        'single_transaction_upload': 12000.0,  # 12 seconds (single transaction)
        'csv_batch_upload': 30000.0,    # 30 seconds (batch upload)
    }
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def monitor_operation(self, operation_type: str, 
                         threshold_ms: Optional[float] = None,
                         transaction_count: int = 1,
                         user_id: Optional[str] = None,
                         session_id: Optional[str] = None):
        """
        Decorator to monitor operation performance.
        
        **Usage:**
        ```python
        @performance_monitor.monitor_operation('blockchain_save')
        def save_to_blockchain(transactions):
            # Your blockchain save logic here
            pass
        ```
        
        Args:
            operation_type: Type of operation being monitored
            threshold_ms: Custom threshold in milliseconds (uses default if None)
            transaction_count: Number of transactions being processed
            user_id: Optional user identifier
            session_id: Optional session identifier
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error_message = None
                
                try:
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Check if result indicates failure
                    if isinstance(result, dict) and result.get('status') == 'error':
                        success = False
                        error_message = result.get('message', 'Unknown error')
                    
                    return result
                    
                except Exception as e:
                    success = False
                    error_message = str(e)
                    self.logger.error(f"Operation {operation_type} failed: {e}")
                    raise
                
                finally:
                    # Calculate execution time
                    execution_time_ms = (time.time() - start_time) * 1000
                    
                    # Store metric asynchronously to avoid blocking
                    self._store_metric_async(
                        operation_type=operation_type,
                        execution_time_ms=execution_time_ms,
                        transaction_count=transaction_count,
                        success=success,
                        error_message=error_message,
                        user_id=user_id,
                        session_id=session_id
                    )
                    
                    # Check for threshold violations
                    self._check_threshold_violation(
                        operation_type=operation_type,
                        execution_time_ms=execution_time_ms,
                        threshold_ms=threshold_ms
                    )
                    
                    # Log performance info
                    self.logger.info(
                        f"{operation_type} completed in {execution_time_ms:.2f}ms "
                        f"(success: {success}, transactions: {transaction_count})"
                    )
            
            return wrapper
        return decorator
    
    def _store_metric_async(self, **kwargs):
        """
        Store performance metric asynchronously to avoid blocking.
        
        **Purpose:** Prevents performance monitoring from affecting
        the performance of the monitored operations.
        """
        try:
            # Use Django's transaction.on_commit to store after transaction completes
            transaction.on_commit(
                lambda: self._store_metric_sync(**kwargs)
            )
        except Exception as e:
            # Fallback to immediate storage if on_commit fails
            self.logger.warning(f"Failed to schedule async metric storage: {e}")
            self._store_metric_sync(**kwargs)
    
    def _store_metric_sync(self, operation_type: str, execution_time_ms: float,
                          transaction_count: int, success: bool,
                          error_message: Optional[str] = None,
                          user_id: Optional[str] = None,
                          session_id: Optional[str] = None):
        """
        Synchronously store performance metric.
        
        **Purpose:** Internal method for storing metrics with error handling.
        """
        try:
            PerformanceMetric.objects.create(
                operation_type=operation_type,
                execution_time_ms=execution_time_ms,
                transaction_count=transaction_count,
                success=success,
                error_message=error_message,
                user_id=user_id,
                session_id=session_id
            )
        except Exception as e:
            self.logger.error(f"Failed to store performance metric: {e}")
    
    def _check_threshold_violation(self, operation_type: str, 
                                 execution_time_ms: float,
                                 threshold_ms: Optional[float] = None):
        """
        Check if execution time exceeds threshold and create alert if needed.
        
        **Purpose:** Automatically detect performance degradation
        and create alerts for monitoring.
        """
        if threshold_ms is None:
            threshold_ms = self.DEFAULT_THRESHOLDS.get(operation_type, 10000.0)
        
        if execution_time_ms > threshold_ms:
            # Determine severity based on how much threshold was exceeded
            ratio = execution_time_ms / threshold_ms
            if ratio > 3.0:
                severity = 'critical'
            elif ratio > 2.0:
                severity = 'high'
            elif ratio > 1.5:
                severity = 'medium'
            else:
                severity = 'low'
            
            # Create alert
            try:
                PerformanceAlert.objects.create(
                    operation_type=operation_type,
                    threshold_ms=threshold_ms,
                    actual_time_ms=execution_time_ms,
                    severity=severity,
                    message=f"Operation {operation_type} took {execution_time_ms:.2f}ms, "
                           f"exceeding threshold of {threshold_ms:.2f}ms"
                )
                
                self.logger.warning(
                    f"Performance alert created: {operation_type} exceeded "
                    f"threshold by {ratio:.1f}x ({execution_time_ms:.2f}ms > {threshold_ms:.2f}ms)"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to create performance alert: {e}")
    
    def get_average_time(self, operation_type: str, hours: int = 24) -> float:
        """
        Get average execution time for an operation.
        
        Args:
            operation_type: Type of operation
            hours: Number of hours to look back
            
        Returns:
            float: Average execution time in milliseconds
        """
        return PerformanceMetric.get_average_time(operation_type, hours)
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            dict: Performance summary for all operations
        """
        return PerformanceMetric.get_performance_summary(hours)
    
    def get_recent_alerts(self, hours: int = 24, severity: Optional[str] = None) -> list:
        """
        Get recent performance alerts.
        
        Args:
            hours: Number of hours to look back
            severity: Filter by severity level (optional)
            
        Returns:
            list: List of recent alerts
        """
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        queryset = PerformanceAlert.objects.filter(created_at__gte=cutoff_time)
        
        if severity:
            queryset = queryset.filter(severity=severity)
        
        return list(queryset.order_by('-created_at'))


# Global instance for easy access
performance_monitor = PerformanceMonitor()


def monitor_blockchain_save(func):
    """
    Convenience decorator for monitoring blockchain save operations.
    
    **Usage:**
    ```python
    @monitor_blockchain_save
    def save_transaction_to_blockchain(transaction):
        # Blockchain save logic
        pass
    ```
    """
    return performance_monitor.monitor_operation('blockchain_save')(func)


def monitor_anomaly_detection(func):
    """
    Convenience decorator for monitoring anomaly detection operations.
    
    **Usage:**
    ```python
    @monitor_anomaly_detection
    def analyze_transactions(transactions):
        # Anomaly detection logic
        pass
    ```
    """
    return performance_monitor.monitor_operation('anomaly_detection')(func)


def get_average_time(operation_type: str, hours: int = 24) -> float:
    """
    Simple function to get average execution time for an operation.
    
    Args:
        operation_type: Type of operation (e.g., 'single_transaction_upload')
        hours: Number of hours to look back (default: 24)
        
    Returns:
        float: Average execution time in milliseconds
    """
    return PerformanceMetric.get_average_time(operation_type, hours)


def get_performance_summary(hours: int = 24) -> dict:
    """
    Simple function to get performance summary for all operations.
    
    Args:
        hours: Number of hours to look back (default: 24)
        
    Returns:
        dict: Performance summary for all operations
    """
    return PerformanceMetric.get_performance_summary(hours)


def track_performance(operation_type: str, transaction_count: int = 1):
    """
    Simple decorator to track performance of functions.
    
    Usage:
    @track_performance('single_transaction_upload', transaction_count=1)
    def upload_transaction():
        # Your upload logic here
        pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Calculate execution time
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Store metric (simple, no complex async logic)
                try:
                    PerformanceMetric.objects.create(
                        operation_type=operation_type,
                        execution_time_ms=execution_time_ms,
                        transaction_count=transaction_count,
                        success=success,
                        error_message=error_message
                    )
                except Exception as e:
                    logger.error(f"Failed to store performance metric: {e}")
                
                # Log the result
                logger.info(f"{operation_type} completed in {execution_time_ms:.2f}ms (success: {success})")
        
        return wrapper
    return decorator 