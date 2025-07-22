# Research Model Implementation Summary

## Overview

This implementation creates a new Django management command `research_model` that combines training and evaluation functionality with research mode, using separate datasets for training and evaluation. This makes researching Isolation Forest models easy and efficient.

## What Was Implemented

### 1. New Django Management Command: `research_model.py`

**Location**: `apps/ai_analytics/management/commands/research_model.py`

**Key Features**:

- **Combines training and evaluation** in a single command
- **Uses separate datasets** for training and evaluation
- **Tests multiple contamination values** automatically
- **Selects the best model** based on evaluation metrics
- **Generates comprehensive reports** of the research process

**Main Methods**:

- `_process_training_data()`: Processes training dataset
- `_process_evaluation_data()`: Processes evaluation dataset
- `_research_mode_training_and_evaluation()`: Core research logic
- `_evaluate_model_on_evaluation_data()`: Evaluates models on separate dataset
- `_calculate_evaluation_metrics()`: Calculates precision, recall, F1-score, etc.

### 2. Combined Configuration File: `research_model.yml`

**Location**: `data/data/research/config/research_model.yml`

**Key Sections**:

- **Data Source**: Separate paths for training and evaluation CSV files
- **Model Configuration**: Contamination range and Isolation Forest parameters
- **Training Configuration**: Research mode settings
- **Evaluation Configuration**: Output format and metrics
- **Output Configuration**: File paths for saving results
- **Advanced Configuration**: Data handling options

**Example Usage**:

```yaml
data_source:
  training_csv_path: path/to/train.csv
  evaluation_csv_path: path/to/eval.csv
  actual_contamination: 0.05

model:
  contamination_range: [0.01, 0.05, 0.10, 0.15, 0.20]
  n_estimators: 100
  random_state: 42
```

### 3. Comprehensive Documentation

**Files Created**:

- `README.md`: Complete usage guide and documentation
- `IMPLEMENTATION_SUMMARY.md`: This summary document
- `test_research_model.py`: Test script for the command

## How It Addresses Your Requirements

### ✅ Requirement: "Make researching on isolation forest easy"

**Solution**: The new command provides a streamlined workflow:

1. Configure data paths in YAML file
2. Run single command: `python manage.py research_model --config config.yml`
3. Get comprehensive results automatically

### ✅ Requirement: "Combining @train_model.py revamping research mode by copying how @evaluate_model.py does evaluation"

**Solution**:

- **From `train_model.py`**: Research mode logic, contamination range testing, best model selection
- **From `evaluate_model.py`**: Evaluation metrics calculation, comprehensive reporting, JSON output
- **Combined**: Single command that trains multiple models and evaluates them properly

### ✅ Requirement: "Must accept a range of values"

**Solution**:

```yaml
model:
  contamination_range: [0.01, 0.05, 0.10, 0.15, 0.20]
```

The command automatically tests each contamination value and reports results for all.

### ✅ Requirement: "Must output the result of evaluation"

**Solution**: Multiple output formats:

- **Console output**: Real-time progress and final summary
- **JSON file**: Comprehensive results with all metrics
- **Best model**: Automatically saved and ready to use

### ✅ Requirement: "Training to be done by a different dataset csv (e.g. train.csv), and then the research evaluation to be done using a different dataset csv (e.g. eval.csv)"

**Solution**:

```yaml
data_source:
  training_csv_path: path/to/train.csv
  evaluation_csv_path: path/to/eval.csv
```

### ✅ Requirement: "Create a new yml config file again combining @train_research.yml and @evaluate_research.yml"

**Solution**: The `research_model.yml` combines:

- **From `train_research.yml`**: Model parameters, contamination range, output paths
- **From `evaluate_research.yml`**: Evaluation settings, metrics, reporting options

## Key Improvements Over Original Commands

| Feature                  | Original Commands           | New `research_model`        |
| ------------------------ | --------------------------- | --------------------------- |
| **Workflow**             | Two separate commands       | Single command              |
| **Datasets**             | Same dataset for train/eval | Separate datasets           |
| **Research Mode**        | Limited in train_model      | Full research mode          |
| **Evaluation**           | Separate command needed     | Built-in evaluation         |
| **Best Model Selection** | Manual comparison           | Automatic selection         |
| **Reporting**            | Multiple files              | Single comprehensive report |

## Usage Example

```bash
# 1. Prepare your data
# - train.csv: Training dataset
# - eval.csv: Evaluation dataset with labels

# 2. Configure the YAML file
# - Update CSV paths
# - Set contamination range
# - Configure output paths

# 3. Run the research
python watchdog_ai/manage.py research_model --config data/data/research/config/research_model.yml

# 4. Review results
# - Console output shows progress and summary
# - JSON file contains detailed results
# - Best model is automatically saved
```

## Output Files Generated

1. **Best Model**: `research_isolation_forest.joblib`
2. **Training Columns**: `research_training_columns.joblib`
3. **Research Results**: `research_results.json`

## Research Results Structure

The JSON output contains:

- **Dataset information**: Training/evaluation sample counts, feature counts
- **Contamination analysis**: Results for each tested contamination value
- **Best model**: Performance metrics and file paths
- **Training summary**: Overall research summary

## Benefits

1. **Simplified Workflow**: One command instead of multiple
2. **Proper Evaluation**: Uses separate datasets for training and evaluation
3. **Comprehensive Results**: All metrics and detailed analysis
4. **Best Model Selection**: Automatically finds optimal contamination
5. **Reproducible Research**: All settings and results saved
6. **Easy Configuration**: Single YAML file for all settings

## Next Steps

1. **Test the command** with your actual data
2. **Adjust configuration** based on your specific needs
3. **Review results** and iterate on contamination ranges
4. **Use the best model** for production anomaly detection

The implementation successfully addresses all your requirements and provides a robust, easy-to-use solution for researching Isolation Forest models.
