# IntelliOps AI — Sales Forecasting Data Audit & Preparation Specification
**Document Version:** 1.0.0 (Phase 6A Deliverable)  
**Target Platform:** IntelliOps AI (DataScout)  
**Location:** `c:\DayScout`  
**Status:** Completed, Validated, and Verified  

---

## 1. Executive Summary

Phase 6A establishes a reliable, deterministic, and audited data foundation for future sales forecasting machine learning models within **IntelliOps AI**. This deliverable performs a thorough data audit, formulates an exact business revenue definition, implements reproducible time-series extraction pipelines, documents statistical forecastability characteristics, and designs a leak-free chronological validation strategy.

### Key Deliverables:
- **`backend/ml/prepare_sales_data.py`**: Portable, deterministic ETL and audit pipeline with strictly read-only database connections (`mode=ro` and `PRAGMA query_only = ON;`).
- **`backend/ml/__init__.py`**: Python package export exposing high-level data extraction and audit functions.
- **`backend/tests/test_sales_data_preparation.py`**: 14 automated unit tests utilizing isolated temporary databases.
- **`backend/ml/artifacts/`**: Generated CSV and JSON time-series datasets and audit logs (excluded from version control via `.gitignore`).
- **`docs/SALES_FORECASTING_DATA.md`**: This comprehensive specification.
- **`docs/PHASE_6A_REPORT.md`**: Formal delivery report and Phase 6B recommendations.

---

## 2. Forecasting Target Definition

### 2.1 Primary Target: Daily Completed-Order Revenue
The primary forecasting target is **daily completed-order revenue** ($Y_t$):

$$\text{Daily Completed Revenue}_t = \sum_{o \in \text{Orders}_t \mid \text{status} = \text{'completed'}} o.\text{total\_amount}$$

#### Exact Revenue Inclusion Criteria:
1. **Status Filtering**:
   - **`completed` (Included)**: 930 orders totaling **$31,822,832.40** (subtotal: $29,237,297.50, tax: $2,597,234.90, discount: $11,700.00). These represent realized commercial transactions with successful payments.
   - **`cancelled` (Excluded)**: 34 orders totaling $1,183,096.25. The associated payment status in `payments` is `failed`. Counting cancelled orders would artificially inflate actual revenue.
   - **`refunded` (Excluded)**: 20 orders totaling $769,755.45. In the database, refunded orders record both an initial completed payment and an identical offsetting refund payment (`status = 'refunded'`), resulting in net cash collected of $0.00. Including refunded orders would overstate net revenue.
   - **`pending` (Excluded)**: 0 orders currently in database (enforced by schema domain check `CHECK(status IN ('completed', 'pending', 'cancelled', 'refunded'))`). Unfinalized orders must not be recorded as recognized revenue.

2. **Prevention of One-to-Many Join Multiplication (Cartesian Explosion)**:
   - An order contains multiple items in `order_items` (1,649 item lines across 984 orders; average 1.68 items per order).
   - If an engineer joins `orders` and `order_items` and sums `orders.total_amount`, the order's total amount is duplicated across every line item row.
   - In our empirical audit, summing `orders.total_amount` after joining with `order_items` produced **$68,324,532.11**—an erroneous **114.7% overstatement** of actual revenue ($31,822,832.40).
   - The extraction pipeline computes daily revenue directly from `orders.total_amount` without joining line items.

3. **Currency Representation & Limitations**:
   - Monies in `orders`, `order_items`, `payments`, and `products` are stored as floating-point `REAL` values without an explicit ISO currency code column.
   - All transactions implicitly use a uniform base currency (USD).
   - Regional tax variations exist (e.g., NA at 6%, EMEA at 19%, APAC/LATAM at 0%), but no exchange-rate conversions are performed or stored.

### 2.2 Secondary Target: Daily Units Sold (Independent Target)
To support inventory and supply-chain planning, a separate target is prepared:

