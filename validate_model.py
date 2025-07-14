"""
Validation Script for Isolation Forest Model
Tests the model's ability to detect known anomalies from anomaly_definitions.py
"""
import pandas as pd
import numpy as np
import joblib
import sys
import os
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from watchdog_ai.apps.ai_analytics.services import preprocessing, feature_engineering
from watchdog_ai.apps.data_generation.anomaly_definitions import ANOMALY_BLUEPRINTS

def load_model():
    """Load the trained Isolation Forest model and feature columns."""
    model_path = 'watchdog_ai/apps/ai_analytics/model_files/isolation_forest.joblib'
    columns_path = 'watchdog_ai/apps/ai_analytics/model_files/training_columns.joblib'
    
    if not os.path.exists(model_path):
        print("❌ Model not found. Please train the model first using:")
        print("   python manage.py train_model")
        return None, None
    
    model = joblib.load(model_path)
    columns = joblib.load(columns_path)
    return model, columns

def load_normal_data():
    """Load normal transaction data for testing."""
    csv_path = 'data/normal_data_scraped/2025-07-13_23-31-05/transactions.csv'
    
    if not os.path.exists(csv_path):
        print(f"❌ Data file not found: {csv_path}")
        return None
    
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df)} normal transactions")
    return df

def inject_anomalies(df, anomaly_types=None):
    """
    Inject known anomalies into normal data for testing.
    
    Args:
        df: Normal transaction DataFrame
        anomaly_types: List of anomaly class names to test. If None, tests all.
    
    Returns:
        DataFrame with injected anomalies and labels
    """
    if anomaly_types is None:
        anomaly_types = [blueprint.name for blueprint in ANOMALY_BLUEPRINTS]
    
    # Create a copy for testing
    test_df = df.copy()
    test_df['is_anomaly'] = 0  # Label normal transactions as 0
    
    injected_anomalies = []
    
    for blueprint in ANOMALY_BLUEPRINTS:
        if blueprint.name in anomaly_types:
            print(f"🔍 Testing anomaly type: {blueprint.name}")
            
            # Select a random normal transaction to inject anomaly
            sample_idx = np.random.choice(len(test_df), size=min(3, len(test_df)), replace=False)
            
            for idx in sample_idx:
                # Create a copy of the normal transaction
                anomaly_record = test_df.iloc[idx].copy()
                
                # Apply the anomaly transformation
                anomaly_record = blueprint.apply(anomaly_record)
                
                # Mark as anomaly
                anomaly_record['is_anomaly'] = 1
                
                # Add to injected anomalies
                injected_anomalies.append(anomaly_record)
    
    # Combine normal and anomalous data
    final_df = pd.concat([test_df, pd.DataFrame(injected_anomalies)], ignore_index=True)
    
    print(f"✅ Injected {len(injected_anomalies)} anomalies")
    print(f"📊 Final dataset: {len(final_df)} total transactions")
    print(f"   - Normal: {len(test_df)}")
    print(f"   - Anomalies: {len(injected_anomalies)}")
    
    return final_df

def evaluate_model_performance(model, columns, test_df):
    """
    Evaluate model performance on test data with known labels.
    
    Args:
        model: Trained Isolation Forest model
        columns: Feature column names
        test_df: Test DataFrame with 'is_anomaly' labels
    
    Returns:
        Dictionary with performance metrics
    """
    # Prepare features
    cleaned_df = preprocessing.clean_raw_data(test_df)
    processed_df, feature_cols = feature_engineering.create_model_features(cleaned_df)
    
    # Ensure all required columns exist
    missing_cols = set(columns) - set(processed_df.columns)
    if missing_cols:
        print(f"⚠️  Missing columns: {missing_cols}")
        # Add missing columns with zeros
        for col in missing_cols:
            processed_df[col] = 0
    
    # Get predictions and scores
    X = processed_df[columns]
    predictions = model.predict(X)
    scores = model.decision_function(X)
    
    # Calculate metrics
    true_labels = test_df['is_anomaly'].values
    predicted_anomalies = (predictions == -1).astype(int)
    
    # Basic metrics
    total_anomalies = true_labels.sum()
    detected_anomalies = ((true_labels == 1) & (predicted_anomalies == 1)).sum()
    false_positives = ((true_labels == 0) & (predicted_anomalies == 1)).sum()
    false_negatives = ((true_labels == 1) & (predicted_anomalies == 0)).sum()
    
    # Calculate rates
    detection_rate = detected_anomalies / total_anomalies if total_anomalies > 0 else 0
    false_positive_rate = false_positives / (len(true_labels) - total_anomalies) if (len(true_labels) - total_anomalies) > 0 else 0
    precision = detected_anomalies / (detected_anomalies + false_positives) if (detected_anomalies + false_positives) > 0 else 0
    recall = detection_rate
    
    # Calculate F1-score
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    # Score analysis for separation
    normal_scores = scores[true_labels == 0]
    anomaly_scores = scores[true_labels == 1]
    
    # Calculate score separation
    score_separation = abs(anomaly_scores.mean() - normal_scores.mean()) if len(anomaly_scores) > 0 and len(normal_scores) > 0 else 0
    
    # Additional score statistics
    normal_score_std = normal_scores.std() if len(normal_scores) > 0 else 0
    anomaly_score_std = anomaly_scores.std() if len(anomaly_scores) > 0 else 0
    
    results = {
        'detection_rate': detection_rate,
        'false_positive_rate': false_positive_rate,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'total_anomalies': total_anomalies,
        'detected_anomalies': detected_anomalies,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'normal_score_mean': normal_scores.mean() if len(normal_scores) > 0 else 0,
        'anomaly_score_mean': anomaly_scores.mean() if len(anomaly_scores) > 0 else 0,
        'normal_score_std': normal_score_std,
        'anomaly_score_std': anomaly_score_std,
        'score_separation': score_separation
    }
    
    return results

