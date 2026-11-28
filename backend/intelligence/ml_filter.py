import numpy as np
import pandas as pd
import joblib
import json
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

SCALE_INVARIANT_FEATURE_COLS = [
    'rsi', 'rsi_delta', 'ema9_dist_pct', 'ema21_dist_pct', 'vwap_dist_pct',
    'vol_ratio', 'momentum', 'volatility', 'trend_strength',
    'range_pct', 'return_5', 'return_20', 'frac_diff_pct',
    'cusum_event', 'body_pct', 'return_1', 'hour_ist', 'direction',
]


def _derive_feature_value(col: str, features: dict) -> float:
    """Resolve a numeric feature value, deriving scale-invariant ratios if raw keys are supplied."""
    if col == "direction":
        value = features.get("direction", features.get("candidate_direction", 0.0))
        if isinstance(value, str):
            value = {"LONG": 1.0, "SHORT": -1.0}.get(value.upper(), 0.0)
        return float(value) if value is not None else 0.0

    if col in features and features[col] is not None:
        return float(features[col])

    close = float(features.get("close", features.get("ltp", 0.0)) or 0.0)
    if col == "rsi_delta":
        rsi = float(features.get("rsi", 50.0) or 50.0)
        prev_rsi = float(features.get("prev_rsi", rsi) or rsi)
        return rsi - prev_rsi
    if col == "ema9_dist_pct" and close > 0 and "ema9" in features:
        return (close - float(features["ema9"])) / close * 100.0
    if col == "ema21_dist_pct" and close > 0 and "ema21" in features:
        return (close - float(features["ema21"])) / close * 100.0
    if col == "vwap_dist_pct":
        vwap = float(features.get("vwap", 0.0) or 0.0)
        return ((close - vwap) / vwap * 100.0) if vwap > 0 and close > 0 else 0.0
    if col == "frac_diff_pct" and close > 0 and "frac_diff" in features:
        return float(features["frac_diff"]) / close * 100.0
    if col == "body_pct":
        high = float(features.get("high", close) or close)
        low = float(features.get("low", close) or close)
        open_p = float(features.get("open", features.get("candle_open", close)) or close)
        span = high - low
        return (close - open_p) / span if span > 0 else 0.0
    if col == "hour_ist" and "timestamp" in features:
        dt = pd.to_datetime(features["timestamp"], utc=True, errors="coerce")
        if pd.notna(dt):
            dt_ist = dt.tz_convert("Asia/Kolkata")
            return float(dt_ist.hour + dt_ist.minute / 60.0)
        return 12.0
    return 0.0


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
        self.approval_threshold = 0.56
        
        self.feature_cols = list(SCALE_INVARIANT_FEATURE_COLS)
        
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
                        loaded = joblib.load(mp)
                        if hasattr(loaded, "n_jobs"):
                            loaded.n_jobs = 1
                        self.models[name] = loaded
                
                meta_path = self.model_dir / f"{self.prefix}_meta.json"
                if meta_path.exists():
                    metadata = json.loads(meta_path.read_text())
                    self.approval_threshold = float(metadata.get("approval_threshold", 0.56))
                    if isinstance(metadata.get("feature_cols"), list) and metadata["feature_cols"]:
                        self.feature_cols = list(metadata["feature_cols"])
                    
                if len(self.models) == 4:
                    self.is_loaded = True
                    print("[ML] ML Ensemble Tribunal loaded successfully.")
        except Exception as e:
            print(f"[WARN] Failed to load ML models: {e}")
            self.is_loaded = False

    def predict(self, features: dict) -> float:
        """
        Return ensemble probability if it meets self.approval_threshold, else 0.0 (veto).
        """
        if not self.is_loaded or len(self.models) < 4:
            return 0.0
            
        try:
            values = []
            for col in self.feature_cols:
                try:
                    numeric_value = float(_derive_feature_value(col, features))
                except (TypeError, ValueError):
                    numeric_value = 0.0
                if not np.isfinite(numeric_value):
                    numeric_value = 0.0
                values.append(numeric_value)

            x = pd.DataFrame([values], columns=self.feature_cols)
            x_scaled = self.scaler.transform(x)

            probs = [model.predict_proba(x_scaled)[0][1] for model in self.models.values()]
            mean_prob = float(np.mean(probs))
            if mean_prob < self.approval_threshold:
                return 0.0

            return mean_prob
        except Exception as e:
            print(f"ML predict error: {e}")
            return 0.0

    def predict_batch(self, frame: pd.DataFrame) -> np.ndarray:
        """Vectorized raw mean probability estimation over a batch of feature rows."""
        if not self.is_loaded or len(self.models) < 4 or frame.empty:
            return np.zeros(len(frame), dtype=float)
        working = frame.reindex(columns=self.feature_cols, fill_value=0.0).copy()
        working = working.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
        x_scaled = self.scaler.transform(working)
        probs = np.mean([model.predict_proba(x_scaled)[:, 1] for model in self.models.values()], axis=0)
        return np.asarray(probs, dtype=float)

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
        
        df = backtest_df.copy()
        for col in self.feature_cols:
            if col not in df.columns:
                df[col] = 0.0
        required_cols = self.feature_cols + ['target']
        df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=required_cols)
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        if len(df) < 40:
            return False

        if df["target"].nunique() < 2:
            print("[WARN] Training requires both target classes.")
            return False

        # Keep validation chronological so future labels never influence training or calibration.
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
        self.models["hgb"] = HistGradientBoostingClassifier(
            class_weight=class_weight, max_iter=200, max_depth=5,
            min_samples_leaf=50, l2_regularization=2.0, random_state=42,
        )
        self.models["rf"] = RandomForestClassifier(
            class_weight=class_weight, n_estimators=200, max_depth=8,
            min_samples_leaf=30, random_state=42, n_jobs=-1,
        )
        self.models["et"] = ExtraTreesClassifier(
            class_weight=class_weight, n_estimators=200, max_depth=8,
            min_samples_leaf=30, random_state=42, n_jobs=-1,
        )
        self.models["dnn"] = MLPClassifier(
            hidden_layer_sizes=(64, 32), max_iter=200,
            early_stopping=True, alpha=0.01, random_state=42,
        )
        
        for model in self.models.values():
            model.fit(X_train_scaled, y_train)

        validation_probabilities = np.mean(
            [model.predict_proba(X_validation_scaled)[:, 1] for model in self.models.values()],
            axis=0,
        )
        validation_target = validation_df["target"].to_numpy()

        # Calibrate approval threshold strictly on chronological validation set.
        # Restrict standard balanced mode to >= 0.56 so round-trip slippage + brokerage
        # (~0.20%) does not erode marginal high-frequency signals.
        candidate_thresholds = (
            (0.56, 0.58, 0.60)
            if mode == "standard"
            else (0.35, 0.37, 0.39, 0.41, 0.45)
        )
        min_signals = max(10, int(len(validation_df) * 0.002))
        best_threshold = candidate_thresholds[0]
        best_score = float("-inf")
        for th in candidate_thresholds:
            selected = validation_probabilities >= th
            count = int(selected.sum())
            if count < min_signals:
                continue
            win_rate_sel = float(validation_target[selected].mean())
            expected_r = win_rate_sel * 2.5 - (1.0 - win_rate_sel) * 1.5 - 0.25
            total_utility = expected_r * np.sqrt(min(count, 200))
            if total_utility > best_score:
                best_score = total_utility
                best_threshold = float(th)

        threshold = best_threshold
        validation_predictions = validation_probabilities >= threshold
        validation_accuracy = float(np.mean(validation_predictions == validation_target))

        # Refit the persisted ensemble on all available history after the
        # chronological check, preserving the validation result in metadata.
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        for model in self.models.values():
            model.fit(X_scaled, y)
            if hasattr(model, "n_jobs"):
                model.n_jobs = 1
            
        self.is_loaded = True
        self.approval_threshold = threshold
        
        # Save
        joblib.dump(self.scaler, self.model_dir / f"{self.prefix}_scaler.joblib")
        for name, model in self.models.items():
            joblib.dump(model, self.model_dir / f"{self.prefix}_{name}.joblib")
            
        selected_val_mask = validation_probabilities >= threshold
        (self.model_dir / f"{self.prefix}_meta.json").write_text(json.dumps({
            "approval_threshold": self.approval_threshold,
            "training_mode": mode,
            "feature_cols": self.feature_cols,
            "training_rows": int(len(train_df)),
            "validation_rows": int(len(validation_df)),
            "validation_accuracy": round(validation_accuracy, 4),
            "validation_selected_signals": int(selected_val_mask.sum()),
            "validation_selected_win_rate": round(
                float(validation_target[selected_val_mask].mean()), 4
            ) if selected_val_mask.any() else 0.0,
            "class_balance": {
                "wins": int((y == 1).sum()),
                "losses": int((y == 0).sum()),
            },
        }, indent=2))
        
        print(f"[OK] Ensemble trained and saved. Threshold={threshold:.2f}, Chronological val acc: {validation_accuracy:.1%}")
        return True

ml_filter = MLQualityFilter()