$$\text{Daily Units Sold}_t = \sum_{oi \in \text{OrderItems}_t \mid oi.\text{order}.\text{status} = \text{'completed'}} oi.\text{quantity}$$

- **Catalog Total**: 2,686 total units across 1,559 completed order item lines.
- **Separation Guarantee**: Units sold and revenue are **never combined** into a single hybrid metric. They are emitted into separate target columns and independent artifact files (`daily_units_sold.csv` and `daily_sales_revenue.csv`).

---

## 3. Dataset Characteristics & Audit Findings

The audit was executed against the operational database (`backend/datascout.db`) using `backend/ml/prepare_sales_data.py`.

### 3.1 Date Range & Zero Inflation
| Metric | Value | Interpretation |
| :--- | :--- | :--- |
| **Operational Calendar Start** | 2024-01-01 | Baseline platform launch date |
| **Operational Calendar End** | 2025-12-31 | Current dataset horizon |
| **Total Calendar Days** | **731 days** | Inclusive continuous calendar (366 days in 2024 leap year + 365 days in 2025) |
| **First Observed Order Date** | 2024-01-22 | First transaction recorded |
| **Last Observed Order Date** | 2025-12-31 | Final transaction recorded |
| **Active Sales Days** | **466 days** (63.75%) | Calendar days with $\ge 1$ completed order |
| **Zero-Sales Days** | **265 days** (**36.25%**) | Days with zero completed sales |

### 3.2 Statistical Distribution of Daily Revenue

| Statistic | Full Series (731 Days, with Zeros) | Active Days Only (466 Days) |
| :--- | :--- | :--- |
| **Total Revenue** | $31,822,832.40 | $31,822,832.40 |
| **Mean** | $43,533.29 | $68,289.34 |
| **Median** | $18,570.00 | $48,141.75 |
| **Standard Deviation** | $62,651.86 | $66,843.24 |
| **Coefficient of Variation** | 1.44 (High dispersion) | 0.98 |
| **Minimum** | $0.00 | $2,201.50 |
| **25th Percentile (Q1)** | $0.00 | $23,432.50 |
| **75th Percentile (Q3)** | $63,670.30 | $91,960.00 |
| **Interquartile Range (IQR)**| $63,670.30 | $68,527.50 |
| **Maximum** | $428,281.00 | $428,281.00 |

### 3.3 Outlier Analysis (Tukey's Fences)
- **Mild Outlier Threshold** ($Q3 + 1.5 \times \text{IQR}$): **$159,175.75** $\rightarrow$ **44 days (6.0%)**
- **Extreme Outlier Threshold** ($Q3 + 3.0 \times \text{IQR}$): **$254,681.20** $\rightarrow$ **12 days (1.6%)**

Top 5 Peak Revenue Dates:
1. `2025-08-07`: $428,281.00 (5 enterprise orders)
2. `2025-03-24`: $374,534.50 (6 enterprise orders)
3. `2025-08-01`: $357,987.50 (5 enterprise orders)
4. `2025-04-18`: $312,239.50 (4 enterprise orders)
5. `2025-03-18`: $299,692.00 (6 enterprise orders)

