# IntelliOps AI — Phase 6A Delivery Report
**Project Name:** IntelliOps AI (DataScout)  
**Deliverable:** Sales Forecasting Data Audit and Preparation (Phase 6A)  
**Location:** `c:\DayScout`  
**Date:** October 2026  
**Status:** Completed, Verified, and Ready for Review  

---

## 1. Executive Summary

Phase 6A is **DATA AUDIT AND PREPARATION ONLY**. No final models were trained, no frontend files were modified, existing application functionality was preserved without alteration, and the underlying database was accessed strictly read-only.

A comprehensive audit was performed across the 10 normalized tables in `backend/datascout.db`. We identified critical properties of the data, resolved a Cartesian revenue double-counting risk, established an audited target definition, implemented a deterministic ETL and audit pipeline in `backend/ml/`, and designed a leak-free chronological time-series evaluation strategy for Phase 6B.

All 49 unit and integration tests across the backend passed with a 100% success rate, and the FastAPI backend `/health` endpoint was verified operational.

---

## 2. Files Created or Modified

| File | Status | Description |
| :--- | :--- | :--- |
| **`backend/ml/__init__.py`** | *Created* | Exposes high-level data extraction, audit, and artifact generation functions. |
| **`backend/ml/prepare_sales_data.py`** | *Created* | Deterministic extraction and diagnostic audit pipeline with strictly read-only SQLite connections (`mode=ro` + `PRAGMA query_only = ON;`), CLI interface, and artifact export. |
| **`backend/tests/test_sales_data_preparation.py`** | *Created* | 14 automated unit tests verifying daily aggregation, status exclusion, join deduplication, continuous date index, error handling, read-only enforcement, and determinism using isolated temp databases. |
| **`backend/.gitignore`** | *Modified* | Added `ml/artifacts/` to prevent committing generated time-series data. |
| **`.gitignore`** | *Modified* | Added `backend/ml/artifacts/` at project root. |
| **`docs/SALES_FORECASTING_DATA.md`** | *Created* | Complete technical specification of target definitions, statistical characteristics, baseline benchmarks, and time-series validation architecture. |
| **`docs/PHASE_6A_REPORT.md`** | *Created* | This delivery report. |

---

## 3. Actual Data Quality Findings

### 3.1 Order Status Breakdown & Revenue Definitions
The operational SQLite database (`backend/datascout.db`) contains 984 orders. A full audit of order statuses revealed:

| Status | Order Count | Subtotal | Tax | Discount | Total Amount | Included in Completed Revenue? | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`completed`** | **930** | $29,237,297.50 | $2,597,234.90 | $11,700.00 | **$31,822,832.40** | **YES** | Legitimate commercial sales with completed settlement payments. |
| **`cancelled`** | **34** | $1,066,820.00 | $116,626.25 | $350.00 | **$1,183,096.25** | **NO** | Transactions aborted before fulfillment; payments recorded as `failed`. |
| **`refunded`** | **20** | $674,397.50 | $95,557.95 | $200.00 | **$769,755.45** | **NO** | Payments reversed with equal offsetting refund records (`net cash = $0.00`). |
| **`pending`** | **0** | $0.00 | $0.00 | $0.00 | **$0.00** | **NO** | None exist in database; unfinalized orders are not recognized revenue. |

### 3.2 Resolution of One-to-Many Join Trap (Cartesian Multiplication)
- In the normalized schema, each order in `orders` has 1 to 4 items in `order_items` (1,649 total item lines; average 1.68 items/order).
- Summing `orders.total_amount` after joining `orders` and `order_items` duplicates each order's total for every line item, producing **$68,324,532.11** (an erroneous **114.7% overstatement**).
- **Resolution**: Daily completed revenue is aggregated directly from `orders.total_amount` filtered by `status = 'completed'` without joining `order_items`. Mathematical reconciliation:
  $$\sum \text{order\_items.total\_price} + \sum \text{tax} - \sum \text{discount} = \$29,237,297.50 + \$2,597,234.90 - \$11,700.00 = \$31,822,832.40$$

### 3.3 Data Integrity & Hygiene
- **Null Dates**: 0 orders have null or empty order dates.
- **Negative Amounts**: 0 orders have negative totals or subtotals.
- **Null Amounts**: 0 orders have null totals.
- **Foreign Key Integrity**: Confirmed 0 broken foreign key relationships via `PRAGMA foreign_key_check`.
- **Currency Representation**: SQLite schema stores numeric `REAL` floats. Currency is uniform USD; no currency conversion column exists.

---

## 4. Dataset Shape & Date Range

