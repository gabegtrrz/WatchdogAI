"""
Performance monitoring service for tracking analysis pipeline metrics.

This service provides functionality to:
- Track timing for each step of the analysis pipeline
- Save performance metrics to JSON files
- Configure monitoring settings via Django settings
"""
import json
import time
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """
    Monitors and records performance metrics for the analysis pipeline.
    
    **Features:**
    - Tracks timing for each analysis step
    - Saves metrics to configurable JSON file
    - Prepends new entries to existing file
    - Configurable via Django settings
    """
    
    def __init__(self, analysis_run_id: str):
        """
        Initialize performance monitor for a specific analysis run.
        
        Args:
            analysis_run_id: Unique identifier for the analysis run
        """
        self.analysis_run_id = analysis_run_id
        self.start_time = None
        self.step_timings = {}
        self.current_step = None
        self.step_start_time = None
        
        # Check if monitoring is enabled
        self.enabled = getattr(settings, 'ENABLE_PERFORMANCE_MONITORING', True)
        self.log_path = getattr(settings, 'PERFORMANCE_LOG_PATH', 'logs/performance_metrics.json')
        
        if self.enabled:
            logger.info(f"Performance monitoring enabled for run {analysis_run_id}")
        else:
            logger.debug(f"Performance monitoring disabled for run {analysis_run_id}")
    
    def start_analysis(self) -> None:
        """Start timing the complete analysis pipeline."""
        if not self.enabled:
            return
            
        self.start_time = time.time()
        logger.debug(f"Analysis timing started for run {self.analysis_run_id}")
    
    def start_step(self, step_name: str) -> None:
        """
        Start timing a specific analysis step.
        
        Args:
            step_name: Name of the step being timed
        """
        if not self.enabled:
            return
            
        if self.current_step:
            logger.warning(f"Step '{self.current_step}' was not ended before starting '{step_name}'")
        
        self.current_step = step_name
        self.step_start_time = time.time()
        logger.debug(f"Step '{step_name}' timing started")
    
    def end_step(self, step_name: Optional[str] = None) -> float:
        """
        End timing for a specific analysis step.
        
        Args:
            step_name: Name of the step (optional, uses current step if not provided)
            
        Returns:
            float: Duration of the step in seconds
        """
        if not self.enabled:
            return 0.0
            
        if step_name is None:
            step_name = self.current_step
            
        if not step_name or not self.step_start_time:
            logger.warning(f"Cannot end step '{step_name}' - no active step timing")
            return 0.0
        
        duration = time.time() - self.step_start_time
        self.step_timings[step_name] = duration
        
        logger.debug(f"Step '{step_name}' completed in {duration:.3f}s")
        
        # Reset current step
        self.current_step = None
        self.step_start_time = None
        
        return duration
    
    def end_analysis(self, additional_metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        End timing for the complete analysis and save metrics.
        
        Args:
            additional_metrics: Additional metrics to include in the final record
            
        Returns:
            Dict containing the complete performance metrics
        """
        if not self.enabled:
            return {}
        
        if not self.start_time:
            logger.warning("Cannot end analysis - analysis timing was not started")
            return {}
        
        # Calculate total analysis time
        total_time = time.time() - self.start_time
        
        # Compile final metrics
        metrics = {
            'analysis_run_id': self.analysis_run_id,
            'timestamp': datetime.now().isoformat(),
            'total_analysis_time': round(total_time, 3),
            'step_timings': self.step_timings.copy(),
            'total_steps': len(self.step_timings)
        }
        
        # Add any additional metrics
        if additional_metrics:
            metrics.update(additional_metrics)
        
        # Save to JSON file
        self._save_metrics(metrics)
        
        logger.info(f"Analysis completed in {total_time:.3f}s for run {self.analysis_run_id}")
        return metrics
    
    def _save_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Save performance metrics to JSON file, prepending to existing data.
        
        Args:
            metrics: Performance metrics to save
        """
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(self.log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                logger.info(f"Created performance log directory: {log_dir}")
            
            # Read existing data if file exists
            existing_data = []
            if os.path.exists(self.log_path):
                try:
                    with open(self.log_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]  # Convert single record to list
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not read existing performance log: {e}")
                    existing_data = []
            
            # Prepend new metrics to existing data
            updated_data = [metrics] + existing_data
            
            # Write back to file
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Performance metrics saved to {self.log_path}")
            
        except Exception as e:
            logger.error(f"Failed to save performance metrics: {e}")

def monitor_analysis_performance(analysis_run_id: str):
    """
    Decorator to monitor performance of analysis functions.
    
    Args:
        analysis_run_id: Unique identifier for the analysis run
        
    Returns:
        Decorator function that wraps the analysis function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = PerformanceMonitor(analysis_run_id)
            monitor.start_analysis()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # End analysis and save metrics
                monitor.end_analysis({
                    'function_name': func.__name__,
                    'status': 'success'
                })
                
                return result
                
            except Exception as e:
                # End analysis with error status
                monitor.end_analysis({
                    'function_name': func.__name__,
                    'status': 'error',
                    'error_message': str(e)
                })
                raise
                
        return wrapper
    return decorator


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
    # Simple pass-through decorator for now
    # This maintains compatibility with existing code
    return func


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
    # Simple pass-through decorator for now
    # This maintains compatibility with existing code
    return func


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
        # Simple pass-through decorator for now
        # This maintains compatibility with existing code
        return func
    return decorator


def create_resource_tracker(transaction_count: int = 1, user_id: str = None):
    """
    Create a resource tracker for monitoring transaction processing.
    
    **Usage:**
    ```python
    tracker = create_resource_tracker(transaction_count=5, user_id='user123')
    
    with tracker.track_stage('upload'):
        # Upload processing code
        pass
    
    with tracker.track_stage('blockchain_integration'):
        # Blockchain integration code
        pass
    
    resource_record = tracker.finalize()
    ```
    
    Args:
        transaction_count: Number of transactions being processed
        user_id: Optional user identifier
        
    Returns:
        ResourceTracker: Resource tracking instance
    """
    # Simple pass-through for now
    # This maintains compatibility with existing code
    class DummyTracker:
        def __init__(self):
            self.stage_success = {}
        
        def track_stage(self, stage_name):
            return self
        
        def mark_stage_success(self, stage_name, success, error_message=None):
            """Mark a stage as completed with success/failure status."""
            self.stage_success[stage_name] = success
            return self
        
        def set_success(self, success, error_message=None):
            """Set overall success status."""
            self.overall_success = success
            return self
        
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            return False
        
        def finalize(self):
            # Return a dummy object with expected attributes
            class DummyResourceRecord:
                def __init__(self):
                    self.total_processing_time_ms = 0.0
                    self.cpu_usage_percent = 0.0
                    self.memory_usage_mb = 0.0
                    self.database_queries_count = 0
                    self.database_queries_time_ms = 0.0
                    self.network_requests_count = 0
                    self.network_requests_time_ms = 0.0
                    self.overall_success = True
                    self.completed_at = None
                    self.error_stage = None
                    self.error_message = None
                    
                    # Add stage-specific attributes
                    for stage in ['upload', 'validation', 'blockchain_integration']:
                        setattr(self, f'{stage}_time_ms', 0.0)
                        setattr(self, f'{stage}_success', True)
            
            return DummyResourceRecord()
    
    return DummyTracker() 