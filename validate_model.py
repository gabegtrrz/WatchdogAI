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
    
    # Score analysis
    normal_scores = scores[true_labels == 0]
    anomaly_scores = scores[true_labels == 1]
    
    results = {
        'detection_rate': detection_rate,
        'false_positive_rate': false_positive_rate,
        'precision': precision,
        'recall': recall,
        'total_anomalies': total_anomalies,
        'detected_anomalies': detected_anomalies,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'normal_score_mean': normal_scores.mean() if len(normal_scores) > 0 else 0,
        'anomaly_score_mean': anomaly_scores.mean() if len(anomaly_scores) > 0 else 0,
        'score_separation': abs(anomaly_scores.mean() - normal_scores.mean()) if len(anomaly_scores) > 0 and len(normal_scores) > 0 else 0
    }
    
    return results

def print_results(results):
    """Print formatted validation results."""
    print("\n" + "="*60)
    print("📊 MODEL VALIDATION RESULTS")
    print("="*60)
    
    print(f"🎯 Detection Rate: {results['detection_rate']:.3f} ({results['detected_anomalies']}/{results['total_anomalies']})")
    print(f"❌ False Positive Rate: {results['false_positive_rate']:.3f} ({results['false_positives']} false alarms)")
    print(f"📈 Precision: {results['precision']:.3f}")
    print(f"🔄 Recall: {results['recall']:.3f}")
    
    print(f"\n📊 Score Analysis:")
    print(f"   Normal transactions score mean: {results['normal_score_mean']:.3f}")
    print(f"   Anomalous transactions score mean: {results['anomaly_score_mean']:.3f}")
    print(f"   Score separation: {results['score_separation']:.3f}")
    
    # Interpretation
    print(f"\n💡 Interpretation:")
    if results['detection_rate'] > 0.7:
        print("   ✅ Good anomaly detection capability")
    elif results['detection_rate'] > 0.5:
        print("   ⚠️  Moderate anomaly detection capability")
    else:
        print("   ❌ Poor anomaly detection capability")
    
    if results['false_positive_rate'] < 0.1:
        print("   ✅ Low false positive rate")
    elif results['false_positive_rate'] < 0.2:
        print("   ⚠️  Moderate false positive rate")
    else:
        print("   ❌ High false positive rate")

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
    print(f"✅ Feature columns: {len(columns)}")
    
    # Test 1: Overall performance with mixed anomalies
    print(f"\n📋 TEST 1: Overall Performance")
    print("-" * 30)
    
    test_df = inject_anomalies(normal_df)
    results = evaluate_model_performance(model, columns, test_df)
    print_results(results)
    
    # Test 2: Specific anomaly types
    test_specific_anomalies()
    
    # Test 3: Contamination analysis
    print(f"\n📋 TEST 3: Contamination Analysis")
    print("-" * 30)
    
    contamination_values = [0.01, 0.05, 0.10, 0.15, 0.20]
    
    for contamination in contamination_values:
        print(f"\n🧪 Testing contamination = {contamination}")
        
        # Create model with this contamination
        from sklearn.ensemble import IsolationForest
        test_model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        
        # Prepare data for training
        cleaned_df = preprocessing.clean_raw_data(normal_df)
        processed_df, feature_cols = feature_engineering.create_model_features(cleaned_df)
        
        # Train on normal data only
        X_train = processed_df[columns]
        test_model.fit(X_train)
        
        # Test on mixed data
        test_df = inject_anomalies(normal_df)
        test_results = evaluate_model_performance(test_model, columns, test_df)
        
        print(f"   Detection Rate: {test_results['detection_rate']:.3f}")
        print(f"   False Positive Rate: {test_results['false_positive_rate']:.3f}")
    
    print(f"\n✅ Validation complete!")
    print(f"📝 Results can be used for thesis documentation")

if __name__ == "__main__":
    main() 