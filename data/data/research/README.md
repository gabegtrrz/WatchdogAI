# Research Model Command

This directory contains the configuration and documentation for the new `research_model` Django management command, which combines training and evaluation functionality with research mode using separate datasets.

## Overview

The `research_model` command is designed to make researching Isolation Forest models easy by:

1. **Training models** on a training dataset with different contamination values
2. **Evaluating models** on a separate evaluation dataset
3. **Comparing results** across different contamination values
4. **Saving the best model** based on evaluation metrics
5. **Generating comprehensive reports** of the research process

## Key Features

- **Separate datasets**: Uses different CSV files for training and evaluation
- **Research mode**: Tests multiple contamination values automatically
- **Comprehensive evaluation**: Calculates precision, recall, F1-score, and other metrics
- **Best model selection**: Automatically selects the best model based on F1-score
- **Detailed logging**: Saves all research results to JSON files
- **Console output**: Provides real-time progress updates

## Usage

### Basic Usage

```bash
python watchdog_ai/manage.py research_model --config data/data/research/config/research_model.yml
```

### Configuration File Structure

The configuration file (`research_model.yml`) contains several sections:

#### Data Source Configuration
```yaml
data_source:
  training_csv_path: path/to/training_data.csv
  evaluation_csv_path: path/to/evaluation_data.csv
  actual_contamination: 0.05  # Optional
```

#### Model Configuration
```yaml
model:
  contamination_range: [0.01, 0.05, 0.10, 0.15, 0.20]  # Values to test
  n_estimators: 100
  random_state: 42
  max_samples: 700
  bootstrap: false
```

#### Output Configuration
```yaml
output:
  model_dir: path/to/save/models
  model_filename: 'research_isolation_forest.joblib'
  columns_filename: 'research_training_columns.joblib'
  research_log_filename: 'research_results.json'
```

## Configuration Options

### Data Source
- `training_csv_path`: Path to CSV file for training (required)
- `evaluation_csv_path`: Path to CSV file for evaluation (required)
- `actual_contamination`: Known contamination rate in data (optional)

### Model Parameters
- `contamination_range`: List of contamination values to test
- `n_estimators`: Number of trees in Isolation Forest
- `random_state`: Random seed for reproducibility
- `max_samples`: Number of samples per tree
- `bootstrap`: Whether to use bootstrap sampling
- `n_jobs`: Number of parallel jobs (null = use all)
- `verbose`: Verbosity level
- `warm_start`: Whether to reuse previous solution
- `max_features`: Number of features to consider per split

### Evaluation Settings
- `output_format`: "json", "console", or "both"
- `metrics`: List of metrics to calculate
- `reporting`: What information to include in results

### Advanced Settings
- `handle_missing_columns`: Whether to add missing columns with defaults
- `missing_column_default`: Default value for missing columns
- `remove_extra_columns`: Whether to remove extra columns not in training
- `validate_data`: Whether to validate data before processing

## Output Files

The command generates several output files:

1. **Trained Model**: `research_isolation_forest.joblib` - The best trained model
2. **Training Columns**: `research_training_columns.joblib` - Column names used in training
3. **Research Results**: `research_results.json` - Comprehensive research results

## Research Results Structure

The research results JSON file contains:

```json
{
  "research_date": "2025-01-XX...",
  "configuration": { /* Full config used */ },
  "dataset_info": {
    "training_sample_count": 1000,
    "training_feature_count": 15,
    "evaluation_sample_count": 500,
    "evaluation_feature_count": 15,
    "true_anomalies": 25,
    "true_normal": 475,
    "actual_contamination": 0.05
  },
  "contamination_analysis": {
    "0.01": { /* Results for contamination=0.01 */ },
    "0.05": { /* Results for contamination=0.05 */ },
    /* ... more contamination values */
  },
  "best_model": {
    "contamination": 0.05,
    "f1_score": 0.8500,
    "precision": 0.8000,
    "recall": 0.9000,
    "predicted_anomalies": 30,
    "model_path": "path/to/model.joblib"
  },
  "training_summary": {
    "total_contamination_values_tested": 5,
    "contamination_values_tested": [0.01, 0.05, 0.10, 0.15, 0.20],
    "best_contamination": 0.05,
    "best_f1_score": 0.8500,
    "training_completed_at": "2025-01-XX...",
    "model_saved_to": "path/to/model.joblib"
  }
}
```

## Example Workflow

1. **Prepare Data**: Split your labeled data into training and evaluation sets
2. **Configure**: Update the YAML config file with your data paths
3. **Run Research**: Execute the command
4. **Analyze Results**: Review the console output and JSON results
5. **Use Best Model**: The best model is automatically saved and ready to use

## Comparison with Other Commands

| Feature | `train_model` | `evaluate_model` | `research_model` |
|---------|---------------|------------------|------------------|
| Training | ✅ | ❌ | ✅ |
| Evaluation | ❌ | ✅ | ✅ |
| Research Mode | ✅ | ❌ | ✅ |
| Separate Datasets | ❌ | ❌ | ✅ |
| Multiple Contamination Values | ✅ | ❌ | ✅ |
| Best Model Selection | ✅ | ❌ | ✅ |
| Comprehensive Reporting | ✅ | ✅ | ✅ |

## Tips for Research

1. **Start with a wide range**: Test contamination values from 0.01 to 0.20
2. **Use separate datasets**: Always use different data for training and evaluation
3. **Monitor console output**: Real-time progress helps identify issues
4. **Check results file**: The JSON file contains detailed analysis
5. **Validate data**: Ensure your CSV files have the required columns

## Troubleshooting

### Common Issues

1. **File not found**: Check that CSV paths are correct and files exist
2. **Column mismatch**: Ensure training and evaluation data have similar columns
3. **No anomalies predicted**: Try higher contamination values
4. **Memory issues**: Reduce `max_samples` or `n_estimators`

### Debug Mode

Enable debug logging by setting:
```yaml
logging:
  level: "DEBUG"
```

This will provide detailed information about the data processing and model training steps. 