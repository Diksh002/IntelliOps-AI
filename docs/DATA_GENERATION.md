# IntelliOps AI — Synthetic Business Data Generation Guide
**Document Version:** 1.0.0 (Phase 4 Deliverable)  
**Target Platform:** IntelliOps AI  
**Generator Script:** `backend/data/generate_business_data.py`  
**Validator Script:** `backend/data/validate_business_data.py`  
**Status:** Approved & Validated  

---

## 1. Overview & Objectives

Machine learning models for business intelligence require realistic, longitudinal, and logically consistent data containing:
- Multi-year seasonal trends
- Customer lifetime activity cycles
- B2B transaction value distributions
- Anomaly events for benchmark detection
- Explicit, leak-free target labels (e.g., Customer Churn)

The data generator produces deterministic data across 10 normalized relational tables in SQLite without requiring external network access or heavy dependencies.

---

## 2. Generator Design Principles

### 2.1 Determinism & Reproducibility
- The generator accepts a `--seed` argument (default `42`).
- Uses Python's standard library `random` module with zero external dependencies.
- Re-running the script with the same seed on an identical database produces bit-for-bit identical row counts, amounts, dates, and relationships.

### 2.2 Mathematical Consistency
- **Order Item Total:** `total_price = round(quantity * unit_price * (1.0 - discount), 2)`
- **Order Subtotal:** `subtotal = round(sum(order_items.total_price), 2)`
- **Order Total:** `total_amount = round(subtotal + tax - discount, 2)`
- **Payment Reconciliation:** Every `completed` order has an exactly matching `completed` payment record with `amount == total_amount`.
- **Refund Reconciliation:** `refunded` orders record the original payment plus an equal offsetting refund transaction.

### 2.3 Temporal Validity
- All customer orders and customer interactions occur **on or after** the customer's `signup_date`.
- Support ticket `resolved_date` occurs **after** `created_date`.
- Active dates span January 1, 2024 through December 31, 2025.

---

## 3. Modeling B2B Customer Behavior

### 3.1 Tier-Based Purchasing Profiles
| Customer Tier | Population Weight | Typical Order Frequency | Basket Quantity | Average Order Value |
| :--- | :--- | :--- | :--- | :--- |
| **Enterprise** | 25% | 5–17 orders/year | 2–8 units/SKU | ~$46,300 |
| **Mid-Market** | 45% | 3–12 orders/year | 1–4 units/SKU | ~$30,700 |
| **SMB** | 30% | 2–10 orders/year | 1 unit/SKU | ~$22,300 |

### 3.2 Non-Leaking Customer Churn Rule
To prepare for **Phase 6: Customer Churn Prediction**, synthetic customer churn is generated following a strict time-window rule:
- **Observation End Date:** December 31, 2025.
- **Churn Inactivity Cutoff:** October 1, 2024 (90 days of inactivity).
- **Rule:** A customer is labeled as churned (`is_active = 0`) if their last order occurred prior to the cutoff date despite having registered earlier in the period.
- **Resulting Churn Rate:** **20.7% (31 out of 150 customers)**, providing a balanced, realistic target distribution for training binary classifiers (Random Forest, Logistic Regression, XGBoost).
- **No Target Leakage:** The dataset contains no artificial synthetic flag directly correlating with churn; future models must learn patterns from RFM features (Recency, Frequency, Monetary value), ticket counts, and interaction frequency.

---

## 4. Controlled Synthetic Anomalies

The generator injects 3 realistic, documented business anomalies to evaluate future Anomaly Detection and Causal Decision Intelligence models:

### Anomaly 1: APAC Supply Chain Shock (August – September 2024)
- **Mechanism:** Simulates port strikes in Singapore delaying hardware shipments.
- **Manifestation:** In APAC between 2024-08-01 and 2024-09-30, hardware orders (`category_id = 3`) drop by ~70%, and hardware inventory reaches near-depletion levels.
- **Ground Truth Document:** Corresponds with `backend/reports/Q3_APAC_Analysis.pdf`.

### Anomaly 2: Cyber Week SaaS Spikes (Late November 2024 & 2025)
- **Mechanism:** End-of-year promotional campaigns and Black Friday enterprise flash discounts.
- **Manifestation:** Cloud Subscriptions (`category_id = 2`) surge by 250% during the final week of November in both 2024 and 2025.

### Anomaly 3: Software Release Quality Outage (March 2025)
- **Mechanism:** Defective enterprise software minor release.
- **Manifestation:** A 400% surge in `Critical` and `High` priority support tickets for `SW-DS-CORE` and `SW-DS-ADV`.
- **Customer Impact:** CSAT scores for these tickets drop from baseline 4.2/5 to 1.8/5.

---

## 5. Dataset Scale Configurations

| Scale | Customers | Expected Orders | Expected Items | Run Duration |
| :--- | :--- | :--- | :--- | :--- |
| **`small` (Default)** | 150 | ~900–1,100 | ~1,500–2,000 | ~0.8 seconds |
| **`medium`** | 500 | ~3,500–4,500 | ~6,000–8,000 | ~3.2 seconds |
| **`large`** | 2,000 | ~16,000–22,000 | ~30,000–40,000 | ~15 seconds |

---

## 6. Execution Commands (PowerShell)

### Generate Small Dataset (Default)
```powershell
cd c:\DayScout\backend
.\venv\Scripts\python data\generate_business_data.py --scale small --seed 42
```

### Force Overwrite / Clean Regeneration
```powershell
.\venv\Scripts\python data\generate_business_data.py --scale small --seed 42 --force
```

### Generate to an Isolated Test Database
```powershell
.\venv\Scripts\python data\generate_business_data.py --db test_staging.db --scale small --seed 42
```

### Run Comprehensive Automated Validation
```powershell
.\venv\Scripts\python data\validate_business_data.py --db datascout.db
```
*Expected Output:*
```text
INFO:__main__:Validation complete: 10/10 checks PASSED.
INFO:__main__:[OK] All data integrity checks passed.
```
