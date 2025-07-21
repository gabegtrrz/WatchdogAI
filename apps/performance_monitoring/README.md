# Performance Monitoring System

A comprehensive performance monitoring system for tracking execution times of critical operations in the WatchdogAI application.

## Features

### 🔍 **Automatic Performance Tracking**

- **Blockchain Save Operations**: Tracks time to save transactions to blockchain
- **Anomaly Detection Analysis**: Monitors AI model analysis execution times
- **Transaction Upload**: Measures file upload and processing times
- **Data Preprocessing**: Tracks data cleaning and preparation times
- **Feature Engineering**: Monitors feature generation performance
- **Model Prediction**: Tracks ML model inference times

### 📊 **Performance Metrics**

- **Average Execution Times**: Calculated over configurable time periods
- **Min/Max Times**: Track performance boundaries
- **Success Rates**: Monitor operation reliability
- **Transaction Counts**: Track batch processing efficiency
- **Error Tracking**: Capture and analyze failure patterns

### 🚨 **Performance Alerts**

- **Threshold Violations**: Automatic alerts when operations exceed limits
- **Severity Levels**: Low, Medium, High, Critical based on threshold ratios
- **Alert Management**: Track and resolve performance issues
- **Real-time Monitoring**: Immediate notification of performance degradation

### 🛠 **Easy Integration**

- **Decorator-based**: Simple `@monitor_operation` decorators
- **Non-blocking**: Async metric storage to avoid performance impact
- **Context-aware**: Track user sessions and transaction counts
- **Production-safe**: Graceful error handling and fallbacks

## Quick Start

### 1. Monitor an Operation

```python
from apps.performance_monitoring.services import monitor_blockchain_save

@monitor_blockchain_save
def save_transaction_to_blockchain(transaction):
    # Your blockchain save logic here
    pass
```

### 2. Get Performance Data

```python
from apps.performance_monitoring.services import performance_monitor

# Get average time for blockchain saves
avg_time = performance_monitor.get_average_time('blockchain_save', hours=24)

# Get comprehensive performance summary
summary = performance_monitor.get_performance_summary(hours=24)

# Get recent alerts
alerts = performance_monitor.get_recent_alerts(hours=24, severity='high')
```

### 3. API Endpoints

```bash
# Get performance summary
GET /performance/api/performance/summary/?hours=24

# Get metrics for specific operation
GET /performance/api/performance/operation/blockchain_save/?hours=24

# Get performance alerts
GET /performance/api/performance/alerts/?severity=high

# Get dashboard data
GET /performance/api/performance/dashboard/?hours=24
```

## Management Commands

### View Performance Metrics

```bash
# View all operations summary
python manage.py view_performance

# View specific operation
python manage.py view_performance --operation-type blockchain_save

# View with alerts
python manage.py view_performance --show-alerts

# Export as JSON
python manage.py view_performance --format json

# Filter by time range
python manage.py view_performance --hours 48
```

## Configuration

### Default Thresholds

| Operation             | Threshold | Description                  |
| --------------------- | --------- | ---------------------------- |
| `blockchain_save`     | 5000ms    | Blockchain transaction saves |
| `anomaly_detection`   | 30000ms   | AI model analysis            |
| `transaction_upload`  | 10000ms   | File upload and processing   |
| `data_preprocessing`  | 5000ms    | Data cleaning operations     |
| `feature_engineering` | 8000ms    | Feature generation           |
| `model_prediction`    | 15000ms   | ML model inference           |

### Custom Thresholds

```python
from apps.performance_monitoring.services import monitor_operation

@monitor_operation('blockchain_save', threshold_ms=3000)
def fast_blockchain_save(transaction):
    # Optimized blockchain save
    pass
```

## Database Models

### PerformanceMetric

Stores individual performance measurements:

```python
{
    'operation_type': 'blockchain_save',
    'execution_time_ms': 1250.5,
    'transaction_count': 5,
    'success': True,
    'created_at': '2024-01-15T10:30:00Z',
    'user_id': 'user123',
    'session_id': 'session456'
}
```

### PerformanceAlert

Tracks threshold violations:

