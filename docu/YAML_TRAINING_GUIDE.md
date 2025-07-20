# YAML-Based Model Training Guide

## Overview

The WatchdogAI system now supports YAML-based configuration for model training, providing comprehensive research tracking and experiment management capabilities. This system is designed for research environments where you need to track inputs, outputs, and experiment parameters systematically.

## Key Features

- **Research Tracking**: Complete experiment metadata and results logging
- **Flexible Configuration**: All training parameters configurable via YAML
- **Multiple Data Sources**: Support for database, CSV, and labeled CSV data
- **Hyperparameter Optimization**: Built-in grid search and cross-validation
- **Comprehensive Evaluation**: Multiple metrics and detailed reporting
- **Experiment Management**: Easy creation and organization of experiments

## Quick Start

### 1. Create a New Experiment

```bash
# Create a new experiment configuration
python manage.py create_experiment \
    --name "Feature Engineering Study" \
    --description "Testing different feature engineering approaches" \
    --researcher "Dr. Smith" \
    --research-mode \
    --data-source labeled_csv \
    --labeled-data-path "data/training_data/1/transactions_with_labels.csv"
```

### 2. Run the Experiment

```bash
# Train the model using the configuration
python manage.py train_model --config data/config/experiment_feature_engineering_study.yml
```

### 3. View Results

The system automatically saves:

- Trained model files
- Research logs with detailed results
- Configuration snapshots
- Performance metrics

## Configuration Structure

### Experiment Metadata

```yaml
experiment:
  name: "Your Experiment Name"
  description: "Detailed description of the experiment"
  researcher: "Your Name"
  date: "2024-01-15"
  version: "1.0"
  tags:
    - "baseline"
    - "feature_engineering"
  references:
    - "Previous experiment: baseline_v1"
```

### Data Configuration

```yaml
data:
  source:
    type: "labeled_csv" # Options: database, csv, labeled_csv
    labeled_data_path: "data/training_data/1/transactions_with_labels.csv"

  preprocessing:
    feature_engineering:
      include_temporal_features: true
      include_price_features: true
      include_supplier_features: true
      include_procurement_features: true

    cleaning:
      remove_duplicates: true
      handle_missing_values: "drop" # Options: drop, impute, ignore
      outlier_removal: false

    scaling:
      method: "standard" # Options: standard, minmax, robust, none
      apply_to_features: true
```

### Model Configuration

```yaml
model:
  algorithm: "IsolationForest"

  isolation_forest:
    contamination: "auto" # Will be optimized in research mode
    n_estimators: 100
    max_samples: "auto"
    bootstrap: false
    n_jobs: -1
    random_state: 42
    verbose: 0
    warm_start: false
```

### Training Configuration

```yaml
training:
  research_mode: true # Enable for hyperparameter optimization

  cross_validation:
    enabled: true
    cv_folds: 5
    cv_method: "StratifiedKFold" # Options: KFold, StratifiedKFold, TimeSeriesSplit
    random_state: 42

  hyperparameter_optimization:
    enabled: true
    method: "grid_search" # Options: grid_search, random_search, bayesian

    grid_search:
      contamination_range: [0.01, 0.05, 0.10, 0.15, 0.20]
      n_estimators_range: [50, 100, 200]
      max_samples_range: ["auto", 0.5, 0.7]

  evaluation:
    primary_metric: "f1_score" # Options: f1_score, precision, recall, roc_auc
    metrics_to_track:
      - "precision"
      - "recall"
      - "f1_score"
      - "roc_auc_score"
      - "confusion_matrix"

  model_selection:
    criterion: "f1_score"
    direction: "maximize" # Options: maximize, minimize
```

### Output Configuration

```yaml
output:
  model_files:
    model_path: "apps/ai_analytics/model_files/isolation_forest.joblib"
    columns_path: "apps/ai_analytics/model_files/training_columns.joblib"
    research_log_path: "apps/ai_analytics/model_files/research_log.json"

  experiment_tracking:
    save_detailed_results: true
    save_model_artifacts: true
    save_feature_importance: true
    save_confusion_matrix: true

  reporting:
    generate_summary_report: true
    save_plots: true
    plot_types:
      - "confusion_matrix"
      - "roc_curve"
      - "precision_recall_curve"
      - "feature_importance"

  logging:
    level: "INFO" # Options: DEBUG, INFO, WARNING, ERROR
    save_logs: true
    log_file: "logs/model_training.log"
```

## Research Mode vs Standard Mode

### Research Mode

- Enables hyperparameter optimization
- Performs cross-validation
- Saves detailed research logs
- Tracks multiple evaluation metrics
- Best for experimentation and research

### Standard Mode

- Single model training
- No hyperparameter optimization
- Faster execution
- Suitable for production deployment

## Data Sources

### Database Source

```yaml
data:
  source:
    type: "database"
```

### CSV Source

```yaml
data:
  source:
    type: "csv"
    csv_path: "path/to/your/data.csv"
```

### Labeled CSV Source (Recommended for Research)

```yaml
data:
  source:
    type: "labeled_csv"
    labeled_data_path: "data/training_data/1/transactions_with_labels.csv"
```

## Hyperparameter Optimization

### Grid Search