def print_results(results):
    """Print formatted validation results."""
    print("\n" + "="*60)
    print("📊 MODEL VALIDATION RESULTS")
    print("="*60)
    
    # Classification metrics
    print(f"🎯 Detection Rate: {results['detection_rate']:.3f} ({results['detected_anomalies']}/{results['total_anomalies']})")
    print(f"❌ False Positive Rate: {results['false_positive_rate']:.3f} ({results['false_positives']} false alarms)")
    print(f"📈 Precision: {results['precision']:.3f}")
    print(f"🔄 Recall: {results['recall']:.3f}")
    print(f"🎯 F1-Score: {results['f1_score']:.3f}")
    
    # Score separation analysis
    print(f"\n📊 Score Separation Analysis:")
    print(f"   Normal transactions score mean: {results['normal_score_mean']:.3f} ± {results['normal_score_std']:.3f}")
    print(f"   Anomalous transactions score mean: {results['anomaly_score_mean']:.3f} ± {results['anomaly_score_std']:.3f}")
    print(f"   Score separation: {results['score_separation']:.3f}")
    
    # Comprehensive interpretation
    print(f"\n💡 Comprehensive Interpretation:")
    
    # F1-Score interpretation
    print(f"   📊 Classification Performance (F1-Score):")
    if results['f1_score'] > 0.8:
        print("      ✅ Excellent classification performance")
    elif results['f1_score'] > 0.7:
        print("      ✅ Good classification performance")
    elif results['f1_score'] > 0.5:
        print("      ⚠️  Moderate classification performance")
    else:
        print("      ❌ Poor classification performance")
    
    # Score separation interpretation
    print(f"   🔍 Algorithm Behavior (Score Separation):")
    if results['score_separation'] > 0.5:
        print("      ✅ Excellent discriminative power")
    elif results['score_separation'] > 0.3:
        print("      ✅ Good discriminative power")
    elif results['score_separation'] > 0.1:
        print("      ⚠️  Moderate discriminative power")
    else:
        print("      ❌ Poor discriminative power")
    
    # Detection capability
    print(f"   🎯 Detection Capability:")
    if results['detection_rate'] > 0.7:
        print("      ✅ Good anomaly detection capability")
    elif results['detection_rate'] > 0.5:
        print("      ⚠️  Moderate anomaly detection capability")
    else:
        print("      ❌ Poor anomaly detection capability")
    
    # False positive analysis
    print(f"   ⚠️  False Positive Analysis:")
    if results['false_positive_rate'] < 0.1:
        print("      ✅ Low false positive rate (operational efficiency)")
    elif results['false_positive_rate'] < 0.2:
        print("      ⚠️  Moderate false positive rate (acceptable)")
    else:
        print("      ❌ High false positive rate (operational burden)")
    
    # Overall assessment
    print(f"\n🎯 Overall Assessment:")
    if results['f1_score'] > 0.7 and results['score_separation'] > 0.3:
        print("   ✅ Model is ready for deployment")
    elif results['f1_score'] > 0.5 and results['score_separation'] > 0.1:
        print("   ⚠️  Model needs optimization before deployment")
    else:
        print("   ❌ Model requires significant improvement")