```python
{
    'operation_type': 'blockchain_save',
    'threshold_ms': 5000.0,
    'actual_time_ms': 12000.0,
    'severity': 'high',
    'message': 'Operation exceeded threshold by 2.4x',
    'created_at': '2024-01-15T10:30:00Z',
    'resolved': False
}
```

## API Reference

### GET /performance/api/performance/summary/

Returns performance summary for all operations.

**Query Parameters:**

- `hours` (int): Time range in hours (default: 24, max: 720)

**Response:**

```json
{
  "status": "success",
  "hours": 24,
  "summary": {
    "blockchain_save": {
      "average_time_ms": 1250.5,
      "min_time_ms": 800.0,
      "max_time_ms": 3000.0,
      "total_operations": 150,
      "successful_operations": 148,
      "success_rate": 98.7
    }
  }
}
```

### GET /performance/api/performance/operation/{operation_type}/

Returns metrics for a specific operation type.

**Path Parameters:**

- `operation_type` (str): Type of operation to query

**Query Parameters:**

- `hours` (int): Time range in hours (default: 24)

**Response:**

```json
{
  "status": "success",
  "operation_type": "blockchain_save",
  "average_time_ms": 1250.5,
  "hours": 24,
  "recent_metrics": [
    {
      "execution_time_ms": 1200.0,
      "transaction_count": 5,
      "success": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### GET /performance/api/performance/alerts/

Returns performance alerts.

**Query Parameters:**

- `hours` (int): Time range in hours (default: 24)
- `severity` (str): Filter by severity (low, medium, high, critical)
- `resolved` (bool): Filter by resolution status

**Response:**

```json
{
  "status": "success",
  "hours": 24,
  "alerts": [
    {
      "operation_type": "blockchain_save",
      "severity": "high",
      "threshold_ms": 5000.0,
      "actual_time_ms": 12000.0,
      "message": "Operation exceeded threshold by 2.4x",
      "created_at": "2024-01-15T10:30:00Z",
      "resolved": false
    }
  ]
}
```

## Admin Interface

Access performance data through Django admin at `/admin/`:

- **Performance Metrics**: View all performance measurements with filtering and search
- **Performance Alerts**: Manage alerts with bulk resolution actions
- **Performance Summary**: See real-time performance statistics

## Production Considerations

### Performance Impact

- **Non-blocking**: Metrics are stored asynchronously using Django's `transaction.on_commit`
- **Graceful degradation**: Monitoring failures don't affect core operations
- **Efficient queries**: Indexed database fields for fast retrieval

### Data Management

- **Automatic cleanup**: Consider periodic cleanup of old metrics
- **Database optimization**: Monitor table sizes and query performance
- **Backup strategy**: Include performance data in backup schedules

### Monitoring Integration

- **Log aggregation**: Performance logs integrate with existing logging
- **Alert integration**: Connect to existing monitoring systems
- **Dashboard integration**: Embed performance widgets in existing dashboards

## Troubleshooting

### Common Issues

1. **Metrics not being recorded**

   - Check that the app is in `INSTALLED_APPS`
   - Verify database migrations are applied
   - Check for import errors in the monitoring service

2. **High performance impact**

   - Ensure async storage is working
   - Check for database connection issues
   - Monitor for excessive alert creation

3. **Missing alerts**
   - Verify threshold configurations
   - Check alert creation permissions
   - Review error logs for alert creation failures

### Debug Commands

```bash
# Test performance monitoring
python manage.py shell
>>> from apps.performance_monitoring.services import performance_monitor
>>> performance_monitor.get_performance_summary(24)

# Check for recent alerts
python manage.py view_performance --show-alerts --severity critical

# Export performance data
python manage.py view_performance --format csv > performance_report.csv
```

## Contributing

When adding new monitored operations:

1. **Add operation type** to `PerformanceMetric.OPERATION_CHOICES`
2. **Set default threshold** in `PerformanceMonitor.DEFAULT_THRESHOLDS`
3. **Create decorator** in `services.py` if needed
4. **Add tests** in `tests.py`
5. **Update documentation** in this README

## License

This performance monitoring system is part of the WatchdogAI project and follows the same licensing terms.