### 3.4 Monthly Revenue Progression
```
2024-01: $  118,452.15 (4 orders)   |  4 active / 31 days
2024-02: $   30,870.00 (2 orders)   |  2 active / 29 days
2024-03: $  220,424.00 (8 orders)   |  6 active / 31 days
2024-04: $   81,107.00 (4 orders)   |  4 active / 30 days
2024-05: $  575,998.00 (11 orders)  |  8 active / 31 days
2024-06: $  704,246.00 (22 orders)  | 14 active / 30 days
2024-07: $  845,068.50 (19 orders)  | 14 active / 31 days
2024-08: $1,228,993.50 (38 orders)  | 23 active / 31 days
2024-09: $1,395,928.50 (44 orders)  | 22 active / 30 days
2024-10: $1,327,909.00 (41 orders)  | 21 active / 31 days
2024-11: $  986,424.88 (29 orders)  | 16 active / 30 days
2024-12: $1,086,311.70 (39 orders)  | 24 active / 31 days
2025-01: $1,526,989.55 (43 orders)  | 25 active / 31 days
2025-02: $1,493,572.72 (41 orders)  | 21 active / 28 days
2025-03: $2,813,531.50 (63 orders)  | 27 active / 31 days
2025-04: $1,668,879.23 (55 orders)  | 25 active / 30 days
2025-05: $1,536,091.50 (47 orders)  | 27 active / 31 days
2025-06: $1,388,281.50 (48 orders)  | 21 active / 30 days
2025-07: $2,065,114.50 (62 orders)  | 28 active / 31 days
2025-08: $2,601,958.00 (71 orders)  | 29 active / 31 days
2025-09: $2,023,106.50 (67 orders)  | 27 active / 30 days
2025-10: $2,184,762.30 (58 orders)  | 25 active / 31 days
2025-11: $1,614,180.12 (55 orders)  | 26 active / 30 days
2025-12: $2,304,631.75 (59 orders)  | 27 active / 31 days
```

### 3.5 Day-of-Week Distribution (Seasonality Analysis)
| Day of Week | Mean Daily Revenue | Median Daily Revenue | Active Days | Total Days |
| :--- | :--- | :--- | :--- | :--- |
| **Monday** | $32,722.67 | $11,000.00 | 67 | 105 |
| **Tuesday** | $55,763.82 | $20,051.50 | 67 | 105 |
| **Wednesday** | $44,487.89 | $23,562.00 | 69 | 105 |
| **Thursday** | $42,645.40 | $18,885.00 | 68 | 104 |
| **Friday** | $38,841.19 | $13,223.00 | 63 | 104 |
| **Saturday** | $43,842.17 | $21,322.50 | 66 | 104 |
| **Sunday** | $46,407.02 | $19,543.25 | 66 | 104 |

**Key Finding**: In real enterprise B2B sales, transactions concentrate heavily during Monday–Friday business hours with steep weekend drop-offs. In this synthetic dataset, Saturday and Sunday exhibit active day counts (66/104) and mean revenues ($43.8k–$46.4k) that are virtually identical to weekdays. This is an artifact of uniform integer offset date generation (`order_dt = c_signup + timedelta(days=offset)`).

### 3.6 Autocorrelation Analysis
| Lag | Autocorrelation ($r$) | Interpretation |
| :--- | :--- | :--- |
| **Lag 1 (Day -1)** | **+0.1139** | Very weak day-to-day correlation; daily series behaves largely as white noise around a rising mean. |
| **Lag 2 (Day -2)** | **+0.0944** | Negligible persistence. |
| **Lag 7 (Week -1)** | **+0.1337** | **Absence of weekly seasonality.** No 7-day cyclical pattern. |
| **Lag 14 (Week -2)** | **+0.1894** | Slight positive drift reflecting quarterly volume increase. |
| **Lag 28 (Month -1)** | **+0.1745** | Weak monthly correlation. |
| **Lag 30 (Day -30)** | **+0.1139** | Weak monthly correlation. |
| **Lag 90 (Quarter -1)** | **+0.0886** | Negligible quarterly cycle. |

---

## 4. Synthetic Data Realities vs. Statistical Forecastability

> [!WARNING]
> **Synthetic Artifact vs. Macroeconomic Reality**:
> Machine learning models must not be expected to discover non-existent real-world signals.
> The apparent "growth trend" (from ~$118k in Jan 2024 to ~$2.3M in Dec 2025) is mathematically caused by the customer acquisition ramp:
> ```python
> signup_days = random.randint(0, 450)
> signup_dt = start_calendar + timedelta(days=signup_days)
> ```
> Customers were introduced uniformly over the first 450 days (Jan 2024 through March 2025). As the active customer pool expanded from 1 to 150 accounts, total daily order opportunities multiplied proportionally.

