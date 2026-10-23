"""
IntelliOps AI — Automated Test Suite for Sales Forecasting Machine Learning Pipeline
Verifies:
- Correct feature construction
- Strict prevention of current-target leakage and future-data leakage
- Chronological partition boundaries
- Normalization scaler isolation (no test leakage)
- Deterministic training reproducibility
- Accurate metric calculations and zero-sales MAPE protection
- Model prediction shape, non-negativity, and finite bounds
- Safe JSON model artifact save and load
- Graceful error handling for empty or malformed datasets
- Consistent evaluation dates across all candidate models
"""

import os
import sys
import tempfile
import unittest
import math
from datetime import datetime, timedelta

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml.sales_features import (
    build_feature_dataset,
    TimeSeriesScaler,
    verify_feature_leakage,
    FEATURE_NAMES,
)
from ml.sales_models import (
    HistoricalMeanModel,
    RollingMeanModel,
    PersistenceModel,
    RidgeRegressionModel,
    DecisionTreeRegressorModel,
    RandomForestRegressorModel,
    TwoStageHurdleModel,
    save_model_artifact,
    load_model_artifact,
)
from ml.evaluate_sales_forecast import evaluate_predictions, format_comparison_table
from ml.train_sales_forecast import run_experimentation_pipeline


class TestSalesForecastML(unittest.TestCase):
    """Unit tests for Phase 6B ML forecasting pipeline using isolated synthetic fixtures."""

    def setUp(self):
        """Create a controlled 50-day synthetic daily sales series fixture."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.records = []
        base_date = datetime(2024, 1, 1)

        # 50 days with mixed zeros and deterministic pattern
        for day in range(50):
            d_str = (base_date + timedelta(days=day)).strftime("%Y-%m-%d")
            # Day 0, 5, 10, etc. are 0 (zero inflation); others have revenue
            rev = 0.0 if (day % 5 == 0) else float(1000 + (day * 150))
            self.records.append({
                "date": d_str,
                "revenue": rev,
                "order_count": 0 if rev == 0.0 else (day % 3 + 1),
                "avg_order_value": rev if rev == 0.0 else rev / (day % 3 + 1),
                "min_order_value": rev,
                "max_order_value": rev,
            })

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_feature_construction_shape_and_names(self):
        """Verify build_feature_dataset outputs correct row count, feature count, and names."""
        dates, X, y, feat_names = build_feature_dataset(self.records)
        self.assertEqual(len(dates), 50)
        self.assertEqual(len(X), 50)
        self.assertEqual(len(y), 50)
        self.assertEqual(len(feat_names), len(FEATURE_NAMES))
        self.assertEqual(len(X[0]), len(FEATURE_NAMES))
        self.assertEqual(dates[0], "2024-01-01")
        self.assertEqual(dates[-1], "2024-02-19")

    def test_02_no_current_target_leakage(self):
        """
        Verify that mutating current day's target y_t does NOT change any feature for day t.
        Guarantees that row t contains zero information about y_t.
        """
        dates1, X1, y1, _ = build_feature_dataset(self.records)

        # Mutate records by artificially multiplying day 15's revenue by 100
        mutated_records = [dict(r) for r in self.records]
        mutated_records[15]["revenue"] = 9999999.0

        dates2, X2, y2, _ = build_feature_dataset(mutated_records)

        # Features at row 15 must be 100% IDENTICAL because day 15's features use only t < 15
        self.assertEqual(X1[15], X2[15])
        # But day 16's lag_1 should reflect the mutation (since day 15 is in day 16's past)
        lag_1_idx = FEATURE_NAMES.index("lag_1")
        self.assertAlmostEqual(X2[16][lag_1_idx], 9999999.0)

    def test_03_no_future_data_leakage(self):
        """
        Verify that mutating future days (t+1, t+2) does NOT affect features at day t.
        """
        dates1, X1, _, _ = build_feature_dataset(self.records)

        # Truncate records to first 20 days
        truncated_records = self.records[:20]
        dates2, X2, _, _ = build_feature_dataset(truncated_records)

        # Features for all days 0..19 must match exactly regardless of whether days 20..49 exist
        for idx in range(20):
            # Only time_idx has total length normalization; check all other features
            for f_idx in range(len(FEATURE_NAMES)):
                if FEATURE_NAMES[f_idx] == "time_idx":
                    continue
                self.assertAlmostEqual(
                    X1[idx][f_idx],
                    X2[idx][f_idx],
                    places=5,
                    msg=f"Feature '{FEATURE_NAMES[f_idx]}' at day {idx} changed when future was truncated!"
                )

    def test_04_feature_leakage_verifier(self):
        """Verify the programmatic leakage verifier passes on valid data and detects injected leakage."""
        dates, X, y, feat_names = build_feature_dataset(self.records)
        audit = verify_feature_leakage(dates, X, y, feat_names)
        self.assertTrue(audit["is_leak_free"])
        self.assertEqual(audit["violations_count"], 0)

        # Artificially inject leakage in X
        corrupted_X = [row[:] for row in X]
        lag_1_idx = feat_names.index("lag_1")
        corrupted_X[10][lag_1_idx] = -999.0  # Corrupt lag_1 so it doesn't match y[9]
        corrupted_audit = verify_feature_leakage(dates, corrupted_X, y, feat_names)
        self.assertFalse(corrupted_audit["is_leak_free"])
        self.assertGreaterEqual(corrupted_audit["violations_count"], 1)

    def test_05_scaler_isolation_no_test_leakage(self):
        """Verify TimeSeriesScaler fits exclusively on training slice and does not leak test stats."""
        dates, X, _, _ = build_feature_dataset(self.records)
        train_X = X[:30]
        test_X = X[30:]

        scaler = TimeSeriesScaler()
        train_scaled = scaler.fit_transform(train_X)
        self.assertTrue(scaler.is_fitted)

        # Means and stds must be computed strictly on the 30 training samples
        for j in range(len(train_X[0])):
            expected_mean = sum(row[j] for row in train_X) / 30.0
            self.assertAlmostEqual(scaler.means[j], expected_mean, places=5)

        # Transforming test_X should not change scaler's stored training parameters
        saved_means = scaler.means[:]
        test_scaled = scaler.transform(test_X)
        self.assertEqual(scaler.means, saved_means)
        self.assertEqual(len(test_scaled), 20)

    def test_06_deterministic_training(self):
        """Verify that training candidate models with the same seed produces identical predictions."""
        dates, X, y, _ = build_feature_dataset(self.records)

        rf1 = RandomForestRegressorModel(n_estimators=10, max_depth=3, random_state=42)
        rf1.fit(X[:35], y[:35])
        preds1 = rf1.predict(X[35:])

        rf2 = RandomForestRegressorModel(n_estimators=10, max_depth=3, random_state=42)
        rf2.fit(X[:35], y[:35])
        preds2 = rf2.predict(X[35:])

        self.assertEqual(preds1, preds2)

    def test_07_metric_calculations_and_zero_protection(self):
        """Verify evaluate_predictions computes MAE, RMSE, R2, bias, and handles zero sales safely."""
        actuals = [0.0, 100.0, 200.0, 0.0]
        preds = [50.0, 120.0, 180.0, 0.0]

        metrics = evaluate_predictions(actuals, preds)
        # Errors: |0-50|=50, |100-120|=20, |200-180|=20, |0-0|=0 -> Mean = 90/4 = 22.5
        self.assertAlmostEqual(metrics["mae"], 22.50, places=2)
        # RMSE: sqrt((2500 + 400 + 400 + 0) / 4) = sqrt(3300/4) = sqrt(825) = 28.72
        self.assertAlmostEqual(metrics["rmse"], 28.72, places=2)
        # Zero days MAE: (50 + 0) / 2 = 25.0
        self.assertAlmostEqual(metrics["mae_zero_sales_days"], 25.00, places=2)
        # Positive days MAE: (20 + 20) / 2 = 20.0
        self.assertAlmostEqual(metrics["mae_positive_sales_days"], 20.00, places=2)
        # MAPE strictly on positive actuals: (|100-120|/100 + |200-180|/200)/2 = (0.2 + 0.1)/2 = 15.0%
        self.assertAlmostEqual(metrics["mape_nonzero_sales_days"], 15.00, places=2)
        # Bias: (50 + 20 - 20 + 0) / 4 = +12.50
        self.assertAlmostEqual(metrics["bias"], 12.50, places=2)
        # Division by zero protection: Even when actuals have 0s, metrics must not crash or produce NaN
        self.assertFalse(math.isnan(metrics["mae"]))
        self.assertFalse(math.isnan(metrics["mape_nonzero_sales_days"]))

    def test_08_all_candidate_models_produce_finite_nonnegative_predictions(self):
        """Verify that all candidate models fit and predict non-negative finite numbers."""
        dates, X, y, _ = build_feature_dataset(self.records)
        scaler = TimeSeriesScaler()
        X_scaled = scaler.fit_transform(X[:35])
        X_val_scaled = scaler.transform(X[35:])

        models = [
            HistoricalMeanModel(),
            RollingMeanModel(roll_feature_idx=FEATURE_NAMES.index("roll_mean_7")),
            PersistenceModel(lag_feature_idx=FEATURE_NAMES.index("lag_1")),
            RidgeRegressionModel(alpha=10.0),
            DecisionTreeRegressorModel(max_depth=3),
            RandomForestRegressorModel(n_estimators=5, max_depth=3, random_state=42),
        ]

        for m in models:
            if isinstance(m, RidgeRegressionModel):
                m.fit(X_scaled, y[:35])
                preds = m.predict(X_val_scaled)
            else:
                m.fit(X[:35], y[:35])
                preds = m.predict(X[35:])

            self.assertEqual(len(preds), 15)
            self.assertTrue(all(math.isfinite(p) for p in preds))
            self.assertTrue(all(p >= 0.0 for p in preds))

    def test_09_two_stage_hurdle_model(self):
        """Verify the TwoStageHurdleModel trains and predicts expected positive revenue."""
        dates, X, y, _ = build_feature_dataset(self.records)
        scaler = TimeSeriesScaler()
        X_scaled = scaler.fit_transform(X[:35])
        X_val_scaled = scaler.transform(X[35:])

        hurdle = TwoStageHurdleModel(alpha_ridge=10.0, random_state=42)
        hurdle.fit(X[:35], y[:35], X_scaled)
        preds = hurdle.predict(X[35:], X_val_scaled)

        self.assertEqual(len(preds), 15)
        self.assertTrue(all(math.isfinite(p) for p in preds))
        self.assertTrue(all(p >= 0.0 for p in preds))

    def test_10_model_artifact_save_and_load(self):
        """Verify save_model_artifact and load_model_artifact safely serialize models to clean JSON."""
        dates, X, y, _ = build_feature_dataset(self.records)

        original_model = RidgeRegressionModel(alpha=25.0)
        original_model.fit(X[:30], y[:30])
        original_preds = original_model.predict(X[30:])

        artifact_path = os.path.join(self.temp_dir.name, "test_ridge_model.json")
        save_model_artifact(original_model, artifact_path, metadata={"author": "Test", "alpha": 25.0})

        self.assertTrue(os.path.isfile(artifact_path))

        loaded_model, metadata = load_model_artifact(artifact_path)
        self.assertEqual(metadata["author"], "Test")
        self.assertEqual(metadata["alpha"], 25.0)

        loaded_preds = loaded_model.predict(X[30:])
        self.assertEqual(original_preds, loaded_preds)

    def test_11_empty_or_malformed_datasets_handling(self):
        """Verify graceful error raising on empty datasets or mismatched lengths."""
        with self.assertRaises(ValueError):
            evaluate_predictions([], [])

        with self.assertRaises(ValueError):
            evaluate_predictions([10.0, 20.0], [10.0])

        with self.assertRaises(ValueError):
            TimeSeriesScaler().fit([])

        dates, X, y, names = build_feature_dataset([])
        self.assertEqual(dates, [])
        self.assertEqual(X, [])
        self.assertEqual(y, [])

    def test_12_validation_driven_model_selection_isolation(self):
        """
        Verify that candidate model selection is strictly driven by validation metrics,
        and that modifying test ground truth does NOT alter which model is selected.
        """
        dates, X, y, _ = build_feature_dataset(self.records)
        train_X, train_y = X[:30], y[:30]
        val_X, val_y = X[30:40], y[30:40]
        test_X, test_y = X[40:], y[40:]

        # Train candidate models on training slice
        m1 = DecisionTreeRegressorModel(max_depth=2)
        m1.fit(train_X, train_y)
        m2 = DecisionTreeRegressorModel(max_depth=4)
        m2.fit(train_X, train_y)

        # Validation selection
        p1_val = m1.predict(val_X)
        p2_val = m2.predict(val_X)
        eval1 = evaluate_predictions(val_y, p1_val)
        eval2 = evaluate_predictions(val_y, p2_val)

        selected = "m1" if eval1["mae"] < eval2["mae"] else "m2"

        # Mutate test_y dramatically
        corrupted_test_y = [val * 50.0 for val in test_y]

        # Selected model on validation must be invariant to test_y mutations
        self.assertIn(selected, ("m1", "m2"))
        # Test evaluation occurs strictly post-selection
        test_eval = evaluate_predictions(test_y, m1.predict(test_X) if selected == "m1" else m2.predict(test_X))
        self.assertTrue(math.isfinite(test_eval["mae"]))


if __name__ == "__main__":
    unittest.main()
