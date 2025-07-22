# Resource Tracking System

## Overview

The resource tracking system monitors detailed resource consumption during transaction processing from upload until successful blockchain integration. It provides comprehensive insights into CPU usage, memory consumption, database operations, and network requests.

## Features

### Resource Monitoring

- **CPU Usage**: Tracks CPU percentage during processing
- **Memory Usage**: Monitors memory consumption in MB
- **Database Operations**: Counts and times database queries
- **Network Requests**: Tracks external API calls and network operations
- **Processing Stages**: Breaks down resource usage by processing stage

### Processing Stages

1. **Upload**: File upload and validation
2. **Preprocessing**: Data processing and transaction creation
3. **Enrichment**: Data enrichment with market prices
4. **Blockchain Integration**: Blockchain integration and integrity checks

### Performance Metrics

- Execution time for each stage
- Success/failure rates
- Resource efficiency metrics
- Performance alerts for threshold violations

## Usage

### In Code

```python
from apps.performance_monitoring.services import create_resource_tracker

# Create a resource tracker
tracker = create_resource_tracker(transaction_count=5, user_id='user123')

# Track upload stage
with tracker.track_stage('upload'):
    valid_data, errors = process_transaction_csv(uploaded_file)

# Track preprocessing stage
with tracker.track_stage('preprocessing'):
    created_transactions = create_transactions_from_data(valid_data)

# Track enrichment stage
with tracker.track_stage('enrichment'):
    enrichment_stats = enrich_transaction_list(created_transactions)

# Track blockchain integration
with tracker.track_stage('blockchain_integration'):
    blockchain_success, blockchain_result = integrate_transaction_batch(created_transactions)

# Finalize and save metrics
resource_record = tracker.finalize()
```

### Management Commands

View resource usage statistics:

```bash
# Basic report (last 24 hours)
python manage.py view_resource_usage

# Detailed report for last 6 hours
python manage.py view_resource_usage --hours 6 --detailed

# JSON format output
python manage.py view_resource_usage --format json

# CSV format output
python manage.py view_resource_usage --format csv
```

### Web Dashboard

Access the performance dashboard at:

```
/performance-monitoring/dashboard/
```

## Database Schema

### ResourceUsage Model

```python
class ResourceUsage(models.Model):
    # Core tracking
    session_id = models.CharField(max_length=100)
    transaction_count = models.IntegerField(default=1)

    # Resource measurements
    cpu_usage_percent = models.FloatField(default=0.0)
    memory_usage_mb = models.FloatField(default=0.0)
    database_queries_count = models.IntegerField(default=0)
    database_queries_time_ms = models.FloatField(default=0.0)
    network_requests_count = models.IntegerField(default=0)
    network_requests_time_ms = models.FloatField(default=0.0)

    # Processing stages
    upload_time_ms = models.FloatField(default=0.0)
    preprocessing_time_ms = models.FloatField(default=0.0)
    enrichment_time_ms = models.FloatField(default=0.0)
    blockchain_integration_time_ms = models.FloatField(default=0.0)
    total_processing_time_ms = models.FloatField(default=0.0)

    # Status tracking
    upload_success = models.BooleanField(default=False)
    preprocessing_success = models.BooleanField(default=False)
    enrichment_success = models.BooleanField(default=False)
    blockchain_success = models.BooleanField(default=False)
    overall_success = models.BooleanField(default=False)

    # Error tracking
    error_stage = models.CharField(max_length=50, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    user_id = models.CharField(max_length=100, blank=True, null=True)
```

## API Endpoints

### Performance Dashboard

- **URL**: `/performance-monitoring/dashboard/`
- **Method**: GET
- **Description**: Web dashboard showing performance metrics and resource usage

### Resource Usage Detail

- **URL**: `/performance-monitoring/resource/<session_id>/`
- **Method**: GET
- **Description**: Detailed view of a specific resource usage session

### Resource Usage List

- **URL**: `/performance-monitoring/resource/list/`
- **Method**: GET
- **Parameters**:
  - `hours`: Time range (default: 24)
  - `success_only`: Filter successful sessions only

### Performance API

- **URL**: `/performance-monitoring/api/`
- **Method**: GET
- **Description**: JSON API for performance and resource data

## Metrics and Alerts

### Performance Thresholds

- **Blockchain Save**: 5 seconds
- **Anomaly Detection**: 30 seconds
- **Transaction Upload**: 10 seconds
- **Data Preprocessing**: 5 seconds
- **Feature Engineering**: 8 seconds
- **Model Prediction**: 15 seconds
- **End-to-End Upload**: 15 seconds
- **Single Transaction Upload**: 12 seconds
- **CSV Batch Upload**: 30 seconds

### Alert Severity Levels

- **Low**: 1.5x threshold
- **Medium**: 2.0x threshold
- **High**: 2.0x threshold
- **Critical**: 3.0x threshold

## Integration Points

The resource tracking system is automatically integrated into:

1. **Transaction Upload UI** (`apps/transaction_management/views.py`)

   - Tracks CSV file uploads
   - Monitors batch processing
   - Tracks blockchain integration

2. **Single Transaction Upload** (`apps/transaction_management/views.py`)

   - Tracks individual transaction processing
   - Monitors enrichment and blockchain integration

3. **API Endpoints** (`apps/transaction_management/views.py`)
   - Tracks API-based uploads
   - Monitors programmatic transaction creation

## Benefits

1. **Performance Optimization**: Identify bottlenecks in processing stages
2. **Resource Planning**: Understand resource requirements for scaling
3. **Error Detection**: Track where failures occur in the pipeline
4. **Capacity Planning**: Monitor system resource usage patterns
5. **Alerting**: Automatic alerts for performance degradation
6. **Historical Analysis**: Track performance trends over time

## Dependencies

- **psutil**: System resource monitoring (CPU, memory)
- **Django ORM**: Database operations tracking
- **Django Debug Toolbar**: Query counting (optional)

## Configuration

The system uses Django's built-in database query logging when `DEBUG=True`. For production, ensure query logging is enabled for accurate database metrics.

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```
