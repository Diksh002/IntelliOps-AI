# IntelliOps AI — System Architecture Specification
**Target Platform:** IntelliOps AI (Enterprise Decision Intelligence Platform)  
**Baseline Codebase:** DataScout Enterprise Platform  
**Document Status:** Approved Architecture Blueprint (Phase 2 Checkpoint)  
**Author:** Senior Engineering Team (Pair Programming with Antigravity AI)  

---

## 1. Architectural Overview & Design Philosophy

The objective of **IntelliOps AI** is to transform a basic multi-agent data query scaffold into a production-grade **AI-powered Business Intelligence and Decision Intelligence platform**.

The system enables business executives, operations directors, and data analysts to ask complex natural-language business questions (e.g., *"Why did revenue decrease last month, and what should we do to improve it?"*), and receive verified, evidence-backed answers supported by:
1. Direct relational SQL database queries.
2. Verified statistical calculations and period-over-period decompositions.
3. Genuine, trained Machine Learning models (Forecasting, Churn, Demand, Anomalies).
4. Semantic document retrieval (RAG) over business reports and corporate policy.
5. Evidence-based recommendation synthesis distinguishing **Facts**, **Calculations**, **Predictions**, **Hypotheses**, and **Actionable Recommendations**.

---

## 2. Component Status Legend

To maintain strict engineering integrity, every component in this architecture document is explicitly tagged with its actual implementation status:

| Tag | Definition | Current Presence |
| :--- | :--- | :--- |
| `[EXISTING - ACTIVE]` | Fully implemented, verified, and operational in the local environment. | FastAPI backend, SQLite database, Next.js frontend, baseline smoke tests. |
| `[EXISTING - BLOCKED]` | Implemented in codebase, but currently non-operational due to missing credentials or configuration mismatches. | LangGraph Supervisor, Natural-Language SQL Agent, Pinecone RAG Agent. |
| `[PROPOSED - PHASE 4]` | Designed and scheduled for Phase 4; not yet written in code. | Relational Business Schema (Customers, Products, Orders, Inventory, Campaigns). |
| `[PROPOSED - PHASE 5]` | Designed and scheduled for Phase 5; not yet written in code. | AST-validated, Read-Only Natural Language SQL Engine. |
| `[PROPOSED - PHASE 6-7]`| Designed and scheduled for Phase 6 & 7; not yet written in code. | Trained ML Suite & Inference ML Agent (Forecasting, Churn, Demand, Anomaly). |
| `[PROPOSED - PHASE 8]` | Designed and scheduled for Phase 8; not yet written in code. | Local/Embedded Vector Store (ChromaDB/FAISS) with dimension-aligned embeddings. |
| `[PROPOSED - PHASE 9-11]`| Designed and scheduled for Phase 9–11; not yet written in code. | Master Decision Synthesizer & Variance Contribution Engine. |

---

## 3. Current Baseline Architecture (As-Is)

### 3.1 Macro Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                               Next.js 16 Frontend                               |
|                  (App Router, React 19, Tailwind CSS, Recharts)                 |
|                       Running on http://localhost:3000                          |
+---------------------------------------------------------------------------------+
                                       │  HTTP Fetch
                                       │  (JSON / REST)
                                       ▼
+---------------------------------------------------------------------------------+
|                               FastAPI Backend                                   |
|                        Running on http://localhost:8000                         |
|                                                                                 |
|  [REST Endpoints]                                                               |
|  ├── /health                       --> System & Provider Health Check           |
|  ├── /api/stats                    --> Basic metrics from SQLite                |
|  ├── /api/analytics/summary        --> Latency and query logs from SQLite       |
|  ├── /api/history                  --> Query audit history                      |
|  ├── /api/settings                 --> User preferences store                   |
|  ├── /api/documents                --> Uploaded PDF metadata                    |
|  └── /chat                         --> Natural language query entry point       |
+---------------------------------------------------------------------------------+
           │                                          │
           │ Direct SQLite Queries                    │ Invokes
           ▼                                          ▼
