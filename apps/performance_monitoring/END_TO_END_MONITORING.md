# End-to-End Performance Monitoring

This document explains how the end-to-end performance monitoring system tracks the complete transaction upload workflow from submission to blockchain block creation.

## What We Measure

### 🎯 **Complete Workflow Timing**

We track the **total time** from when a user submits a transaction through the upload UI until the blockchain block is successfully created. This includes:

1. **Transaction Creation**: Saving the transaction to the database
2. **Data Enrichment**: Fetching market prices and enriching transaction data
3. **Blockchain Integration**: Creating the block and verifying integrity
4. **Success Confirmation**: Final blockchain block creation

### 📊 **Tracked Operations**

| Operation Type              | Description                        | Threshold  | Use Case                       |
| --------------------------- | ---------------------------------- | ---------- | ------------------------------ |
| `single_transaction_upload` | Single transaction form submission | 12 seconds | Individual transaction uploads |
| `csv_batch_upload`          | CSV file batch upload              | 30 seconds | Bulk transaction uploads       |
| `end_to_end_upload`         | Generic end-to-end tracking        | 15 seconds | Custom workflows               |

## How It Works

### 1. **Context Manager Integration**

The system uses a context manager to automatically track the entire workflow:

```python
from apps.performance_monitoring.services import EndToEndPerformanceTracker

def single_transaction_upload(request):
    if request.method == 'POST':
        form = SingleTransactionUploadForm(request.POST)
        if form.is_valid():
            # Track the complete workflow
            with EndToEndPerformanceTracker('single_transaction_upload', transaction_count=1) as tracker:
                # 1. Create transaction
                new_transaction = form.save()

                # 2. Enrich data
                enrichment_stats = enrich_transaction_list([new_transaction])

                # 3. Integrate with blockchain
                blockchain_success, blockchain_result = integrate_transaction_batch([new_transaction])

                # 4. Set final success status
                tracker.set_success(blockchain_success, blockchain_result.get('error_message'))
```

### 2. **Automatic Metric Storage**

The context manager automatically:

- ✅ Records start time when entering the context
- ✅ Records end time when exiting the context
- ✅ Calculates total execution time in milliseconds
- ✅ Stores the metric in the database
- ✅ Creates alerts if threshold is exceeded
- ✅ Handles exceptions gracefully

### 3. **Success/Failure Tracking**

The system tracks whether the entire workflow succeeded:

```python
# Set success status based on blockchain integration result
tracker.set_success(blockchain_success, blockchain_result.get('error_message'))
```

## API Endpoints

### Get End-to-End Performance Metrics

```bash
# Get all end-to-end metrics for the last 24 hours
GET /performance/api/performance/end-to-end/

# Get specific operation metrics
GET /performance/api/performance/end-to-end/?operation_type=single_transaction_upload

# Get metrics for different time ranges
GET /performance/api/performance/end-to-end/?hours=48
```

**Response Example:**

```json
{
  "status": "success",
  "hours": 24,
  "end_to_end_metrics": {
    "single_transaction_upload": {
      "average_time_ms": 8500.0,
      "total_operations": 25,
      "success_rate": 96.0,
      "min_time_ms": 3000.0,
      "max_time_ms": 15000.0
    },
    "csv_batch_upload": {
      "average_time_ms": 25000.0,
      "total_operations": 10,
      "success_rate": 90.0,
      "min_time_ms": 15000.0,
      "max_time_ms": 45000.0
    }
  }
}
```

## Management Commands

### View End-to-End Performance

```bash
# View all end-to-end metrics
python manage.py view_performance --operation-type single_transaction_upload

# View with alerts
python manage.py view_performance --show-alerts --severity high

# Export as JSON
python manage.py view_performance --format json
```

### Test Performance Monitoring

```bash
# Test with 10 single transaction uploads
python manage.py test_performance --operation-type single_transaction_upload --count 10

# Test CSV batch uploads
python manage.py test_performance --operation-type csv_batch_upload --count 5
```

## Admin Interface

Access end-to-end performance data through Django admin at `/admin/`:

- **Performance Metrics**: Filter by `single_transaction_upload` or `csv_batch_upload`
- **Performance Alerts**: View threshold violations for end-to-end operations
- **Real-time Monitoring**: See current performance trends

## Thresholds and Alerts

### Default Thresholds

| Operation                   | Threshold  | Description                          |
| --------------------------- | ---------- | ------------------------------------ |
| `single_transaction_upload` | 12 seconds | Complete single transaction workflow |
| `csv_batch_upload`          | 30 seconds | Complete batch upload workflow       |
| `end_to_end_upload`         | 15 seconds | Generic end-to-end workflow          |

