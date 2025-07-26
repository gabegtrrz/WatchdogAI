# Thesis Feature Set Comparison Experiments

This directory contains the controlled experiments for comparing different feature sets in anomaly detection for procurement fraud detection.

## Overview

The experiments compare ten different feature sets:

1. **Baseline**: Raw numerical features only

   - `quantity`, `unit_purchase_price`, `total_purchase_price`, `approved_budget`

2. **Financial Only**: Baseline + Financial engineered features

   - `budget_utilization_ratio`, `price_vs_market_average`, `price_competitiveness_score`, `total_transaction_value`

3. **Temporal Only**: Baseline + Temporal engineered features

   - `bidding_period_number_of_days`, `award_decision_duration`, `contract_signing_number_of_days`, `total_procurement_duration`, `transaction_month`

4. **Supplier Only**: Baseline + Supplier engineered features

   - `supplier_frequency`, `price_per_supplier_freq`, `price_vs_supplier_average`

5. **Efficiency Only**: Baseline + Efficiency engineered features

   - `price_per_unit_efficiency`, `quantity_per_peso_ratio`, `budget_efficiency_score`, `procurement_timeline_speed_ratio`, `transaction_on_a_weekend`

6. **Financial + Temporal**: Baseline + Financial + Temporal features

7. **Financial + Supplier**: Baseline + Financial + Supplier features

8. **Temporal + Supplier**: Baseline + Temporal + Supplier features

9. **Financial + Temporal + Supplier**: Baseline + Financial + Temporal + Supplier features

10. **Final (All Engineered)**: All engineered features combined
    - Uses the complete feature engineering pipeline from `feature_engineering.py`

## Experimental Design

### Controlled Variables

- **Same training/testing data splits** for all experiments
- **Same model hyperparameters** (Isolation Forest parameters)
- **Same evaluation metrics** (Precision, Recall, F1-Score)
- **Same contamination range** testing (0.01, 0.05, 0.10, 0.15, 0.20)

### Independent Variable

- **Feature set composition** (the only major variable that changes)

### Data

- **Training data**: `data/training/training_data/21_0.05/labeled/training.csv`
- **Evaluation data**: `data/training/training_data/21_0.05/labeled/training.csv`
- **Actual contamination**: 5% (0.05)

## Configuration Structure

The `thesis_config.yml` file defines:

- **Baseline features**: Raw features that are always included
- **Feature sets**: Each set explicitly lists its engineered features
- **Model parameters**: Isolation Forest hyperparameters
- **Experiment settings**: Contamination range, metrics, output options

### Example Feature Set Definition

```yaml
financial_temporal:
  description: "Baseline + Financial + Temporal features"
  features:
    - "budget_utilization_ratio"
    - "price_vs_market_average"
    - "price_competitiveness_score"
    - "total_transaction_value"
    - "bidding_period_number_of_days"
    - "award_decision_duration"
    - "contract_signing_number_of_days"
    - "total_procurement_duration"
    - "transaction_month"
  enabled: true
```

## Running the Experiments

### Prerequisites

1. Ensure Django environment is set up
2. Ensure all required packages are installed
3. Verify data files exist in the specified paths

### Command

```bash
python manage.py thesis_feature_comparison --config "1 Thesis/features/research_model/thesis_config.yml"
```

### Expected Output

The command will:

1. Load and process the training/evaluation data
2. Run experiments for each feature set
3. Test different contamination values for each feature set
4. Calculate precision, recall, and F1-score for each combination
5. Save detailed results to JSON files
6. Display a summary comparison table

## Results Structure

Results are saved in `1 Thesis/features/research_model/results/` with the following structure:

```json
{
  "experiment_date": "2025-01-XX...",
  "configuration": {...},
  "dataset_info": {
    "training_sample_count": 800,
    "evaluation_sample_count": 102,
    "true_anomalies": 5,
    "true_normal": 97,
    "actual_contamination": 0.05
  },
  "feature_set_results": {
    "baseline": {
      "feature_columns": [...],
      "feature_count": 4,
      "contamination_results": {
        "0.01": {"f1_score": 0.0, "precision": 0.0, "recall": 0.0, ...},
        "0.05": {"f1_score": 0.4, "precision": 0.5, "recall": 0.3, ...},
        ...
      },
      "best_contamination": 0.05,
      "best_f1_score": 0.4,
      "best_metrics": {...}
    },
    "financial_only": {...},
    "temporal_only": {...},
    "final_all_engineered": {...}
  },
  "best_overall_model": {
    "feature_set": "final_all_engineered",
    "f1_score": 0.75,
    "contamination": 0.05
  }
}
```

## Analysis

### Key Metrics to Compare

1. **F1-Score**: Primary metric for imbalanced anomaly detection
2. **Precision**: Accuracy of positive predictions
3. **Recall**: Ability to find all anomalies
4. **Feature Count**: Number of features in each set

### Expected Outcomes

- **Hypothesis**: Final set (All Engineered) should achieve the highest F1-score
- **Baseline**: Baseline set establishes the performance benchmark
- **Incremental Improvement**: Individual feature sets show the contribution of specific feature types

## Files

- `thesis_config.yml`: Configuration file for experiments
- `README.md`: This documentation file
- `results/`: Directory containing experiment results
- `models/`: Directory for saved models (if enabled)

## Troubleshooting

### Common Issues

1. **File not found errors**: Check data file paths in config
2. **Import errors**: Ensure Django environment is activated
3. **Memory errors**: Reduce `max_samples` in model config
4. **Column mismatch**: Verify data structure matches expected format

### Debug Mode

To run with more verbose output, modify the logging level in `thesis_config.yml`:

```yaml
logging:
  level: "DEBUG"
```

## Next Steps

After running experiments:

1. Analyze the JSON results
2. Create visualizations comparing feature sets
3. Document findings in thesis
4. Consider additional feature engineering if needed
5. Validate results with different datasets
