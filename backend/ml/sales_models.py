"""
IntelliOps AI — Sales Forecasting Model Architectures
Implements baseline, regularized linear, decision tree, random forest,
and two-stage hurdle forecasting models in pure Python with zero heavy dependencies.

All models:
- Enforce deterministic execution via random_state.
- Implement standard fit(X, y) and predict(X) APIs.
- Support safe JSON serialization without unsafe pickle dependencies.
"""

import math
import random
import json
import os
import statistics
from typing import Dict, Any, List, Optional, Tuple


# ------------------------------------------------------------------------------
# 1. Linear Algebra Helpers (Gauss-Jordan Inversion & Matrix Operations)
# ------------------------------------------------------------------------------

def _solve_linear_system(A: List[List[float]], b: List[float]) -> List[float]:
    """Solves A x = b using Gauss-Jordan elimination with partial pivoting."""
    n = len(A)
    # Augment A with b
    M = [A[i][:] + [b[i]] for i in range(n)]

    for col in range(n):
        # Pivot selection
        max_r = col
        max_v = abs(M[col][col])
        for r in range(col + 1, n):
            if abs(M[r][col]) > max_v:
                max_v = abs(M[r][col])
                max_r = r

        if max_v < 1e-12:
            raise ValueError(f"Matrix is singular or near-singular at column {col}.")

        M[col], M[max_r] = M[max_r], M[col]
        pivot = M[col][col]
        for c in range(n + 1):
            M[col][c] /= pivot

        for r in range(n):
            if r != col:
                factor = M[r][col]
                for c in range(n + 1):
                    M[r][c] -= factor * M[col][c]

    return [M[i][-1] for i in range(n)]


# ------------------------------------------------------------------------------
# 2. Baseline Models
# ------------------------------------------------------------------------------

class HistoricalMeanModel:
    """Predicts a constant historical training mean: y_hat = mean(y_train)."""

    def __init__(self):
        self.mean_value: float = 0.0
        self.name: str = "HistoricalMeanBaseline"

    def fit(self, X: List[List[float]], y: List[float]) -> "HistoricalMeanModel":
        if not y:
            raise ValueError("HistoricalMeanModel requires at least one target value to fit.")
        self.mean_value = float(statistics.mean(y))
        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        return [self.mean_value] * len(X)

    def to_dict(self) -> Dict[str, Any]:
        return {"model_type": self.name, "mean_value": self.mean_value}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoricalMeanModel":
        model = cls()
        model.mean_value = data["mean_value"]
        return model


class RollingMeanModel:
    """Predicts the shifted 7-day rolling mean extracted from features (roll_mean_7)."""

    def __init__(self, roll_feature_idx: int = 11):
        self.roll_feature_idx = roll_feature_idx
        self.name: str = "RollingMeanBaseline"

    def fit(self, X: List[List[float]], y: List[float]) -> "RollingMeanModel":
        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        return [max(0.0, float(row[self.roll_feature_idx])) for row in X]

    def to_dict(self) -> Dict[str, Any]:
        return {"model_type": self.name, "roll_feature_idx": self.roll_feature_idx}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RollingMeanModel":
        return cls(roll_feature_idx=data.get("roll_feature_idx", 11))


class PersistenceModel:
    """Predicts yesterday's actual value (lag 1)."""

    def __init__(self, lag_feature_idx: int = 6):
        self.lag_feature_idx = lag_feature_idx
        self.name: str = "NaivePersistenceBaseline"

    def fit(self, X: List[List[float]], y: List[float]) -> "PersistenceModel":
        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        return [max(0.0, float(row[self.lag_feature_idx])) for row in X]

    def to_dict(self) -> Dict[str, Any]:
        return {"model_type": self.name, "lag_feature_idx": self.lag_feature_idx}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersistenceModel":
        return cls(lag_feature_idx=data.get("lag_feature_idx", 6))


# ------------------------------------------------------------------------------
# 3. Ridge Regression Model
# ------------------------------------------------------------------------------