+-----------------------+              +-----------------------------------------+
| SQLite (datascout.db) |              | LangGraph Multi-Agent Workflow          |
|                       |              |                                         |
| ├── documents         |              | [Supervisor] (ChatOpenAI gpt-4o)        |
| ├── agent_logs        |              |     ├── sql_agent (LangChain SQL agent) |
| ├── query_audit       |              |     ├── rag_agent (Pinecone vector DB)  |
| ├── custom_agents     |              |     └── clarify (Clarification prompt)  |
| ├── user_settings     |              +-----------------------------------------+
| ├── transactions (1K) |                                 │
| └── payroll (3 rows)  |                                 ▼
+-----------------------+              +-----------------------------------------+
                                       | Visualizer Agent (Recharts JSON schema) |
                                       +-----------------------------------------+
```

### 3.2 Frontend Responsibilities (`[EXISTING - ACTIVE]`)
- **Framework:** Next.js 16.0.5 with Turbopack, React 19.2.0, TypeScript 5.
- **Port:** `http://localhost:3000`.
- **Pages & Routes:**
  - `/dashboard`: High-level KPI summary cards, agent activity feed, quick links.
  - `/analytics`: Query metrics, average latency charts, query volume breakdown.
  - `/query`: Interactive chat workspace, thought log accordion, dynamic chart display.
  - `/documents`: Document upload and ingestion monitoring list.
  - `/settings`: Persistent preferences (theme, default LLM model).
  - `/agents`: Agent inventory and custom agent creator.
- **State & Data Fetching:** Zustand for client-side state; TanStack React Query for caching API calls.
- **API Client:** `lib/api.ts` targets `process.env.NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

### 3.3 Backend Responsibilities (`[EXISTING - ACTIVE]`)
- **Framework:** FastAPI with Uvicorn ASGI server.
- **Port:** `http://localhost:8000`.
- **CORS:** Configured for `http://localhost:3000`.
- **Core Endpoints:**
  - `GET /health`: Reports server status, SQLite connection, and AI provider key detection.
  - `GET /api/stats`: Returns document counts, query counts, and revenue.
  - `GET /api/analytics/summary`: Aggregates latency and success rate from `agent_logs`.
  - `GET /api/history`: Returns audit history from `query_audit`.
  - `GET /api/settings` & `POST /api/settings`: Manages key-value user settings.
  - `POST /chat`: Receives natural-language query; routes to supervisor or diagnostic configuration response.

### 3.4 Database Structure (`[EXISTING - ACTIVE]`)
- **Technology:** Local SQLite 3 stored at `backend/datascout.db`.
- **Tables & Schemas:**
  1. `documents`: `(id INTEGER PK, name TEXT, size TEXT, upload_date TEXT, status TEXT, entities_count INT)`
  2. `agent_logs`: `(id INTEGER PK, agent_name TEXT, query TEXT, status TEXT, timestamp TEXT, duration_ms INT)`
  3. `query_audit`: `(id INTEGER PK, timestamp TEXT, query TEXT, result TEXT)`
  4. `custom_agents`: `(id INTEGER PK, name TEXT, description TEXT, system_prompt TEXT, tools TEXT, created_at TEXT)`
  5. `user_settings`: `(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)`
  6. `transactions`: `(id INTEGER PK, date TEXT, region TEXT, product TEXT, amount REAL, category TEXT)` — 1,000 synthetic rows.
  7. `payroll`: `(id INTEGER PK, employee_id TEXT, name TEXT, salary REAL, department TEXT)` — 3 static rows.

### 3.5 Existing Agent Implementation (`[EXISTING - BLOCKED]`)
1. **Supervisor (`agents/supervisor.py`):**
   - Implements LangGraph `StateGraph(SupervisorState)`.
   - Uses `ChatOpenAI(model="gpt-4o")` with structured output `RouteQuery`.
   - Decision paths: `sql_agent`, `rag_agent`, or `clarify`.
   - *Status:* Blocked when `OPENAI_API_KEY` is not present; resilient handler in `/chat` returns informative configuration status.