### Alert Severity Levels

- **Low**: 1.5x threshold (e.g., 18s for single upload)
- **Medium**: 2.0x threshold (e.g., 24s for single upload)
- **High**: 3.0x threshold (e.g., 36s for single upload)
- **Critical**: >3.0x threshold (e.g., >36s for single upload)

## Production Monitoring

### Key Metrics to Watch

1. **Average Response Time**: Should stay under thresholds
2. **Success Rate**: Should be >95% for healthy system
3. **Alert Frequency**: Monitor for increasing alert rates
4. **Peak Times**: Identify when performance degrades

### Common Performance Issues

1. **Database Slowdowns**: Check for slow queries during transaction creation
2. **Enrichment Delays**: Monitor external API response times
3. **Blockchain Bottlenecks**: Check blockchain integration performance
4. **Network Issues**: Monitor external service connectivity

## Integration Points

### Current Integration

The end-to-end monitoring is integrated into:

1. **Single Transaction Upload** (`apps/transaction_management/views.py`)
   - Tracks complete workflow from form submission to blockchain
2. **CSV Batch Upload** (`apps/transaction_management/views.py`)
   - Tracks batch processing from file upload to blockchain
3. **API Upload** (`apps/transaction_management/views.py`)
   - Tracks API-based upload workflows

### Adding New Integration Points

To add end-to-end monitoring to new workflows:

```python
from apps.performance_monitoring.services import EndToEndPerformanceTracker

def your_workflow_function():
    with EndToEndPerformanceTracker('your_operation_type', transaction_count=1) as tracker:
        # Your complete workflow here
        result = do_something()
        tracker.set_success(result.success, result.error_message)
```

## Troubleshooting

### Metrics Not Being Recorded

1. **Check App Installation**: Ensure `performance_monitoring` is in `INSTALLED_APPS`
2. **Verify Migrations**: Run `python manage.py migrate`
3. **Check Context Manager**: Ensure proper `with` statement usage
4. **Review Logs**: Check for import or database errors

### High Performance Impact

1. **Async Storage**: Metrics are stored asynchronously to avoid blocking
2. **Error Handling**: Monitoring failures don't affect core operations
3. **Database Optimization**: Indexed fields for fast queries

### Missing Alerts

1. **Threshold Configuration**: Verify thresholds in `DEFAULT_THRESHOLDS`
2. **Alert Creation**: Check for database permission issues
3. **Log Review**: Look for alert creation errors in logs

## Best Practices

### 1. **Consistent Operation Types**

Use consistent operation type names across your application:

- `single_transaction_upload` for individual uploads
- `csv_batch_upload` for batch uploads
- `api_upload` for API-based uploads

### 2. **Proper Error Handling**

Always set the success status in your workflows:

```python
try:
    result = do_work()
    tracker.set_success(True)
except Exception as e:
    tracker.set_success(False, str(e))
```

### 3. **Transaction Count Accuracy**

Set the correct transaction count for accurate metrics:

```python
# For single transaction
with EndToEndPerformanceTracker('single_transaction_upload', transaction_count=1) as tracker:

# For batch upload
with EndToEndPerformanceTracker('csv_batch_upload', transaction_count=len(transactions)) as tracker:
```

### 4. **Regular Monitoring**

- Check performance metrics daily
- Review alerts weekly
- Monitor trends monthly
- Adjust thresholds based on actual performance

## Example Usage

### Complete Workflow Example

```python
def process_transaction_workflow(transaction_data):
    """Complete transaction processing workflow with performance monitoring."""

    with EndToEndPerformanceTracker('single_transaction_upload', transaction_count=1) as tracker:
        try:
            # Step 1: Create transaction
            transaction = create_transaction(transaction_data)

            # Step 2: Enrich with market data
            enrichment_result = enrich_transaction(transaction)

            # Step 3: Save to blockchain
            blockchain_result = save_to_blockchain(transaction)

            # Step 4: Verify success
            success = blockchain_result.get('success', False)
            error_message = blockchain_result.get('error_message')

            # Set final status
            tracker.set_success(success, error_message)

            return blockchain_result

        except Exception as e:
            # Handle any exceptions
            tracker.set_success(False, str(e))
            raise
```

This comprehensive end-to-end monitoring system ensures you can track the complete performance of your transaction upload workflows from submission to blockchain block creation, providing valuable insights for optimization and alerting.