class RidgeRegressionModel:
    """
    Ridge (L2-Regularized) Linear Regression.
    Solves (X^T X + alpha * I) beta = X^T y.
    Intercept is not penalized.
    """

    def __init__(self, alpha: float = 50.0):
        self.alpha = float(alpha)
        self.intercept: float = 0.0
        self.weights: List[float] = []
        self.name: str = "RidgeRegression"

    def fit(self, X: List[List[float]], y: List[float]) -> "RidgeRegressionModel":
        if not X or not y:
            raise ValueError("Training data cannot be empty.")
        n_samples = len(X)
        n_features = len(X[0])

        # Augment with intercept column at index 0
        X_aug = [[1.0] + row for row in X]
        p = n_features + 1

        # Compute X^T X
        XTX = [[0.0] * p for _ in range(p)]
        for i in range(n_samples):
            row = X_aug[i]
            for j in range(p):
                val_j = row[j]
                for k in range(j, p):
                    val = val_j * row[k]
                    XTX[j][k] += val
                    if j != k:
                        XTX[k][j] += val

        # Add alpha regularization to diagonal (excluding intercept at j=0)
        for j in range(1, p):
            XTX[j][j] += self.alpha

        # Compute X^T y
        XTy = [0.0] * p
        for i in range(n_samples):
            row = X_aug[i]
            yi = y[i]
            for j in range(p):
                XTy[j] += row[j] * yi

        beta = _solve_linear_system(XTX, XTy)
        self.intercept = beta[0]
        self.weights = beta[1:]
        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        if not self.weights:
            raise RuntimeError("Model must be fitted before predict.")
        preds = []
        for row in X:
            val = self.intercept + sum(w * x for w, x in zip(self.weights, row))
            preds.append(max(0.0, float(val)))  # Revenue is non-negative
        return preds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.name,
            "alpha": self.alpha,
            "intercept": self.intercept,
            "weights": self.weights,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RidgeRegressionModel":
        model = cls(alpha=data.get("alpha", 50.0))
        model.intercept = data["intercept"]
        model.weights = data["weights"]
        return model


# ------------------------------------------------------------------------------
# 4. Decision Tree & Random Forest Regressors
# ------------------------------------------------------------------------------