def test_specific_anomalies():
    """Test model performance on specific anomaly types."""
    print("\n🔬 TESTING SPECIFIC ANOMALY TYPES")
    print("-" * 40)
    
    model, columns = load_model()
    if model is None:
        return
    
    normal_df = load_normal_data()
    if normal_df is None:
        return
    
    # Test key anomaly types
    key_anomalies = [
        'Suspicious Overpricing',
        'Bid Ceiling Collusion', 
        'End of Year Rush',
        'Compressed Timeline',
        'Favored Supplier'
    ]
    
    for anomaly_name in key_anomalies:
        print(f"\n🧪 Testing: {anomaly_name}")
        
        # Inject this specific anomaly type
        test_df = inject_anomalies(normal_df, [anomaly_name])
        
        # Evaluate performance
        results = evaluate_model_performance(model, columns, test_df)
        
        print(f"   Detection Rate: {results['detection_rate']:.3f}")
        print(f"   False Positive Rate: {results['false_positive_rate']:.3f}")
        print(f"   F1-Score: {results['f1_score']:.3f}")
        print(f"   Score Separation: {results['score_separation']:.3f}")

def compare_score_separation_vs_f1():
    """Compare score separation vs F1-score across different contamination values."""
    print("\n🔬 COMPARING SCORE SEPARATION vs F1-SCORE")
    print("-" * 50)
    
    normal_df = load_normal_data()
    if normal_df is None:
        return
    
    # Test different contamination values
    contamination_values = [0.01, 0.05, 0.10, 0.15, 0.20]
    comparison_results = []
    
    print(f"\n📊 Performance Comparison Across Contamination Values:")
    print(f"{'Contamination':<12} {'F1-Score':<10} {'Score Sep.':<12} {'Detection':<10} {'FPR':<8} {'Assessment':<15}")
    print("-" * 80)
    
    for contamination in contamination_values:
        # Create model with this contamination
        from sklearn.ensemble import IsolationForest
        test_model = IsolationForest(
            contamination=str(contamination),  # Convert to string to fix linter error
            random_state=42,
            n_estimators=100
        )
        
        # Prepare data for training
        cleaned_df = preprocessing.clean_raw_data(normal_df)
        processed_df, feature_cols = feature_engineering.create_model_features(cleaned_df)
        
        # Get columns from the processed data
        columns = [col for col in processed_df.columns if col in feature_cols]
        
        # Train on normal data only
        X_train = processed_df[columns]
        test_model.fit(X_train)
        
        # Test on mixed data
        test_df = inject_anomalies(normal_df)
        test_results = evaluate_model_performance(test_model, columns, test_df)
        
        # Determine assessment
        if test_results['f1_score'] > 0.7 and test_results['score_separation'] > 0.3:
            assessment = "✅ Excellent"
        elif test_results['f1_score'] > 0.5 and test_results['score_separation'] > 0.1:
            assessment = "⚠️  Good"
        else:
            assessment = "❌ Poor"
        
        # Store results
        comparison_results.append({
            'contamination': contamination,
            'f1_score': test_results['f1_score'],
            'score_separation': test_results['score_separation'],
            'detection_rate': test_results['detection_rate'],
            'false_positive_rate': test_results['false_positive_rate'],
            'assessment': assessment
        })
        
        # Print results
        print(f"{contamination:<12} {test_results['f1_score']:<10.3f} {test_results['score_separation']:<12.3f} "
              f"{test_results['detection_rate']:<10.3f} {test_results['false_positive_rate']:<8.3f} {assessment:<15}")
    
    # Find optimal contamination
    best_f1_idx = max(range(len(comparison_results)), key=lambda i: comparison_results[i]['f1_score'])
    best_sep_idx = max(range(len(comparison_results)), key=lambda i: comparison_results[i]['score_separation'])
    
    print(f"\n💡 Analysis:")
    print(f"   Best F1-Score: Contamination = {comparison_results[best_f1_idx]['contamination']} "
          f"(F1 = {comparison_results[best_f1_idx]['f1_score']:.3f})")
    print(f"   Best Score Separation: Contamination = {comparison_results[best_sep_idx]['contamination']} "
          f"(Separation = {comparison_results[best_sep_idx]['score_separation']:.3f})")
    
    # Determine if they agree
    if best_f1_idx == best_sep_idx:
        print(f"   ✅ F1-Score and Score Separation agree on optimal contamination")
    else:
        print(f"   ⚠️  F1-Score and Score Separation suggest different optimal contaminations")
        print(f"      Consider operational requirements when choosing between them")
    
    return comparison_results