```yaml
training:
  hyperparameter_optimization:
    method: "grid_search"
    grid_search:
      contamination_range: [0.01, 0.05, 0.10, 0.15, 0.20]
      n_estimators_range: [50, 100, 200]
      max_samples_range: ["auto", 0.5, 0.7]
```

### Random Search

```yaml
training:
  hyperparameter_optimization:
    method: "random_search"
    random_search:
      n_iterations: 20
      contamination_range: [0.01, 0.25]
      n_estimators_range: [50, 300]
      max_samples_range: ["auto", 0.3, 0.9]
```

## Evaluation Metrics

The system tracks multiple metrics:

- **Precision**: True positives / (True positives + False positives)
- **Recall**: True positives / (True positives + False negatives)
- **F1-Score**: Harmonic mean of precision and recall
- **ROC AUC**: Area under the ROC curve
- **Confusion Matrix**: Detailed classification results

## Output Files

### Model Files

- `isolation_forest.joblib`: Trained model
- `training_columns.joblib`: Feature column names
- `research_log.json`: Detailed experiment results

### Research Log Structure

```json
{
  "training_date": "2024-01-15T10:30:00",
  "experiment_info": {
    "name": "Your Experiment",
    "researcher": "Your Name",
    "version": "1.0"
  },
  "dataset_info": {
    "sample_count": 5000,
    "feature_count": 25,
    "true_anomalies": 150,
    "true_normal": 4850
  },
  "contamination_analysis": {
    "0.01": {
      "precision": 0.85,
      "recall": 0.7,
      "f1_score": 0.77,
      "predicted_anomalies": 120
    }
  },
  "best_model": {
    "contamination": 0.05,
    "f1_score": 0.82,
    "precision": 0.88,
    "recall": 0.76
  }
}
```

## Best Practices

### 1. Experiment Naming

- Use descriptive, unique names
- Include version numbers for iterations
- Add tags for easy organization

### 2. Configuration Management

- Keep configurations in version control
- Document changes between experiments
- Use templates for consistency

### 3. Data Management

- Use labeled data for research mode
- Document data preprocessing steps
- Track data versions

### 4. Result Analysis

- Review multiple metrics, not just F1-score
- Consider precision/recall trade-offs
- Document insights and next steps

## Example Workflows

### Baseline Experiment

```bash
# Create baseline experiment
python manage.py create_experiment \
    --name "Baseline Training" \
    --description "Initial baseline with default parameters" \
    --researcher "Research Team" \
    --research-mode

# Run experiment
python manage.py train_model --config data/config/experiment_baseline_training.yml
```

### Feature Engineering Study

```bash
# Create feature engineering experiment
python manage.py create_experiment \
    --name "Feature Engineering Study" \
    --description "Testing different feature combinations" \
    --researcher "Dr. Smith" \
    --research-mode \
    --data-source labeled_csv

# Edit the configuration file to modify feature engineering settings
# Then run the experiment
python manage.py train_model --config data/config/experiment_feature_engineering_study.yml
```

### Hyperparameter Tuning

```bash
# Create hyperparameter tuning experiment
python manage.py create_experiment \
    --name "Hyperparameter Tuning" \
    --description "Optimizing contamination and n_estimators" \
    --researcher "ML Engineer" \
    --research-mode \
    --contamination-range 0.01 0.03 0.05 0.07 0.10 0.15

# Run the experiment
python manage.py train_model --config data/config/experiment_hyperparameter_tuning.yml
```

## Troubleshooting

### Common Issues

1. **Configuration File Not Found**

   - Ensure the path is correct
   - Check file permissions
   - Verify YAML syntax

2. **Data Source Errors**

   - Verify data file paths
   - Check data format
   - Ensure labeled data has 'is_anomaly' column

3. **Memory Issues**

   - Reduce dataset size
   - Use fewer hyperparameter combinations
   - Enable memory-efficient settings

4. **Poor Performance**
   - Check data quality
   - Review feature engineering
   - Adjust contamination range
   - Consider different algorithms

### Debug Mode

```yaml
advanced:
  debugging:
    verbose_output: true
    save_intermediate_results: true
    profile_performance: true
```

## Migration from Legacy Commands

### Old Command

```bash
python manage.py train_model --research-mode --contamination-range 0.01 0.05 0.10
```

### New Command

```bash
python manage.py train_model --config data/config/experiment_baseline.yml
```

The legacy command-line arguments are still supported but deprecated. The YAML configuration provides more flexibility and better research tracking.

## Advanced Features

### Custom Evaluation Metrics

```yaml
advanced:
  custom_evaluation:
    enabled: true
    custom_metrics:
      - "custom_metric_1"
      - "custom_metric_2"
    custom_thresholds:
      custom_metric_1: 0.8
      custom_metric_2: 0.6
```

### Parallel Processing

```yaml
advanced:
  parallel:
    n_jobs: -1 # Use all available cores
    backend: "threading" # Options: threading, multiprocessing
```

### Memory Management

```yaml
advanced:
  memory:
    cache_size: 200
    memory_efficient: false
```

## Conclusion

The YAML-based training system provides a comprehensive solution for research-driven model development. It enables systematic experiment tracking, flexible configuration management, and detailed result analysis, making it ideal for research environments where reproducibility and documentation are crucial.

For additional support or feature requests, please refer to the project documentation or create an issue in the repository.