2. **SQL Agent (`agents/sql_agent.py`):**
   - Uses LangChain `create_sql_agent` with SQLite connection.
   - Restricted by table whitelist to `transactions` and `payroll`.
   - *Status:* Blocked when `OPENAI_API_KEY` is missing.
3. **RAG Agent (`agents/rag_agent.py`):**
   - Connects to remote Pinecone index `datascout`.
   - Queries with `OpenAIEmbeddings(model="text-embedding-3-large", dimensions=1024)`.
   - *Status:* Incompatible with ingestion script (`text-embedding-3-small`, 512 dimensions) and requires paid external Pinecone service.
4. **Visualizer Agent (`agents/visualizer_agent.py`):**
   - Converts tabular SQL result arrays into Recharts schema (`bar`, `line`, `pie`, `area`).

---

## 4. Current Limitations & Technical Debt

1. **Zero Genuine Machine Learning:** The current platform has no forecasting models, churn classifiers, or anomaly detection.
2. **Flat / Unrealistic Data Model:** The database has only a flat `transactions` table. There are no relational entities for `customers`, `products`, `orders`, `order_items`, `inventory`, `marketing_campaigns`, or `support_tickets`.
3. **Cloud Lock-in for RAG:** The RAG system strictly requires cloud Pinecone and OpenAI API keys; no local vector database fallback exists for local development.
4. **RAG Dimension Conflict:** Ingestion embeds with 512 dimensions while query agent queries with 1024 dimensions.
5. **No Read-Only SQL Enforcement:** The SQL connection does not enforce SQLite read-only mode (`mode=ro`), relying solely on LLM prompt discipline.
6. **No Decision / Causal Synthesis:** The system cannot decompose revenue variance, detect anomalies, or provide evidence-backed recommendations.

---

## 5. Target Architecture: IntelliOps AI (To-Be)

```
                                USER QUERY
                                    │
                                    ▼
       +─────────────────────────────────────────────────────────+
       |               MASTER DECISION ORCHESTRATOR              |
       |  (LangGraph Decision Graph with Deterministic Fallback) |
       +─────────────────────────────────────────────────────────+
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
+─────────────────+        +─────────────────+        +─────────────────+
|   SQL ANALYTICS |        | MACHINE LEARNING|        |   RAG RETRIEVAL |
|      ENGINE     |        |   AGENT (REAL)  |        |      ENGINE     |
| [PROPOSED-PH.5] |        | [PROPOSED-PH.7] |        | [PROPOSED-PH.8] |
+─────────────────+        +─────────────────+        +─────────────────+
         │                          │                          │
         ├── AST Parser / ReadOnly  ├── Sales Forecaster       ├── Local Vector Store
         ├── Parameterized Query    ├── Churn Predictor        │   (ChromaDB / SQLite)
         └── Relational Analytics   ├── Demand Predictor       ├── Document Parsers
                                    └── Anomaly Detector       └── Source Attribution
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                                    ▼
       +─────────────────────────────────────────────────────────+
       |             STATISTICAL & VARIANCE ENGINE               |
       |                   [PROPOSED - PH.10]                    |
       | ├── Period-over-period variance bridge                  |
       | ├── Regional & product contribution decomposition       |
       | └── Anomaly correlation vs. baseline metrics            |
       +─────────────────────────────────────────────────────────+
                                    │
                                    ▼
       +─────────────────────────────────────────────────────────+
       |               DECISION & SYNTHESIS ENGINE               |
       |                   [PROPOSED - PH.11]                    |
       | ├── FACT: Verified SQL & Statistical Calculations       |
       | ├── PREDICTION: ML Model Output (MAE, Confidence)       |
       | ├── HYPOTHESIS: Plausible explanatory drivers           |
       | └── RECOMMENDATION: Actionable evidence-backed guidance |
       +─────────────────────────────────────────────────────────+
                                    │
                                    ▼
       +─────────────────────────────────────────────────────────+
       |                  PRESENTATION LAYER                     |
       | ├── Structured Response Contract (JSON)                 |
       | ├── Genuine Dynamic Recharts (Real Tabular Data Only)   |
       | └── Executive Analytics Dashboard                       |
       +─────────────────────────────────────────────────────────+
```

