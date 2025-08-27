# Simple Performance Monitoring

This system tracks how long it takes to save transactions to the blockchain and analyze them for anomalies.

## What We Track

- **Single Transaction Upload**: Time from form submission to blockchain block creation
- **CSV Batch Upload**: Time from file upload to blockchain block creation  
- **Anomaly Detection**: Time to analyze transactions for anomalies

## How to Use

### 1. Track Performance (Automatic)

The system automatically tracks performance when you upload transactions. No code changes needed!

### 2. Get Average Times

```python
from apps.performance_monitoring.services import get_average_time

# Get average time for single transaction uploads (last 24 hours)
avg_time = get_average_time('single_transaction_upload')
print(f"Average time: {avg_time:.2f}ms")

# Get average time for CSV batch uploads
avg_time = get_average_time('csv_batch_upload')
print(f"Average time: {avg_time:.2f}ms")
```

### 3. View Performance Data

```bash
# View all performance data
python manage.py view_performance

# View specific operation
python manage.py view_performance --operation-type single_transaction_upload

# Export as JSON
python manage.py view_performance --format json
```

### 4. API Endpoints

```bash
# Get performance summary
GET /performance/api/performance/summary/

# Get specific operation metrics
GET /performance/api/performance/operation/single_transaction_upload/

# Get end-to-end metrics
GET /performance/api/performance/end-to-end/
```

### 5. Admin Interface

Visit `/admin/` and look for:
- **Performance Metrics**: View all performance data
- **Performance Alerts**: View when operations are too slow

## Thresholds

| Operation | Threshold | Description |
|-----------|-----------|-------------|
| `single_transaction_upload` | 12 seconds | Single transaction upload |
| `csv_batch_upload` | 30 seconds | CSV batch upload |
| `anomaly_detection` | 30 seconds | AI analysis |

## Test the System

```bash
# Test with 5 sample operations
python manage.py test_performance --count 5
```

## Simple Example

```python
from apps.performance_monitoring.services import track_performance

@track_performance('my_operation', transaction_count=1)
def my_function():
    # Your code here
    pass
```

That's it! The system is simple and won't break your existing code. 