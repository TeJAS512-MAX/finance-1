import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import accuracy_score
import json
import joblib

# Add project root to path so we can import modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from intelligence.ml_filter import ml_filter

def run_mda():
    print("==================================================")
    print(" 🧠 Mean Decrease Accuracy (MDA) Feature Pruning")
    print("==================================================")
    
    # Load dataset
    data_path = Path(__file__).parent.parent / "data" / "triple_barrier_dataset_upstox.csv"
    if not data_path.exists():
        print("[ERROR] Dataset not found. Run train_ml.py first.")
        return
        
    df = pd.read_csv(data_path)
    print(f"[OK] Loaded dataset with {len(df)} samples.")
    
    # Reload model
    ml_filter._load_if_exists()
    if not ml_filter.is_loaded:
        print("[ERROR] Ensemble model not found. Run train_ml.py first.")
        return
        
    required_cols = ml_filter.feature_cols + ['target']
    df = df.dropna(subset=required_cols).copy()
    
    X = df[ml_filter.feature_cols]
    y = df['target']
    
    X_scaled = ml_filter.scaler.transform(X)
    
    # Use the Random Forest from the ensemble to calculate baseline accuracy
    rf = ml_filter.models["rf"]
    baseline_pred = rf.predict(X_scaled)
    baseline_acc = accuracy_score(y, baseline_pred)
    print(f"\nBaseline Accuracy (Random Forest): {baseline_acc:.4f}\n")
    
    # Compute MDA for each feature
    mda_scores = {}
    
    for i, col in enumerate(ml_filter.feature_cols):
        X_shuffled = X_scaled.copy()
        
        # Shuffle a single feature column to destroy its predictive power
        np.random.shuffle(X_shuffled[:, i])
        
        # Measure accuracy after scrambling
        shuffled_pred = rf.predict(X_shuffled)
        shuffled_acc = accuracy_score(y, shuffled_pred)
        
        # The decrease in accuracy is the feature's importance (MDA)
        mda = baseline_acc - shuffled_acc
        mda_scores[col] = mda
        
    print("📊 Feature Importance (Mean Decrease Accuracy):")
    print("-" * 50)
    for col, mda in sorted(mda_scores.items(), key=lambda x: x[1], reverse=True):
        if mda <= 0:
            print(f"  ❌ {col:15}: {mda:8.4f} (NOISE: Scrambling improved/did not hurt model)")
        else:
            print(f"  ✅ {col:15}: {mda:8.4f} (ALPHA: Essential for prediction)")
            
    print("-" * 50)
    print("[INFO] Features marked as NOISE should be removed from the feature vector.")

if __name__ == "__main__":
    run_mda()
