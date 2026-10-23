"""
IntelliOps AI — Sales Forecasting Training & Evaluation Orchestrator
Executes reproducible model training, validation-based model selection,
and holdout test evaluation for daily sales revenue.

Workflow:
1. Extract audited daily sales revenue from SQLite database (read-only).
2. Generate leak-free temporal, lagged, and rolling features.
3. Fit scaler strictly on the training partition (2024-01-01 to 2025-06-30).
4. Train candidate models (Baselines, Ridge, Decision Tree, Random Forest, Two-Stage Hurdle).
5. Evaluate all models on Validation partition (2025-07-01 to 2025-09-30) for model selection.
6. Evaluate on final Holdout Test partition (2025-10-01 to 2025-12-31).
7. Save reproducible artifacts, predictions, and metadata to backend/ml/artifacts/.
"""

import os
import sys
import csv
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml.prepare_sales_data import extract_daily_sales_revenue, resolve_db_path
from ml.sales_features import build_feature_dataset, TimeSeriesScaler, verify_feature_leakage
from ml.sales_models import (
    HistoricalMeanModel,
    RollingMeanModel,
    PersistenceModel,
    RidgeRegressionModel,
    DecisionTreeRegressorModel,
    RandomForestRegressorModel,
    TwoStageHurdleModel,
    save_model_artifact,
)
from ml.evaluate_sales_forecast import evaluate_predictions, format_comparison_table

logger = logging.getLogger("ml.train_sales_forecast")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

TRAIN_END_DATE = "2025-06-30"
VAL_START_DATE = "2025-07-01"
VAL_END_DATE = "2025-09-30"
TEST_START_DATE = "2025-10-01"
TEST_END_DATE = "2025-12-31"


