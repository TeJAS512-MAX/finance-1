import numpy as np
import pandas as pd
import joblib
import json
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

class MLQualityFilter:
    """
    Phase 2A: Machine Learning Quality Filter with Ensemble Modeling (The Tribunal).
    """
    def __init__(self, model_prefix="ml_model_ensemble_upstox"):
        self.model_dir = Path(__file__).parent.parent / "data"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.prefix = model_prefix
        
        self.models = {}
        self.scaler = StandardScaler()
        self.approval_threshold = 0.51
        
        self.feature_cols = [
            'rsi', 'ema9', 'ema21', 'vwap', 'atr14',
            'momentum', 'volatility', 'trend_strength',
            'range_pct', 'return_5', 'return_20', 'frac_diff', 'direction'
        ]
        
        self.is_loaded = False
        self._load_if_exists()
        
    def _load_if_exists(self):
        try:
            scaler_path = self.model_dir / f"{self.prefix}_scaler.joblib"
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
                
                for name in ["hgb", "rf", "et", "dnn"]:
                    mp = self.model_dir / f"{self.prefix}_{name}.joblib"
                    if mp.exists():
                        self.models[name] = joblib.load(mp)
                
                meta_path = self.model_dir / f"{self.prefix}_meta.json"
                if meta_path.exists():
                    metadata = json.loads(meta_path.read_text())
                    self.approval_threshold = float(metadata.get("approval_threshold", 0.6))
                    
                if len(self.models) == 4:
                    self.is_loaded = True
                    print("[ML] ML Ensemble Tribunal loaded successfully.")
        except Exception as e:
            print(f"[WARN] Failed to load ML models: {e}")
            self.is_loaded = False

    def predict(self, features: dict) -> float:
        """
        Returns a mean probability if all models in the ensemble agree > 0.5.
        Else returns 0.0 (veto).
        """
        if not self.is_loaded or len(self.models) < 4:
            # Never convert a missing or incomplete model into a tradable
            # neutral signal, particularly when an aggressive threshold is in
            # use.  The caller will journal the rejection and wait for a
            # healthy model artifact.
            return 0.0
            
        try:
            values = []
            for col in self.feature_cols:
                value = features.get(col, 0.0)
                if col == "direction" and isinstance(value, str):
                    value = {"LONG": 1.0, "SHORT": -1.0}.get(value.upper(), 0.0)
                values.append(value)
                
            x = pd.DataFrame([values], columns=self.feature_cols)
            x_scaled = self.scaler.transform(x)
            
            probs = []
            for name, model in self.models.items():
                prob = model.predict_proba(x_scaled)[0][1]
                probs.append(prob)
                
            mean_prob = np.mean(probs)
            # AGGRESSIVE MODE: Rely purely on the mean probability across all 4 models > 0.40
            if mean_prob < 0.40:
                return 0.0
                
            return float(mean_prob)
        except Exception as e:
            print(f"ML predict error: {e}")
            return 0.0

    def train_on_backtest_data(
        self,
        backtest_df: pd.DataFrame,
        mode: str = "standard",
        validation_fraction: float = 0.2,
    ):
        mode = mode.lower().strip()
        if mode not in {"standard", "aggressive"}:
            raise ValueError("mode must be 'standard' or 'aggressive'")
        if not 0 < validation_fraction < 0.5:
            raise ValueError("validation_fraction must be between 0 and 0.5")

        print(f"[ML] Training ML Ensemble Tribunal ({mode} mode)...")
        
        required_cols = self.feature_cols + ['target']
        df = backtest_df.copy()
        
        for col in self.feature_cols:
            if col not in df.columns:
                df[col] = 0.0
                
        df = df.dropna(subset=required_cols)
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        if len(df) < 40:
            return False

        if df["target"].nunique() < 2:
            print("[WARN] Training requires both target classes.")
            return False

        # Keep validation chronological so future labels never influence the
        # reported training score.
        split_index = max(1, int(len(df) * (1.0 - validation_fraction)))
        train_df = df.iloc[:split_index]
        validation_df = df.iloc[split_index:]

        X = df[self.feature_cols]
        y = df['target']
        X_train = train_df[self.feature_cols]
        y_train = train_df["target"]
        self.scaler.fit(X_train)
        X_train_scaled = self.scaler.transform(X_train)
        X_validation_scaled = self.scaler.transform(validation_df[self.feature_cols])
        
        class_weight = "balanced" if mode == "standard" else None
        self.models["hgb"] = HistGradientBoostingClassifier(class_weight=class_weight, max_iter=300, max_depth=6, random_state=42)
        self.models["rf"] = RandomForestClassifier(class_weight=class_weight, n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)
        self.models["et"] = ExtraTreesClassifier(class_weight=class_weight, n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)
        self.models["dnn"] = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=500, alpha=0.01, random_state=42)
        
        for name, model in self.models.items():
            model.fit(X_train_scaled, y_train)

        validation_probabilities = np.mean(
            [model.predict_proba(X_validation_scaled)[:, 1] for model in self.models.values()],
            axis=0,
        )
        validation_predictions = validation_probabilities >= (0.40 if mode == "aggressive" else 0.60)
        validation_target = validation_df["target"].to_numpy()
        validation_accuracy = float(np.mean(validation_predictions == validation_target))

        # Refit the persisted ensemble on all available history after the
        # chronological check, preserving the validation result in metadata.
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        for model in self.models.values():
            model.fit(X_scaled, y)
            
        self.is_loaded = True
        self.approval_threshold = 0.40 if mode == "aggressive" else 0.60
        
        # Save
        joblib.dump(self.scaler, self.model_dir / f"{self.prefix}_scaler.joblib")
        for name, model in self.models.items():
            joblib.dump(model, self.model_dir / f"{self.prefix}_{name}.joblib")
            
        (self.model_dir / f"{self.prefix}_meta.json").write_text(json.dumps({
            "approval_threshold": self.approval_threshold,
            "training_mode": mode,
            "training_rows": int(len(train_df)),
            "validation_rows": int(len(validation_df)),
            "validation_accuracy": round(validation_accuracy, 4),
            "class_balance": {
                "wins": int((y == 1).sum()),
                "losses": int((y == 0).sum()),
            },
        }, indent=2))
        
        print(f"[OK] Ensemble trained and saved. Chronological validation accuracy: {validation_accuracy:.1%}")
        return True

ml_filter = MLQualityFilter()