---

## 6. Target Component Specifications

### 6.1 Relational Business Database (`[PROPOSED - PHASE 4]`)
A comprehensive, normalized relational schema supporting enterprise analytics:
- **`customers`**: Customer ID, registration date, demographic segment, region, lifetime value tier.
- **`products`**: Product ID, SKU, name, category, unit price, unit cost, active status.
- **`orders`**: Order ID, customer ID, order date, total amount, discount, order status.
- **`order_items`**: Item ID, order ID, product ID, quantity, unit price, total price.
- **`payments`**: Payment ID, order ID, payment method, payment date, status.
- **`inventory`**: Product ID, warehouse region, stock on hand, reorder point, safety stock.
- **`marketing_campaigns`**: Campaign ID, channel, spend, start date, end date, target segment.
- **`support_tickets`**: Ticket ID, customer ID, issue category, resolution time, sentiment rating.

### 6.2 Secure SQL Analytics Engine (`[PROPOSED - PHASE 5]`)
- **Read-Only Enforcement:** SQLite opened with URI `file:datascout.db?mode=ro`.
- **AST Query Validation:** Parses generated SQL with `sqlglot` or SQL parser to reject any DDL/DML (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `ATTACH`).
- **Table White-listing:** Enforces strict access boundaries only to analytical entities.
- **Execution Limits:** Strict statement timeouts (5,000 ms) and row count caps (`LIMIT 1000`).

### 6.3 Genuine Machine Learning Suite (`[PROPOSED - PHASE 6 & 7]`)
All ML capabilities will use genuine, pre-trained, versioned models serialized in `backend/models/`:
1. **Sales Forecasting Model (`[PROPOSED]`):**
   - Algorithm: Time-series forecasting (Prophet or ARIMA/SARIMAX baseline + Ridge/GradientBoosting regressor).
   - Metrics: MAE, RMSE, MAPE on chronological train/validation splits.
2. **Customer Churn Predictor (`[PROPOSED]`):**
   - Algorithm: Binary classification (RandomForestClassifier / LogisticRegression).
   - Features: RFM (Recency, Frequency, Monetary), average order value, support ticket frequency, days inactive.
   - Metrics: Precision, Recall, F1-Score, ROC-AUC.
3. **Product Demand Estimator (`[PROPOSED]`):**
   - Algorithm: Product-level demand regression taking into account seasonality and inventory reorder points.
4. **Statistical Anomaly Detector (`[PROPOSED]`):**
   - Algorithm: Isolation Forest / Rolling Z-Score decomposition on daily revenue and order volume.

### 6.4 Local & Cloud RAG Engine (`[PROPOSED - PHASE 8]`)
- **Dual-Mode Vector Store:**
  - Local Mode (default / offline): Embedded ChromaDB or SQLite-vec with local open-source sentence embeddings.
  - Cloud Mode (production): Pinecone with consistent embedding models.
- **Dimension Consistency:** Standardized embedding dimensions across ingestion and query pipelines.
- **Prompt Isolation:** Untrusted document context wrapped in XML boundary tags (`<untrusted_document_context>`) to neutralize prompt injection attacks.
- **Source Attribution:** Mandatory citation of document filename and page numbers.

### 6.5 Decision Intelligence & Synthesis Engine (`[PROPOSED - PHASE 11]`)
Transforms raw analytics into actionable insights following a strict cognitive taxonomy:
- **`FACT`**: Directly observed and verified data (e.g., *"Q3 revenue in APAC declined by 12.4% from $8.1M to $7.1M"*).
- **`CALCULATION`**: Mathematical variance contribution (e.g., *"Hardware delays in APAC accounted for 74% of the total regional variance"*).
- **`PREDICTION`**: Model output with explicit uncertainty bounds (e.g., *"Sales forecasting model predicts Q4 revenue of $7.8M +/- $250K with 95% confidence"*).
- **`HYPOTHESIS`**: Inferred causal explanations supported by document evidence (e.g., *"Port strikes in Singapore delayed on-premise hardware deployments by 6 weeks"*).
- **`RECOMMENDATION`**: Actionable strategic steps (e.g., *"Accelerate cloud-only deployment options to mitigate physical supply chain dependency"*).

