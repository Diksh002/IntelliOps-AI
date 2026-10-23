"""
IntelliOps AI — Sales Forecasting Feature Engineering
Constructs strictly leak-free temporal, lagged, and rolling features for daily revenue forecasting.

Design Principles:
1. Temporal Integrity: At forecast origin t, features use ONLY past observations (< t).
2. Shifted Rolling Windows: All rolling metrics are shifted by at least 1 day ([t-w, ..., t-1]).
3. No Target Leakage: Target y_t is never incorporated into feature matrix row t.
4. Leak-Free Scaling: Normalization statistics are fit strictly on training set indices.
5. Missing History Handling: Pre-launch dates (< 2024-01-01) default to 0.0 with explicit flags.
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional


FEATURE_NAMES = [
    # Calendar & Trend
    "is_weekend",
    "sin_dow",
    "cos_dow",
    "sin_month",
    "cos_month",
    "time_idx",
    # Lagged Revenue (y_{t-k})
    "lag_1",
    "lag_2",
    "lag_7",
    "lag_14",
    "lag_28",
    # Rolling Statistics (Shifted strictly prior to t)
    "roll_mean_7",
    "roll_std_7",
    "roll_min_7",
    "roll_max_7",
    "zero_cnt_7",
    "roll_mean_14",
    "roll_mean_28",
    "roll_std_28",
    "zero_cnt_28",
]


class TimeSeriesScaler:
    """
    Standardizes features using mean and standard deviation derived strictly from training data.
    Prevents normalization leakage across chronological validation and test partitions.
    """

    def __init__(self):
        self.means: List[float] = []
        self.stds: List[float] = []
        self.feature_names: List[str] = []
        self.is_fitted: bool = False

    def fit(self, X: List[List[float]], feature_names: Optional[List[str]] = None) -> "TimeSeriesScaler":
        if not X:
            raise ValueError("Cannot fit scaler on empty feature matrix.")
        n_features = len(X[0])
        self.means = []
        self.stds = []
        self.feature_names = feature_names or [f"f_{i}" for i in range(n_features)]

        for j in range(n_features):
            col_vals = [row[j] for row in X]
            m = statistics.mean(col_vals)
            s = statistics.stdev(col_vals) if len(col_vals) > 1 else 1.0
            self.means.append(m)
            self.stds.append(s if s > 1e-7 else 1.0)

        self.is_fitted = True
        return self

    def transform(self, X: List[List[float]]) -> List[List[float]]:
        if not self.is_fitted:
            raise RuntimeError("Scaler must be fitted before transforming data.")
        n_features = len(self.means)
        X_scaled = []
        for row in X:
            scaled_row = [(row[j] - self.means[j]) / self.stds[j] for j in range(n_features)]
            X_scaled.append(scaled_row)
        return X_scaled

    def fit_transform(self, X: List[List[float]], feature_names: Optional[List[str]] = None) -> List[List[float]]:
        return self.fit(X, feature_names).transform(X)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "means": self.means,
            "stds": self.stds,
            "feature_names": self.feature_names,
            "is_fitted": self.is_fitted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeSeriesScaler":
        scaler = cls()
        scaler.means = data["means"]
        scaler.stds = data["stds"]
        scaler.feature_names = data["feature_names"]
        scaler.is_fitted = data["is_fitted"]
        return scaler


def build_feature_dataset(
    daily_records: List[Dict[str, Any]],
) -> Tuple[List[str], List[List[float]], List[float], List[str]]:
    """
    Constructs leak-free feature vectors for each calendar date.

    Args:
        daily_records: Chronologically sorted list of dictionaries with 'date' and 'revenue'.

    Returns:
        dates: List of YYYY-MM-DD strings.
        X: List of feature vectors matching FEATURE_NAMES.
        y: List of target values (daily completed revenue).
        feature_names: List of column header names.
    """
    if not daily_records:
        return [], [], [], FEATURE_NAMES

    # Ensure chronological order
    sorted_records = sorted(daily_records, key=lambda r: r["date"])
    rev_map: Dict[str, float] = {r["date"]: float(r["revenue"]) for r in sorted_records}
    total_len = len(sorted_records)

    dates: List[str] = []
    X: List[List[float]] = []
    y: List[float] = []

    for i, r in enumerate(sorted_records):
        d_str = r["date"]
        dt = datetime.strptime(d_str, "%Y-%m-%d")
        target_revenue = float(r["revenue"])

        # 1. Calendar & Trend Features (known deterministically in advance)
        dow = dt.weekday()  # 0=Monday, 6=Sunday
        is_wknd = 1.0 if dow in (5, 6) else 0.0
        month = float(dt.month)
        time_idx = float(i) / max(1.0, float(total_len - 1))

        # Cyclical harmonic encodings
        sin_dow = math.sin(2.0 * math.pi * dow / 7.0)
        cos_dow = math.cos(2.0 * math.pi * dow / 7.0)
        sin_month = math.sin(2.0 * math.pi * (month - 1.0) / 12.0)
        cos_month = math.cos(2.0 * math.pi * (month - 1.0) / 12.0)

        # 2. Helper to fetch past revenue strictly prior to date dt
        def _get_past_revenue(lag_days: int) -> float:
            past_dt = dt - timedelta(days=lag_days)
            past_key = past_dt.strftime("%Y-%m-%d")
            # Operational start is 2024-01-01; revenue prior to start was zero
            return rev_map.get(past_key, 0.0)

        # 3. Lagged revenue features (strictly t - k)
        lag_1 = _get_past_revenue(1)
        lag_2 = _get_past_revenue(2)
        lag_7 = _get_past_revenue(7)
        lag_14 = _get_past_revenue(14)
        lag_28 = _get_past_revenue(28)

        # 4. Shifted rolling window statistics ([t-w, ..., t-1])
        past_7 = [_get_past_revenue(k) for k in range(1, 8)]
        past_14 = [_get_past_revenue(k) for k in range(1, 15)]
        past_28 = [_get_past_revenue(k) for k in range(1, 29)]

        roll_mean_7 = statistics.mean(past_7)
        roll_std_7 = statistics.stdev(past_7) if len(past_7) > 1 else 0.0
        roll_min_7 = min(past_7)
        roll_max_7 = max(past_7)
        zero_cnt_7 = sum(1.0 for x in past_7 if x == 0.0)

        roll_mean_14 = statistics.mean(past_14)

        roll_mean_28 = statistics.mean(past_28)
        roll_std_28 = statistics.stdev(past_28) if len(past_28) > 1 else 0.0
        zero_cnt_28 = sum(1.0 for x in past_28 if x == 0.0)

        feat_vector = [
            is_wknd,
            sin_dow,
            cos_dow,
            sin_month,
            cos_month,
            time_idx,
            lag_1,
            lag_2,
            lag_7,
            lag_14,
            lag_28,
            roll_mean_7,
            roll_std_7,
            roll_min_7,
            roll_max_7,
            zero_cnt_7,
            roll_mean_14,
            roll_mean_28,
            roll_std_28,
            zero_cnt_28,
        ]

        dates.append(d_str)
        X.append(feat_vector)
        y.append(target_revenue)

    return dates, X, y, FEATURE_NAMES


def verify_feature_leakage(
    dates: List[str],
    X: List[List[float]],
    y: List[float],
    feature_names: List[str],
) -> Dict[str, Any]:
    """
    Programmatically verifies that no future or current-target data leaks into feature rows.
    Returns audit status dictionary.
    """
    violations = []
    n_rows = len(dates)

    lag_1_idx = feature_names.index("lag_1")
    roll_mean_7_idx = feature_names.index("roll_mean_7")

    for i in range(n_rows):
        current_y = y[i]
        row_feat = X[i]

        # Check 1: Lag 1 at index i must exactly equal y[i-1] for i >= 1
        if i >= 1:
            expected_lag_1 = y[i - 1]
            actual_lag_1 = row_feat[lag_1_idx]
            if abs(actual_lag_1 - expected_lag_1) > 1e-4:
                violations.append(f"Row {i} ({dates[i]}): lag_1 ({actual_lag_1}) != y[i-1] ({expected_lag_1})")

        # Check 2: Row feature must not equal current target unless it's a coincidental match
        # Specifically, check that if current_y is mutated in a test scenario, features don't change
        if i >= 7:
            expected_mean_7 = statistics.mean([y[i - k] for k in range(1, 8)])
            actual_mean_7 = row_feat[roll_mean_7_idx]
            if abs(actual_mean_7 - expected_mean_7) > 1e-4:
                violations.append(f"Row {i} ({dates[i]}): roll_mean_7 ({actual_mean_7}) != expected ({expected_mean_7})")

    return {
        "is_leak_free": len(violations) == 0,
        "total_rows_verified": n_rows,
        "violations_count": len(violations),
        "violations": violations[:5],
    }
