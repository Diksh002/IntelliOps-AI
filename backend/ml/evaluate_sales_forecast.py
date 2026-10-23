"""
IntelliOps AI — Sales Forecast Evaluation & Metrics Module
Computes robust, leak-free evaluation metrics for time-series forecasting models:
- Mean Absolute Error (MAE) - Primary business dollar metric
- Root Mean Squared Error (RMSE) - Penalizes large errors
- Coefficient of Determination (R-squared) with careful interpretation
- Error breakdown on zero-sales vs positive-sales dates
- MAPE strictly on nonzero actual sales dates (division-by-zero protected)
- Prediction bias and systematic directional error
"""

import math
import statistics
from typing import Dict, Any, List, Optional


def evaluate_predictions(
    actuals: List[float],
    preds: List[float],
    dates: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Evaluates forecast predictions against actual ground truth values.

    Args:
        actuals: Ground truth sales revenue values.
        preds: Forecasted sales revenue values.
        dates: Optional list of corresponding calendar dates (YYYY-MM-DD).

    Returns:
        Structured evaluation metrics dictionary.
    """
    if not actuals or not preds:
        raise ValueError("Actuals and predictions must not be empty.")
    if len(actuals) != len(preds):
        raise ValueError(f"Length mismatch: {len(actuals)} actuals vs {len(preds)} predictions.")

    n = len(actuals)
    mae = statistics.mean([abs(a - p) for a, p in zip(actuals, preds)])
    rmse = math.sqrt(statistics.mean([(a - p) ** 2 for a, p in zip(actuals, preds)]))

    # Mean and R^2
    mean_actual = statistics.mean(actuals)
    ss_tot = sum((a - mean_actual) ** 2 for a in actuals)
    ss_res = sum((a - p) ** 2 for a, p in zip(actuals, preds))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-9 else 0.0

    # Error on zero vs positive sales dates
    zero_pairs = [(a, p) for a, p in zip(actuals, preds) if a == 0.0]
    pos_pairs = [(a, p) for a, p in zip(actuals, preds) if a > 0.0]

    mae_zero = statistics.mean([abs(a - p) for a, p in zero_pairs]) if zero_pairs else 0.0
    mae_pos = statistics.mean([abs(a - p) for a, p in pos_pairs]) if pos_pairs else 0.0

    # MAPE strictly on positive actual sales (protected against division by zero)
    if pos_pairs:
        mape_nonzero = statistics.mean([abs(a - p) / a for a, p in pos_pairs]) * 100.0
    else:
        mape_nonzero = 0.0

    # Directional Prediction Bias (mean(pred - actual))
    bias = statistics.mean([p - a for a, p in zip(actuals, preds)])

    actual_std = statistics.stdev(actuals) if n > 1 else 0.0
    pred_mean = statistics.mean(preds)
    pred_std = statistics.stdev(preds) if n > 1 else 0.0

    return {
        "total_evaluated_dates": n,
        "zero_sales_dates_count": len(zero_pairs),
        "positive_sales_dates_count": len(pos_pairs),
        "start_date": dates[0] if dates else None,
        "end_date": dates[-1] if dates else None,
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
        "mae_zero_sales_days": round(mae_zero, 2),
        "mae_positive_sales_days": round(mae_pos, 2),
        "mape_nonzero_sales_days": round(mape_nonzero, 2),
        "bias": round(bias, 2),
        "actual_mean": round(mean_actual, 2),
        "actual_std": round(actual_std, 2),
        "predicted_mean": round(pred_mean, 2),
        "predicted_std": round(pred_std, 2),
        "mape_notice": (
            "MAPE is mathematically undefined on zero-sales dates due to division by zero. "
            "Reported MAPE is strictly calculated across dates with actual revenue > 0."
        ),
    }


def format_comparison_table(results_by_model: Dict[str, Dict[str, Any]], baseline_key: str = "HistoricalMeanBaseline") -> str:
    """Formats a GitHub-flavored Markdown comparison table with baseline delta."""
    header = (
        "| Model Name | MAE ($) | RMSE ($) | R² | MAE (Zero Days) | MAE (Pos Days) | MAPE (Pos %) | Bias ($) | vs Baseline MAE |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    )

    baseline_mae = results_by_model.get(baseline_key, {}).get("mae", 1.0)
    rows = []

    for model_name, metrics in results_by_model.items():
        mae = metrics["mae"]
        rmse = metrics["rmse"]
        r2 = metrics["r2"]
        mae_zero = metrics["mae_zero_sales_days"]
        mae_pos = metrics["mae_positive_sales_days"]
        mape_pos = metrics["mape_nonzero_sales_days"]
        bias = metrics["bias"]

        if model_name == baseline_key:
            delta_str = "Baseline"
        else:
            diff = mae - baseline_mae
            pct_diff = (diff / baseline_mae) * 100.0 if baseline_mae > 0 else 0.0
            sign = "+" if diff > 0 else ""
            delta_str = f"{sign}${diff:,.2f} ({sign}{pct_diff:.1f}%)"

        row = (
            f"| **{model_name}** | ${mae:,.2f} | ${rmse:,.2f} | {r2:+.4f} | "
            f"${mae_zero:,.2f} | ${mae_pos:,.2f} | {mape_pos:.1f}% | ${bias:+,.2f} | {delta_str} |"
        )
        rows.append(row)

    return header + "\n".join(rows)