### 4.1 Primary Target: Daily Completed Revenue
- **Dataset File**: `backend/ml/artifacts/daily_sales_revenue.csv` (and `.json`)
- **Date Range**: `2024-01-01` to `2025-12-31` (continuous inclusive calendar).
- **Dataset Shape**: **731 rows $\times$ 6 columns**
- **Columns**: `date` (YYYY-MM-DD), `revenue` (float), `order_count` (int), `avg_order_value` (float), `min_order_value` (float), `max_order_value` (float).
- **Active Sales Days**: 466 days (63.75%).
- **Zero-Sales Days**: **265 days (36.25%)**.

### 4.2 Secondary Target: Daily Units Sold (Independent Target)
- **Dataset File**: `backend/ml/artifacts/daily_units_sold.csv` (and `.json`)
- **Dataset Shape**: **731 rows $\times$ 5 columns**
- **Columns**: `date` (YYYY-MM-DD), `units_sold` (int), `order_count` (int), `line_item_count` (int), `distinct_products_sold` (int).
- **Total Units Sold**: 2,686 units across 15 SKUs.
- **Separation**: Kept strictly independent from revenue to avoid corrupting financial models with volumetric counts.

---

## 5. Statistical Characteristics & Known Limitations

### 5.1 Distribution Summary (Daily Revenue)
| Metric | Full Continuous Series (731 Days) | Active Days Only (466 Days) |
| :--- | :--- | :--- |
| **Sum** | $31,822,832.40 | $31,822,832.40 |
| **Mean** | $43,533.29 | $68,289.34 |
| **Median** | $18,570.00 | $48,141.75 |
| **Standard Deviation** | $62,651.86 | $66,843.24 |
| **Minimum** | $0.00 | $2,201.50 |
| **25th Percentile (Q1)** | $0.00 | $23,432.50 |
| **75th Percentile (Q3)** | $63,670.30 | $91,960.00 |
| **Interquartile Range (IQR)** | $63,670.30 | $68,527.50 |
| **Maximum** | $428,281.00 | $428,281.00 |

### 5.2 Outliers
- **Mild Outliers** ($> \$159,175.75$): 44 days (6.0%).
- **Extreme Outliers** ($> \$254,681.20$): 12 days (1.6%).
- Outliers correspond to enterprise bulk purchases and synthetic promotional events (Cyber Week late November).

### 5.3 Known Synthetic Limitations
1. **Zero-Inflation (36.25%)**: Over a third of calendar days have $0 revenue. In early 2024 (Jan–April), most days have zero orders.
2. **Deterministic Customer Ramp Artifact**: The upward revenue trend across 2024–2025 is driven by the synthetic customer generator introducing customers uniformly over 0–450 days:
   $$\text{signup\_days} = \text{random.randint}(0, 450)$$
   This must not be mistaken for real organic enterprise market expansion.
3. **Absence of Weekly Cyclicality**: Day-of-week revenue means ($32k–$55k) and active day counts (~63–69/105) are uniform across Monday–Sunday because order offsets were drawn uniformly at random.
4. **Weak Autocorrelation**: Lag 1 is +0.1139, Lag 7 is +0.1337. Standard autoregressive lag features offer limited predictive power.

---

## 6. Commands to Reproduce Preparation

From the repository root (`c:\DayScout`):

```powershell
# 1. Run full data audit and print diagnostic metrics
.\backend\venv\Scripts\python backend\ml\prepare_sales_data.py --audit

# 2. Export clean datasets to backend/ml/artifacts/
.\backend\venv\Scripts\python backend\ml\prepare_sales_data.py --export

# 3. Custom path execution (if running from backend directory)
cd backend
.\venv\Scripts\python ml\prepare_sales_data.py --db datascout.db --output-dir ml\artifacts
```

---

## 7. Tests Executed & Actual Results

All tests were executed against the active virtual environment (`backend/venv/Scripts/python`):

```powershell
cd c:\DayScout\backend
.\venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```

### Test Results Breakdown:
- **`tests/test_sales_data_preparation.py`**: **14 / 14 PASSED** (0.16s)
  - Daily aggregation accuracy
  - Status exclusion (cancelled, refunded, pending)
  - Revenue double-counting prevention
  - Contiguous calendar date index and zero filling
  - Chronological sorting
  - Empty database and missing table resilience
  - Malformed date string and negative amount filtering
  - Read-only database access enforcement (`mode=ro` + `PRAGMA query_only = ON`)
  - Deterministic reproducibility
  - Units sold calculation
  - Physical CSV/JSON export verification
  - Complete audit report structure