---

## 7. Request Lifecycle & Data Flow

### Example User Query:
> *"Why did our revenue decrease last month, and what should we do to improve it?"*

```
1. Request Reception (POST /chat)
   └── Validates JSON payload; assigns unique Request ID.

2. Intent Classification & Routing (Master Orchestrator)
   └── Identifies multi-intent query: Requires (a) SQL Analytics, (b) Anomaly Detection, (c) RAG Document Retrieval.

3. Parallel Execution:
   ├── Branch A (SQL Engine):
   │   └── Queries monthly revenue by region, product, and category for current vs prior month.
   │   └── Computes delta: Identifies APAC region and Hardware product as primary negative drivers.
   ├── Branch B (ML Anomaly Detector):
   │   └── Evaluates APAC daily revenue timeline against 90-day moving average.
   │   └── Flags statistical anomaly in weeks 32-35.
   └── Branch C (RAG Engine):
       └── Searches reports for "APAC revenue drop", "hardware delays", "Q3 performance".
       └── Retrieves chunks from Q3_APAC_Analysis.pdf explaining Singapore port strike.

4. Variance & Decision Synthesis
   └── Correlates SQL delta with RAG document findings and ML anomaly timeline.
   └── Classifies:
       • FACT: APAC revenue dropped $980K (-12.4%).
       • CALCULATION: 74% of the drop concentrated in DataScout Pro hardware sales.
       • HYPOTHESIS: Supply chain disruption cited in internal report as primary cause.
       • RECOMMENDATION: Shift APAC sales incentives toward cloud-only SKU.

5. Visualizer Configuration
   └── Generates Recharts Bar Chart comparing APAC revenue across products for the two months.

6. Response Delivery
   └── Emits structured ChatResponse payload containing formatted markdown, thoughts log, and Recharts JSON.
```

---

## 8. Security Boundaries & Trust Architecture

| Boundary | Threat Model | Mitigation in Architecture |
| :--- | :--- | :--- |
| **Client -> API** | DoS, injection, malformed payloads | Pydantic model validation, CORS whitelist, request rate-limiting. |
| **Agent -> Database** | SQL Injection, DDL drop, privilege escalation | Read-only connection mode (`mode=ro`), AST parser forbidding modifying keywords, table whitelist. |
| **Document -> LLM** | Prompt injection via untrusted PDFs | Document text sandboxed in strict XML fences with system instructions prohibiting instruction overrides. |
| **API -> Environment** | Secret exposure in logs, traces, or errors | Safe config validation; zero credentials in error payloads; `.gitignore` enforcement. |
| **Model -> Inference** | Model poisoning, unverified inputs | Numerical schema validation of feature matrices before passing to scikit-learn models. |

---

## 9. Incremental Migration Roadmap

```
Phase 2 (Current Checkpoint)
  └── Secure foundation established (.gitignore, .env.example, baseline smoke tests, architecture spec).
       │
       ▼
Phase 3–4: Business Database & Synthetic Data Generator
  └── Implement normalized schema (Customers, Products, Orders, Inventory, Campaigns).
       │
       ▼
Phase 5: Secure Natural Language SQL Analytics
  └── Implement read-only AST-validated SQL generation engine.
       │
       ▼
Phase 6–7: Real Machine Learning Pipeline & ML Agent
  └── Train, evaluate, and serialize Forecasting, Churn, Demand, and Anomaly models.
       │
       ▼
Phase 8: Robust Local & Cloud RAG Engine
  └── Fix embedding dimension mismatch, provide embedded ChromaDB/FAISS fallback.
       │
       ▼
Phase 9–11: Decision Intelligence & Analytics UI
  └── Implement multi-agent synthesizer, revenue variance decomposition, and real Recharts.
       │
       ▼
Phase 12: Comprehensive Evaluation, Security Audit & Interview Guide
  └── Automated test suite, benchmark evaluation report, and student defense guide.
```