### Implications for Model Selection (Phase 6B):
1. **Classical ARIMA/SARIMA are Poor Fits**:
   - High zero inflation (36.25% zero days) violates the Gaussian residual assumptions of ARIMA.
   - Weak autocorrelation ($r < 0.15$ across all lags) means autoregressive lag terms will explain little daily variance.
2. **Intermittent / Zero-Inflated Models Recommended**:
   - **Two-Stage Hurdle Model**: Stage 1 predicts binary order probability ($P(\text{orders} > 0)$ via Logistic Regression or LightGBM classifier); Stage 2 predicts positive expected revenue given an order occurs (via Regressor with Tweedie / Log-Normal loss).
   - **Croston's Method / SBA (Syntetos-Boylan)**: Standard industrial benchmarks for intermittent demand.
   - **Feature-Based Regressors (LightGBM / XGBoost / Random Forest)**: Using customer cohort count, active campaign indicators, and rolling statistics (e.g., 14-day, 30-day moving averages).

---

## 5. Time-Series Validation Design (Chronological Splitting)

### 5.1 Strict Chronological Holdout Partitions
Random train/test splits (e.g. `train_test_split(shuffle=True)`) or standard K-Fold cross-validation **must never be used**. They cause catastrophic future information leakage into past predictions.

The dataset is partitioned chronologically:

```
[───────────────────── Training Set ─────────────────────] [─── Validation Set ───] [──── Holdout Test Set ────]
  2024-01-01 to 2025-06-30 (18 months, 547 calendar days)     2025-07-01 to 2025-09-30     2025-10-01 to 2025-12-31
              276 active days / 271 zero days                  (3 months, 92 days)          (3 months, 92 days)
                                                                84 active / 8 zero days      78 active / 14 zero days
```

1. **Training Partition** (2024-01-01 to 2025-06-30 | 547 days):
   - Used exclusively for model fitting and feature pipeline training.
   - Ground truth revenue: $14,028,874.98 | Mean daily: $25,646.94.
2. **Validation Partition** (2025-07-01 to 2025-09-30 | 92 days):
   - Used for model selection, feature engineering tuning, and hyperparameter optimization.
   - Ground truth revenue: $6,690,179.00 | Mean daily: $72,719.34.
3. **Holdout Test Partition** (2025-10-01 to 2025-12-31 | 92 days):
   - Reserved strictly for final unbiased evaluation in Phase 6B.
   - Ground truth revenue: $6,103,574.17 | Mean daily: $66,343.20 | StdDev: $76,590.97.

### 5.2 Benchmark Baseline Models (Holdout Test Set)

To prevent reporting deceptively impressive scores without context, every future candidate model in Phase 6B must be benchmarked against three canonical naive baselines on the holdout test period:

| Baseline Model | Formulation | MAE | RMSE | MAPE (Non-Zero Only)* |
| :--- | :--- | :--- | :--- | :--- |
| **1. Naive Persistence** | $\hat{y}_t = y_{t-1}$ (Yesterday's revenue) | **$87,178.54** | **$121,220.34** | **293.0%** |
| **2. 7-Day Rolling Window Mean** | $\hat{y}_t = \frac{1}{7} \sum_{i=1}^7 y_{t-i}$ | **$61,704.90** | **$83,059.62** | **254.2%** |
| **3. Historical Training Mean** | $\hat{y}_t = \bar{y}_{\text{train}} = \$25,646.94$ | **$52,408.36** | **$82,450.83** | **131.8%** |

#### Why Persistence Performs Poorly:
Due to high day-to-day volatility and 14 zero-sales days in the test partition, predicting yesterday's exact figure yields the worst performance (MAE: $87.1k, RMSE: $121.2k). A candidate ML model in Phase 6B **must achieve an MAE below $52,408.36 and RMSE below $82,450.83** to claim true value over simple historical mean heuristics.

### 5.3 Error Metrics & MAPE Limitations

> [!IMPORTANT]
> **Mathematical Limitations of MAPE**:
> Mean Absolute Percentage Error is formulated as:
> $$\text{MAPE} = \frac{100\%}{N} \sum_{t=1}^N \left| \frac{y_t - \hat{y}_t}{y_t} \right|$$
> When actual revenue $y_t = 0$ (which occurs on 14 days in the test partition and 265 days overall), the formula involves division by zero and is **mathematically undefined**.
> Even on low-sales days (e.g. $y_t = \$1,757.50$), a typical prediction error produces astronomical percentage errors (> 500%), distorting the metric.
> 
> **Evaluation Policy**:
> - **Primary Metric**: **Mean Absolute Error (MAE)** — robust linear loss matching business dollars.
> - **Secondary Metric**: **Root Mean Squared Error (RMSE)** — penalizes extreme forecast misses.
> - **MAPE Policy**: Reported **only on non-zero sales days**, accompanied by the zero-count notice.

---

## 6. Pipeline Commands & Artifacts

### 6.1 Running Data Preparation & Audit
From the repository root (`c:\DayScout`):

```powershell
# Run the statistical audit report in console
.\backend\venv\Scripts\python backend\ml\prepare_sales_data.py --audit

# Export prepared time-series datasets to backend/ml/artifacts
.\backend\venv\Scripts\python backend\ml\prepare_sales_data.py --export

# Custom database path and target output directory
.\backend\venv\Scripts\python backend\ml\prepare_sales_data.py --db backend\datascout.db --output-dir backend\ml\artifacts
```

### 6.2 Produced Artifacts (`backend/ml/artifacts/`)
1. **`daily_sales_revenue.csv`**:
   - Continuous daily time series (731 rows, 2024-01-01 through 2025-12-31).
   - Columns: `date`, `revenue`, `order_count`, `avg_order_value`, `min_order_value`, `max_order_value`.
2. **`daily_sales_revenue.json`**:
   - Structured JSON representation of the daily revenue series.
3. **`daily_units_sold.csv`**:
   - Daily quantities sold for completed orders (731 rows).
   - Columns: `date`, `units_sold`, `order_count`, `line_item_count`, `distinct_products_sold`.
4. **`daily_units_sold.json`**:
   - Structured JSON representation of the daily units sold series.
5. **`sales_data_audit.json`**:
   - Full diagnostic payload containing complete statistical distributions, day-of-week profiles, autocorrelations, monthly aggregations, and baseline benchmark scores.

---

## 7. Automated Test Suite

Run the full sales data preparation test suite:
```powershell
cd c:\DayScout\backend
.\venv\Scripts\python -m unittest tests/test_sales_data_preparation.py
```

### Coverage:
- `test_01_daily_aggregation_and_correct_totals`: Accurate multi-order daily summation and AOV.
- `test_02_excluding_cancelled_refunded_pending_orders`: Excludes non-completed orders.
- `test_03_no_revenue_double_counting`: Rejects 1-to-many Cartesian multiplication.
- `test_04_continuous_calendar_and_zero_sales_dates`: Guarantees contiguous dates and zero fills.
- `test_05_chronological_ordering`: Verifies strictly increasing date index.
- `test_06_empty_database_handling`: Graceful handling of empty databases.
- `test_07_missing_table_handling`: Graceful handling of missing `orders` table.
- `test_08_invalid_or_missing_order_dates`: Skips null and malformed date strings.
- `test_09_negative_or_corrupt_amounts_rejected`: Filters corrupted numeric values.
- `test_10_readonly_database_access`: Confirms write operations trigger read-only operational error.
- `test_11_deterministic_output`: Verifies reproducible, identical output runs.
- `test_12_daily_units_sold_independent`: Aggregates order item quantities independently.
- `test_13_export_artifacts`: Validates physical CSV and JSON exports.
- `test_14_audit_report_generation`: Validates presence of all diagnostic audit keys.