- **`tests/test_sql_agent.py`**: **18 / 18 PASSED** (0.43s)
- **`tests/test_business_database.py`**: **13 / 13 PASSED** (0.55s)
- **`tests/test_baseline_smoke.py`**: **4 / 4 PASSED** (0.10s)
- **Total Backend Test Suite**: **49 / 49 PASSED (100% Success)** in 1.24s.

### Health Endpoint Check:
```python
resp = client.get('/health')
# Output: Status 200 OK -> {'status': 'healthy', 'database': 'connected', 'ai_providers': {'openai': 'not_configured', 'pinecone': 'configured'}}
```

---

## 8. Is the Data Suitable for Forecasting?

**Verdict: YES, but with strict methodological constraints.**

### What WILL Work (Recommended Methodologies):
1. **Two-Stage Hurdle / Zero-Inflated Model**:
   - **Stage 1 (Binary Classifier)**: Predicts probability of $\ge 1$ order occurring on date $t$ ($P(\text{orders} > 0)$).
   - **Stage 2 (Positive Value Regressor)**: Predicts expected positive revenue conditional on an order occurring (using Log-Normal, Gamma, or Tweedie loss).
2. **Intermittent Demand Models**: Croston's Method or Syntetos-Boylan Approximation (SBA).
3. **Tree-Based Feature Regressors (LightGBM / XGBoost / Random Forest)**:
   - Incorporating calendar indicators, active marketing campaign flags, cumulative active customer counts, and rolling window means (7-day, 14-day, 30-day).
   - Using robust loss functions (Huber or MAE) to avoid overfitting extreme B2B outliers.

### What WILL NOT Work (Unsuitable Approaches):
1. **Classical Box-Jenkins ARIMA / SARIMA**:
   - High zero inflation (36.25%) severely violates normality and constant variance assumptions.
   - Low autocorrelation (+0.11 at Lag 1, +0.13 at Lag 7) causes ARIMA to degenerate into a flat mean forecast.
2. **Random Train/Test Splitting**: Leaks future cohort sizes into past predictions.
3. **Evaluating with Raw MAPE**: Division by zero on zero-sales days produces mathematically undefined or absurdly distorted scores.

---

## 9. Recommended Model Evaluation Design for Phase 6B

### 9.1 Chronological Holdout Partitioning
- **Training Set (547 days | 2024-01-01 to 2025-06-30)**: Ground truth mean: $25,646.94.
- **Validation Set (92 days | 2025-07-01 to 2025-09-30)**: Ground truth mean: $72,719.34. Used for model selection and hyperparameter tuning.
- **Holdout Test Set (92 days | 2025-10-01 to 2025-12-31)**: Ground truth mean: $66,343.20, StdDev: $76,590.97. Reserved strictly for final unbiased reporting.

### 9.2 Benchmark Baseline Comparison (Holdout Test Period)
Every candidate model in Phase 6B must be evaluated against these three established baselines:

| Model | MAE | RMSE | MAPE (Non-Zero Only)* |
| :--- | :--- | :--- | :--- |
| **1. Naive Persistence ($y_{t-1}$)** | $87,178.54 | $121,220.34 | 293.0% |
| **2. 7-Day Rolling Mean** | $61,704.90 | $83,059.62 | 254.2% |
| **3. Historical Training Mean ($\bar{y}_{\text{train}}$)** | **$52,408.36** | **$82,450.83** | **131.8%** |

*Target for Phase 6B: Any proposed model must achieve MAE < $52,408.36 and RMSE < $82,450.83 to outperform simple historical mean heuristics.*

### 9.3 Evaluation Metrics Policy
- **Primary Metric**: **Mean Absolute Error (MAE)** — directly interpretable in business dollars; robust to extreme spikes.
- **Secondary Metric**: **Root Mean Squared Error (RMSE)** — tracks sensitivity to large forecasting errors.
- **MAPE Policy**: Reported **only on non-zero sales dates** with explicit documentation of its limitations on intermittent data.

---

## 10. Conclusion & STOP

Phase 6A has met all objectives:
- Data audit completed and thoroughly documented.
- Exact completed-order revenue definition implemented without double-counting.
- Reproducible, deterministic data preparation pipeline created under `backend/ml/`.
- 14 automated unit tests added; all 49 backend tests passing.
- Comprehensive technical documentation created in `docs/SALES_FORECASTING_DATA.md`.
- Time-series validation design and benchmark thresholds established.

**STOP**: As instructed, no final models have been trained, and no prediction APIs have been implemented. Ready for your review before proceeding to Phase 6B.
