"""
IntelliOps AI — Machine Learning Subsystem
Module for data preparation, time-series forecasting, and model evaluation.
"""

from .prepare_sales_data import (
    extract_daily_sales_revenue,
    extract_daily_units_sold,
    run_sales_audit,
    export_prepared_datasets,
    resolve_db_path,
)
from .sales_features import (
    build_feature_dataset,
    TimeSeriesScaler,
    verify_feature_leakage,
    FEATURE_NAMES,
)
from .sales_models import (
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
from .evaluate_sales_forecast import (
    evaluate_predictions,
    format_comparison_table,
)
from .train_sales_forecast import (
    run_experimentation_pipeline,
)

__all__ = [
    "extract_daily_sales_revenue",
    "extract_daily_units_sold",
    "run_sales_audit",
    "export_prepared_datasets",
    "resolve_db_path",
    "build_feature_dataset",
    "TimeSeriesScaler",
    "verify_feature_leakage",
    "FEATURE_NAMES",
    "HistoricalMeanModel",
    "RollingMeanModel",
    "PersistenceModel",
    "RidgeRegressionModel",
    "DecisionTreeRegressorModel",
    "RandomForestRegressorModel",
    "TwoStageHurdleModel",
    "save_model_artifact",
    "load_model_artifact",
    "evaluate_predictions",
    "format_comparison_table",
    "run_experimentation_pipeline",
]