def generate_thesis_report(results, comparison_results):
    """Generate a comprehensive report for thesis documentation."""
    print("\n📝 GENERATING THESIS REPORT")
    print("=" * 50)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'overall_performance': results,
        'contamination_analysis': comparison_results,
        'key_findings': {},
        'recommendations': []
    }
    
    # Analyze overall performance
    if results['f1_score'] > 0.7 and results['score_separation'] > 0.3:
        report['key_findings']['model_quality'] = 'Excellent'
        report['recommendations'].append('Model is ready for deployment')
    elif results['f1_score'] > 0.5 and results['score_separation'] > 0.1:
        report['key_findings']['model_quality'] = 'Good'
        report['recommendations'].append('Model needs minor optimization')
    else:
        report['key_findings']['model_quality'] = 'Poor'
        report['recommendations'].append('Model requires significant improvement')
    
    # Analyze contamination optimization
    if comparison_results:
        best_f1_idx = max(range(len(comparison_results)), key=lambda i: comparison_results[i]['f1_score'])
        best_sep_idx = max(range(len(comparison_results)), key=lambda i: comparison_results[i]['score_separation'])
        
        report['key_findings']['optimal_f1_contamination'] = comparison_results[best_f1_idx]['contamination']
        report['key_findings']['optimal_separation_contamination'] = comparison_results[best_sep_idx]['contamination']
        report['key_findings']['metrics_agreement'] = best_f1_idx == best_sep_idx
        
        if best_f1_idx == best_sep_idx:
            report['recommendations'].append(f'Use contamination = {comparison_results[best_f1_idx]["contamination"]} for optimal performance')
        else:
            report['recommendations'].append('Consider operational requirements when choosing between F1-score and score separation optima')
    
    # Print report summary
    print(f"\n📊 THESIS REPORT SUMMARY:")
    print(f"   Model Quality: {report['key_findings']['model_quality']}")
    print(f"   F1-Score: {results['f1_score']:.3f}")
    print(f"   Score Separation: {results['score_separation']:.3f}")
    print(f"   Detection Rate: {results['detection_rate']:.3f}")
    print(f"   False Positive Rate: {results['false_positive_rate']:.3f}")
    
    if comparison_results:
        print(f"\n   Optimal Contamination Analysis:")
        print(f"     Best F1-Score: {report['key_findings']['optimal_f1_contamination']}")
        print(f"     Best Score Separation: {report['key_findings']['optimal_separation_contamination']}")
        print(f"     Metrics Agreement: {'Yes' if report['key_findings']['metrics_agreement'] else 'No'}")
    
    print(f"\n   Recommendations:")
    for rec in report['recommendations']:
        print(f"     • {rec}")
    
    return report

def main():
    """Main validation function."""
    print("🚀 ISOLATION FOREST MODEL VALIDATION")
    print("=" * 50)
    
    # Load model and data
    model, columns = load_model()
    if model is None:
        return
    
    normal_df = load_normal_data()
    if normal_df is None:
        return
    
    print(f"\n✅ Model loaded successfully")
    if columns is not None:
        print(f"✅ Feature columns: {len(columns)}")
    else:
        print("⚠️  No feature columns loaded")
    
    # Test 1: Overall performance with mixed anomalies
    print(f"\n📋 TEST 1: Overall Performance")
    print("-" * 30)
    
    test_df = inject_anomalies(normal_df)
    results = evaluate_model_performance(model, columns, test_df)
    print_results(results)
    
    # Test 2: Specific anomaly types
    test_specific_anomalies()
    
    # Test 3: Score Separation vs F1-Score Comparison
    print(f"\n📋 TEST 3: Score Separation vs F1-Score Analysis")
    print("-" * 50)
    comparison_results = compare_score_separation_vs_f1()
    
    # Generate thesis report
    thesis_report = generate_thesis_report(results, comparison_results)
    
    # Test 4: Contamination analysis with enhanced metrics
    print(f"\n📋 TEST 4: Enhanced Contamination Analysis")
    print("-" * 40)
    
    contamination_values = [0.01, 0.05, 0.10, 0.15, 0.20]
    
    for contamination in contamination_values:
        print(f"\n🧪 Testing contamination = {contamination}")
        
        # Create model with this contamination
        from sklearn.ensemble import IsolationForest
        test_model = IsolationForest(
            contamination=str(contamination),  # convrt to string to fix linter error
            random_state=42,
            n_estimators=100
        )
        
        # Prepare data for training
        cleaned_df = preprocessing.clean_raw_data(normal_df)
        processed_df, feature_cols = feature_engineering.create_model_features(cleaned_df)
        
        # Get columns from the processed data
        if columns is None:
            columns = [col for col in processed_df.columns if col in feature_cols]
        
        # Train on normal data only
        X_train = processed_df[columns]
        test_model.fit(X_train)
        
        # Test on mixed data
        test_df = inject_anomalies(normal_df)
        test_results = evaluate_model_performance(test_model, columns, test_df)
        
        print(f"   Detection Rate: {test_results['detection_rate']:.3f}")
        print(f"   False Positive Rate: {test_results['false_positive_rate']:.3f}")
        print(f"   F1-Score: {test_results['f1_score']:.3f}")
        print(f"   Score Separation: {test_results['score_separation']:.3f}")
    
    print(f"\n✅ Validation complete!")

if __name__ == "__main__":
    main() 