def run_experimentation_pipeline(
    db_path: Optional[str] = None,
    artifacts_dir: Optional[str] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Executes the full Phase 6B modeling experiment.

    Returns:
        Dictionary containing validation results, test results, selected model info, and file paths.
    """
    logger.info(f"Starting Sales Forecasting ML Pipeline [Seed={seed}]...")
    db_file = resolve_db_path(db_path)

    if not artifacts_dir:
        artifacts_dir = os.path.join(backend_dir, "ml", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    # 1. Extract daily completed revenue
    records = extract_daily_sales_revenue(
        db_path=db_file,
        start_date="2024-01-01",
        end_date="2025-12-31",
        fill_zeros=True,
    )
    if not records:
        raise RuntimeError("No sales records available to train forecasting models.")

    # 2. Build feature matrix
    dates, X_raw, y_all, feature_names = build_feature_dataset(records)

    # Audit for target leakage
    leakage_check = verify_feature_leakage(dates, X_raw, y_all, feature_names)
    if not leakage_check["is_leak_free"]:
        raise RuntimeError(f"Target leakage detected in feature pipeline: {leakage_check['violations']}")
    logger.info("[OK] Feature pipeline verified: ZERO target leakage detected.")

    # 3. Create chronological partitions
    train_indices = [i for i, d in enumerate(dates) if d <= TRAIN_END_DATE]
    val_indices = [i for i, d in enumerate(dates) if VAL_START_DATE <= d <= VAL_END_DATE]
    test_indices = [i for i, d in enumerate(dates) if d >= TEST_START_DATE]

    X_train_raw = [X_raw[i] for i in train_indices]
    y_train = [y_all[i] for i in train_indices]
    dates_train = [dates[i] for i in train_indices]

    X_val_raw = [X_raw[i] for i in val_indices]
    y_val = [y_all[i] for i in val_indices]
    dates_val = [dates[i] for i in val_indices]

    X_test_raw = [X_raw[i] for i in test_indices]
    y_test = [y_all[i] for i in test_indices]
    dates_test = [dates[i] for i in test_indices]

    logger.info(
        f"Partitions: Train={len(y_train)} days ({dates_train[0]} to {dates_train[-1]}), "
        f"Val={len(y_val)} days ({dates_val[0]} to {dates_val[-1]}), "
        f"Test={len(y_test)} days ({dates_test[0]} to {dates_test[-1]})."
    )

    # 4. Standardize features strictly fitting scaler on training partition
    scaler = TimeSeriesScaler()
    X_train_scaled = scaler.fit_transform(X_train_raw, feature_names)
    X_val_scaled = scaler.transform(X_val_raw)
    X_test_scaled = scaler.transform(X_test_raw)

    # 5. Initialize Candidate Models
    models: Dict[str, Any] = {
        "HistoricalMeanBaseline": HistoricalMeanModel(),
        "RollingMeanBaseline": RollingMeanModel(roll_feature_idx=feature_names.index("roll_mean_7")),
        "NaivePersistenceBaseline": PersistenceModel(lag_feature_idx=feature_names.index("lag_1")),
        "RidgeRegression_alpha50": RidgeRegressionModel(alpha=50.0),
        "DecisionTreeRegressor": DecisionTreeRegressorModel(max_depth=3, min_samples_split=15),
        "RandomForestRegressor": RandomForestRegressorModel(n_estimators=15, max_depth=4, random_state=seed),
        "TwoStageHurdleModel": TwoStageHurdleModel(alpha_ridge=50.0, random_state=seed),
    }

    # 6. Fit Models on Training Partition
    logger.info("Fitting candidate models on training set...")
    for name, model in models.items():
        if name in ("RidgeRegression_alpha50",):
            model.fit(X_train_scaled, y_train)
        elif name in ("TwoStageHurdleModel",):
            model.fit(X_train_raw, y_train, X_train_scaled)
        else:
            model.fit(X_train_raw, y_train)

    # 7. Model Selection on Validation Partition
    logger.info("Evaluating candidates on validation partition for model selection...")
    val_metrics: Dict[str, Dict[str, Any]] = {}
    val_predictions: Dict[str, List[float]] = {}

    for name, model in models.items():
        if name in ("RidgeRegression_alpha50",):
            preds = model.predict(X_val_scaled)
        elif name in ("TwoStageHurdleModel",):
            preds = model.predict(X_val_raw, X_val_scaled)
        else:
            preds = model.predict(X_val_raw)

        val_predictions[name] = preds
        val_metrics[name] = evaluate_predictions(y_val, preds, dates=dates_val)

    # Select best model based on lowest Validation MAE (primary) and RMSE (secondary)
    candidate_names = [
        "RidgeRegression_alpha50",
        "DecisionTreeRegressor",
        "RandomForestRegressor",
        "TwoStageHurdleModel",
    ]
    best_candidate_name = min(
        candidate_names,
        key=lambda n: (val_metrics[n]["mae"], val_metrics[n]["rmse"])
    )
    logger.info(
        f"Selected Best Candidate on Validation: '{best_candidate_name}' "
        f"(Val MAE: ${val_metrics[best_candidate_name]['mae']:,.2f}, "
        f"Val RMSE: ${val_metrics[best_candidate_name]['rmse']:,.2f})."
    )

    # 8. Evaluate All Models on Final Holdout Test Partition
    logger.info("Evaluating all candidate models on final holdout test partition...")
    test_metrics: Dict[str, Dict[str, Any]] = {}
    test_predictions: Dict[str, List[float]] = {}

    for name, model in models.items():
        if name in ("RidgeRegression_alpha50",):
            preds = model.predict(X_test_scaled)
        elif name in ("TwoStageHurdleModel",):
            preds = model.predict(X_test_raw, X_test_scaled)
        else:
            preds = model.predict(X_test_raw)

        test_predictions[name] = preds
        test_metrics[name] = evaluate_predictions(y_test, preds, dates=dates_test)

    # 9. Save Artifacts & Predictions
    best_model = models[best_candidate_name]
    model_artifact_path = os.path.join(artifacts_dir, "best_sales_model.json")
    model_metadata = {
        "model_name": best_candidate_name,
        "selected_on": "Validation Partition (2025-07-01 to 2025-09-30)",
        "selection_criteria": "Lowest Validation MAE",
        "train_date_range": [dates_train[0], dates_train[-1]],
        "val_date_range": [dates_val[0], dates_val[-1]],
        "test_date_range": [dates_test[0], dates_test[-1]],
        "random_state": seed,
        "feature_names": feature_names,
        "validation_metrics": val_metrics[best_candidate_name],
        "test_metrics": test_metrics[best_candidate_name],
        "created_at": datetime.now().isoformat(),
        "database_file": db_file,
    }
    save_model_artifact(best_model, model_artifact_path, metadata=model_metadata)

    # Save Scaler Artifact
    scaler_artifact_path = os.path.join(artifacts_dir, "feature_scaler.json")
    with open(scaler_artifact_path, "w", encoding="utf-8") as f:
        json.dump(scaler.to_dict(), f, indent=2)

    # Save Comparison Summary
    summary_path = os.path.join(artifacts_dir, "sales_forecast_comparison.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "best_model_name": best_candidate_name,
                "metadata": model_metadata,
                "validation_results": val_metrics,
                "test_results": test_metrics,
            },
            f,
            indent=2,
        )

    # Save Predictions CSV
    predictions_csv_path = os.path.join(artifacts_dir, "test_predictions.csv")
    csv_headers = ["date", "actual_revenue"] + list(models.keys())
    with open(predictions_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        for i, d in enumerate(dates_test):
            row = [d, y_test[i]] + [test_predictions[m_name][i] for m_name in models.keys()]
            writer.writerow(row)

    logger.info(f"[OK] Artifacts successfully exported to: {artifacts_dir}")

    return {
        "selected_model": best_candidate_name,
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "artifacts": {
            "model_json": model_artifact_path,
            "scaler_json": scaler_artifact_path,
            "comparison_json": summary_path,
            "predictions_csv": predictions_csv_path,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate sales forecasting models.")
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite database")
    parser.add_argument("--artifacts-dir", type=str, default=None, help="Directory to save artifacts")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    results = run_experimentation_pipeline(
        db_path=args.db,
        artifacts_dir=args.artifacts_dir,
        seed=args.seed,
    )

    print("\n" + "=" * 80)
    print("PHASE 6B: SALES FORECASTING MODEL EXPERIMENT RESULTS")
    print("=" * 80)
    print("\n--- 1. VALIDATION SET COMPARISON (MODEL SELECTION) ---")
    print(format_comparison_table(results["validation_metrics"]))

    print(f"\n--> BEST MODEL SELECTED ON VALIDATION: {results['selected_model']}")

    print("\n--- 2. FINAL HOLDOUT TEST SET EVALUATION (2025-10-01 to 2025-12-31) ---")
    print(format_comparison_table(results["test_metrics"]))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