class DecisionTreeRegressorModel:
    """Fast, deterministic regression tree minimizing mean squared error."""

    def __init__(self, max_depth: int = 3, min_samples_split: int = 15):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.tree: Optional[Dict[str, Any]] = None
        self.name: str = "DecisionTreeRegressor"

    def fit(self, X: List[List[float]], y: List[float], feature_indices: Optional[List[int]] = None) -> "DecisionTreeRegressorModel":
        if feature_indices is None:
            feature_indices = list(range(len(X[0])))
        self.tree = self._build_node(X, y, depth=0, feature_indices=feature_indices)
        return self

    def _build_node(self, X: List[List[float]], y: List[float], depth: int, feature_indices: List[int]) -> Dict[str, Any]:
        n_samples = len(y)
        if n_samples == 0:
            return {"leaf": True, "value": 0.0}

        mean_val = statistics.mean(y)
        if depth >= self.max_depth or n_samples < self.min_samples_split:
            return {"leaf": True, "value": mean_val}

        best_feat = None
        best_thresh = None
        best_score = float("inf")
        best_splits = None

        for f_idx in feature_indices:
            vals = [row[f_idx] for row in X]
            sorted_v = sorted(set(vals))
            if len(sorted_v) <= 1:
                continue

            step = max(1, len(sorted_v) // 10)
            thresholds = [sorted_v[k] for k in range(0, len(sorted_v), step)]

            for th in thresholds:
                left_idx = [k for k in range(n_samples) if X[k][f_idx] <= th]
                right_idx = [k for k in range(n_samples) if X[k][f_idx] > th]
                if len(left_idx) < 4 or len(right_idx) < 4:
                    continue

                left_y = [y[k] for k in left_idx]
                right_y = [y[k] for k in right_idx]

                mean_l = statistics.mean(left_y)
                mean_r = statistics.mean(right_y)
                mse_l = sum((val - mean_l) ** 2 for val in left_y)
                mse_r = sum((val - mean_r) ** 2 for val in right_y)
                score = mse_l + mse_r

                if score < best_score:
                    best_score = score
                    best_feat = f_idx
                    best_thresh = th
                    best_splits = (
                        [X[k] for k in left_idx], left_y,
                        [X[k] for k in right_idx], right_y,
                    )

        if best_feat is None:
            return {"leaf": True, "value": mean_val}

        left_X, left_y, right_X, right_y = best_splits
        return {
            "leaf": False,
            "feature": best_feat,
            "threshold": best_thresh,
            "left": self._build_node(left_X, left_y, depth + 1, feature_indices),
            "right": self._build_node(right_X, right_y, depth + 1, feature_indices),
        }

    def _predict_one(self, row: List[float], node: Dict[str, Any]) -> float:
        if node["leaf"]:
            return float(node["value"])
        if row[node["feature"]] <= node["threshold"]:
            return self._predict_one(row, node["left"])
        else:
            return self._predict_one(row, node["right"])

    def predict(self, X: List[List[float]]) -> List[float]:
        if self.tree is None:
            raise RuntimeError("Model must be fitted before predict.")
        return [max(0.0, self._predict_one(row, self.tree)) for row in X]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.name,
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "tree": self.tree,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionTreeRegressorModel":
        model = cls(max_depth=data.get("max_depth", 3), min_samples_split=data.get("min_samples_split", 15))
        model.tree = data["tree"]
        return model


class RandomForestRegressorModel:
    """Ensemble of regression trees with bootstrap sampling and feature subsampling."""

    def __init__(
        self,
        n_estimators: int = 15,
        max_depth: int = 4,
        min_samples_split: int = 10,
        max_features: int = 8,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.max_features = max_features
        self.random_state = random_state
        self.trees: List[DecisionTreeRegressorModel] = []
        self.name: str = "RandomForestRegressor"

    def fit(self, X: List[List[float]], y: List[float]) -> "RandomForestRegressorModel":
        rng = random.Random(self.random_state)
        n_samples = len(X)
        n_features = len(X[0])
        self.trees = []

        for _ in range(self.n_estimators):
            boot_idx = [rng.randint(0, n_samples - 1) for _ in range(n_samples)]
            boot_X = [X[idx] for idx in boot_idx]
            boot_y = [y[idx] for idx in boot_idx]
            sub_feats = rng.sample(list(range(n_features)), min(self.max_features, n_features))

            tree = DecisionTreeRegressorModel(max_depth=self.max_depth, min_samples_split=self.min_samples_split)
            tree.fit(boot_X, boot_y, feature_indices=sub_feats)
            self.trees.append(tree)

        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        if not self.trees:
            raise RuntimeError("Model must be fitted before predict.")
        all_tree_preds = [t.predict(X) for t in self.trees]
        n_samples = len(X)
        final_preds = []
        for i in range(n_samples):
            avg_p = statistics.mean([all_tree_preds[t_idx][i] for t_idx in range(len(self.trees))])
            final_preds.append(max(0.0, float(avg_p)))
        return final_preds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.name,
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "max_features": self.max_features,
            "random_state": self.random_state,
            "trees": [t.to_dict() for t in self.trees],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RandomForestRegressorModel":
        model = cls(
            n_estimators=data.get("n_estimators", 15),
            max_depth=data.get("max_depth", 4),
            min_samples_split=data.get("min_samples_split", 10),
            max_features=data.get("max_features", 8),
            random_state=data.get("random_state", 42),
        )
        model.trees = [DecisionTreeRegressorModel.from_dict(t) for t in data["trees"]]
        return model


# ------------------------------------------------------------------------------
# 5. Two-Stage Hurdle Model
# ------------------------------------------------------------------------------

class TwoStageHurdleModel:
    """
    Two-Stage Hurdle Model for Zero-Inflated Daily Revenue:
    - Stage A: Predicts probability of non-zero revenue P(y_t > 0 | X_t).
    - Stage B: Predicts positive revenue magnitude E[y_t | y_t > 0, X_t].
    - Combined Expected Value: y_hat = P(y_t > 0) * E[y_t | y_t > 0].
    """

    def __init__(self, alpha_ridge: float = 50.0, random_state: int = 42):
        self.alpha_ridge = alpha_ridge
        self.random_state = random_state
        self.classifier = RandomForestRegressorModel(n_estimators=10, max_depth=3, random_state=random_state)
        self.regressor = RidgeRegressionModel(alpha=alpha_ridge)
        self.name: str = "TwoStageHurdleModel"

    def fit(self, X_raw: List[List[float]], y_raw: List[float], X_scaled: List[List[float]]) -> "TwoStageHurdleModel":
        # Stage A: Binary label (1.0 for positive sales, 0.0 for zero sales)
        y_binary = [1.0 if val > 0.0 else 0.0 for val in y_raw]
        self.classifier.fit(X_raw, y_binary)

        # Stage B: Fit regressor only on positive sales dates
        pos_indices = [i for i, val in enumerate(y_raw) if val > 0.0]
        pos_X = [X_scaled[i] for i in pos_indices]
        pos_y = [y_raw[i] for i in pos_indices]
        self.regressor.fit(pos_X, pos_y)
        return self

    def predict(self, X_raw: List[List[float]], X_scaled: List[List[float]]) -> List[float]:
        # Stage A estimated probabilities (clipped between 0.0 and 1.0)
        raw_probs = self.classifier.predict(X_raw)
        probs = [max(0.0, min(1.0, p)) for p in raw_probs]

        # Stage B expected positive revenues
        pos_preds = self.regressor.predict(X_scaled)

        # Combined expectation: E[Y] = P(Y > 0) * E[Y | Y > 0]
        return [max(0.0, round(p * y_pos, 2)) for p, y_pos in zip(probs, pos_preds)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.name,
            "alpha_ridge": self.alpha_ridge,
            "random_state": self.random_state,
            "classifier": self.classifier.to_dict(),
            "regressor": self.regressor.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TwoStageHurdleModel":
        model = cls(alpha_ridge=data.get("alpha_ridge", 50.0), random_state=data.get("random_state", 42))
        model.classifier = RandomForestRegressorModel.from_dict(data["classifier"])
        model.regressor = RidgeRegressionModel.from_dict(data["regressor"])
        return model


# ------------------------------------------------------------------------------
# 6. Model Serialization & Deserialization
# ------------------------------------------------------------------------------

def save_model_artifact(model: Any, filepath: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Safely serializes a model and its metadata into clean JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    payload = {
        "metadata": metadata or {},
        "model_data": model.to_dict(),
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return filepath


def load_model_artifact(filepath: str) -> Tuple[Any, Dict[str, Any]]:
    """Safely deserializes a model artifact from JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)

    model_data = payload["model_data"]
    model_type = model_data.get("model_type")

    if model_type == "HistoricalMeanBaseline":
        model = HistoricalMeanModel.from_dict(model_data)
    elif model_type == "RollingMeanBaseline":
        model = RollingMeanModel.from_dict(model_data)
    elif model_type == "NaivePersistenceBaseline":
        model = PersistenceModel.from_dict(model_data)
    elif model_type == "RidgeRegression":
        model = RidgeRegressionModel.from_dict(model_data)
    elif model_type == "DecisionTreeRegressor":
        model = DecisionTreeRegressorModel.from_dict(model_data)
    elif model_type == "RandomForestRegressor":
        model = RandomForestRegressorModel.from_dict(model_data)
    elif model_type == "TwoStageHurdleModel":
        model = TwoStageHurdleModel.from_dict(model_data)
    else:
        raise ValueError(f"Unknown model_type '{model_type}' in {filepath}.")

    return model, payload.get("metadata", {})
