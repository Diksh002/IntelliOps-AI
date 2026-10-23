# IntelliOps AI — Initial Repository Audit
**Codebase:** DataScout Enterprise Platform  
**Target Platform:** IntelliOps AI  
**Audit Date:** October 21, 2026  
**Auditor:** Senior Engineering Team (Pair Programming with Antigravity AI)  
**Status:** Completed (Phase 0 Checkpoint)

---

## 1. Executive Summary

DataScout was conceived as an AI-powered multi-agent data analysis platform combining natural language SQL querying, document retrieval via RAG, automated chart generation, and a Next.js analytics dashboard. 

The repository at the root (`MBilalKhanAI/DataScout`) is an orchestrator wrapper containing startup scripts and documentation that references two decoupled microservices:
1. `backend/`: FastAPI Python application with LangGraph/LangChain multi-agent routing.
2. `frontend/`: Next.js 16 (App Router) TypeScript web application with Tailwind CSS, Recharts, and Radix UI.

While the architectural concept is sound, the audit revealed several critical gaps, architectural inconsistencies, and missing components that must be addressed systematically before transforming it into the **IntelliOps AI** decision intelligence platform.

---

## 2. Technical Stack & Environment

| Component | Technology | Version / Spec | Notes |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 11 / PowerShell | Active Host | Confirmed via host execution |
| **Git** | Git for Windows | 2.53.0 | Installed and operational |
| **Backend Runtime** | Python (CPython) | 3.12.10 (3.11 & 3.14 also present) | Using isolated venv on 3.12 |
| **Backend Web Framework** | FastAPI | 0.104+ / 0.115+ | ASGI REST API with CORS enabled |
| **ASGI Server** | Uvicorn | 0.30+ | Local development reload mode |
| **Agent / LLM Framework** | LangChain & LangGraph | 0.2+ / 0.3+ | StateGraph orchestration |
| **LLM Provider** | OpenAI (GPT-4o) | Hardcoded in agent classes | Requires `OPENAI_API_KEY` (`sk-...`) |
| **Vector Database** | Pinecone | Cloud index `datascout` | Requires `PINECONE_API_KEY` & host |
| **Primary Database** | SQLite | 3.x (`datascout.db`) | Local file-based relational store |
| **Database Access Layer** | Python `sqlite3` + `SQLDatabase` | Standard library + LangChain utility | Parameterization only partial |
| **Frontend Runtime** | Node.js / npm | Node v24.18.0 / npm 11.16.0 | Installed and operational |
| **Frontend Framework** | Next.js | 16.0.5 (React 19.2.0, App Router) | TypeScript 5.x |
| **Styling & UI** | Tailwind CSS v4 + Radix UI | PostCSS `@tailwindcss/postcss` | Lucide icons, Sonner toasts |
| **State & Data Fetching** | Zustand + TanStack React Query | Zustand 5.0, Query 5.90 | Local and server state caching |
| **Visualizations** | Recharts | 3.7.0 | Bar, Line, Pie, Area chart rendering |

---

## 3. Feature Inventory

| Feature | Implementation Status | Evidence in Codebase | Problems & Technical Debt |
| :--- | :--- | :--- | :--- |
| **System Overview & Stats** | **Working** | `GET /api/stats` in `backend/main.py` queries `documents`, `query_audit` | Hardcoded revenue metric (`$2.4M`); fixed agent count (4). |
| **User Settings Persistence** | **Working** | `GET /api/settings`, `POST /api/settings` in `backend/main.py` & `user_settings` table | Basic key/value store; no schema validation or user auth scoping. |
| **Query History & Audit** | **Working** | `GET /api/history` in `backend/main.py` & `query_audit` table | Only tracks raw query string and result; lacks execution latency or user IDs. |
| **Analytics Summary** | **Working** | `GET /api/analytics/summary` in `backend/main.py` queries `agent_logs` | Computes average latency, total queries, agent breakdown from SQLite. |
| **Custom Agent Management** | **Working** | CRUD endpoints (`/api/agents/custom`) in `backend/main.py` & `custom_agents` table | Serializes tools array as JSON string; basic execution loop. |
| **Supervisor Multi-Agent Routing** | **Partially Working** | `Supervisor` class in `backend/agents/supervisor.py` | Hard-fails if OpenAI API key is missing. No offline/rule-based router fallback. |
| **Natural Language SQL Agent** | **Partially Working** | `SQLAgent` in `backend/agents/sql_agent.py` using `create_sql_agent` | Restricted only to `transactions` and `payroll`. No read-only DB user enforcement. |
| **PDF Document Ingestion & RAG** | **Broken** | `backend/data/ingest_pdfs.py` & `backend/agents/rag_agent.py` | **Dimension Mismatch:** Ingestion embeds with `text-embedding-3-small` (512 dims), while `rag_agent.py` queries with `text-embedding-3-large` (1024 dims). Cloud Pinecone strictly required (no local fallback). `generate_pdfs.py` missing `reportlab` in `requirements.txt`. |
| **Dynamic Visualizations** | **Partially Working** | `VisualizerAgent` in `backend/agents/visualizer_agent.py` & `DynamicChart.tsx` | If SQL returns no structured records, `main.py` injects hardcoded fake regional sales data (`[{"region": "North America", "sales": 45000}, ...]`). Violates Rule 7. |
| **Automated Test Suite** | **Broken / Missing** | Claimed in README: 8 test suites, 70% coverage (`python -m pytest tests/`) | **`backend/tests/` directory is completely absent from git.** Zero automated tests exist. |
| **Machine Learning Capabilities** | **Missing** | Required for IntelliOps AI | No ML models, forecasting pipelines, churn models, or anomaly detectors currently exist. |
| **Business Analytics & Decision Engine** | **Missing** | Required for IntelliOps AI | No root-cause analysis, hypothesis generation, or contribution analysis engines. |

---

## 4. Database Architecture & Schema

### Current Database Engine: SQLite (`datascout.db`)
The application uses local SQLite file storage located at `backend/datascout.db`.

### Tables Created by `init_db.py`:
1. `documents`:
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `name`: TEXT NOT NULL
   - `size`: TEXT
   - `upload_date`: TEXT
   - `status`: TEXT DEFAULT 'pending'
   - `entities_count`: INTEGER DEFAULT 0
2. `agent_logs`:
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `agent_name`: TEXT
   - `query`: TEXT
   - `status`: TEXT
   - `timestamp`: TEXT
   - `duration_ms`: INTEGER
3. `query_audit`:
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `timestamp`: TEXT
   - `query`: TEXT
   - `result`: TEXT
4. `custom_agents`:
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `name`: TEXT NOT NULL
   - `description`: TEXT
   - `system_prompt`: TEXT
   - `tools`: TEXT (added via CRUD)
   - `created_at`: TEXT DEFAULT CURRENT_TIMESTAMP
5. `user_settings`:
   - `key`: TEXT PRIMARY KEY
   - `value`: TEXT NOT NULL
   - `updated_at`: TEXT DEFAULT CURRENT_TIMESTAMP

### Seed Data Tables Created by `data/seed_data.py`:
1. `transactions`:
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `date`: TEXT (YYYY-MM-DD)
   - `region`: TEXT (NA, EMEA, APAC, LATAM)
   - `product`: TEXT (DataScout Pro, DataScout Lite, Consulting, Support)
   - `amount`: REAL ($1,000 to $50,000)
   - `category`: TEXT (Software, Services)
   - *Volume:* 1,000 randomly generated rows.
2. `payroll`:
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `employee_id`: TEXT
   - `name`: TEXT
   - `salary`: REAL
   - `department`: TEXT
   - *Volume:* 3 static rows (Alice Smith, Bob Jones, Charlie Brown).

### Schema Deficiencies:
- No foreign key relationships or constraints between tables.
- Lack of granular business entities: missing `customers`, `orders`, `order_items`, `products`, `categories`, `inventory`, `marketing_campaigns`, and `support_tickets`.
- Flat transactions model does not support customer retention or churn cohort calculations.
- Dates stored as plain text without indexes.

---

## 5. Agent Architecture & Workflow

### 1. Supervisor Agent (`backend/agents/supervisor.py`)
- Built using LangGraph `StateGraph(SupervisorState)`.
- Uses GPT-4o structured output (`with_structured_output(RouteQuery)`).
- Routing destinations: `sql_agent`, `rag_agent`, `clarify`.
- **Limitation:** Fails synchronously at class initialization if `OPENAI_API_KEY` is not present or does not match `sk-...`.

### 2. SQL Agent (`backend/agents/sql_agent.py`)
- Wraps LangChain's `create_sql_agent` with `ChatOpenAI(model="gpt-4o")`.
- Restricted to tables `transactions` and `payroll`.
- Stores raw queries in `query_audit` table.
- Returns plain text answer; attempts fallback data parsing for charts.

### 3. RAG Agent (`backend/agents/rag_agent.py`)
- Requires Pinecone serverless vector database (`PINECONE_API_KEY`, `PINECONE_HOST`).
- Attempts similarity search across PDF chunks.
- Passes retrieved chunks directly to GPT-4o prompt without prompt-injection boundary guards.

### 4. Visualizer Agent (`backend/agents/visualizer_agent.py`)
- Analyzes tabular SQL output using GPT-4o with structured schema (`ChartConfig`).
- Emits chart types: `bar`, `line`, `pie`, `area`.
- If SQL fails to provide structured tabular data, `main.py` feeds a hardcoded fake data mock into the visualizer.

### 5. Custom Agent (`backend/agents/custom_agent.py`)
- Dynamically binds user system prompts with `run_sql_query` and RAG tools using LangChain tool binding.

---

## 6. Discovered Defects, Blockers & Inconsistencies

1. **Missing Test Suites:**
   The documentation explicitly advertises `python -m pytest tests/` with 70% coverage. However, the `tests/` directory was never committed to the repository.
2. **Embedding Dimension Incompatibility:**
   - `backend/data/ingest_pdfs.py` configures:
     `model="text-embedding-3-small", dimensions=512`
   - `backend/agents/rag_agent.py` configures:
     `model="text-embedding-3-large", dimensions=1024`
   This guarantees a runtime dimension failure when executing RAG queries against the ingested Pinecone index.
3. **Hardcoded Mock Visualization Fallback:**
   In `backend/main.py` lines 388-398, queries containing visualization keywords that do not produce structured SQL records generate fake charts using a static array of mock regions and numbers.
4. **Missing Dependency in `generate_pdfs.py`:**
   `generate_pdfs.py` imports `reportlab`, but `reportlab` is omitted from `backend/requirements.txt`.
5. **Unpinned Python Dependencies & Deprecated `pinecone-client`:**
   `backend/requirements.txt` has no version pins. It specifies `pinecone-client` (legacy v2/v3 package) while code imports `from pinecone import Pinecone` (v3+ SDK) and `langchain-pinecone`. This causes resolver backtracking, pip timeouts, and installation errors.
6. **No Offline / Local Mode for Development:**
   Both `Supervisor` and `SQLAgent` hard-crash upon instantiation if `OPENAI_API_KEY` is absent, preventing the chat endpoint from functioning even in mock or diagnostic mode.

---

## 7. Security & Git Hygiene Audit

1. **Root `.gitignore` Missing:**
   The root repository directory `c:\DayScout` contains NO `.gitignore` file. Only the nested sub-repositories have `.gitignore`. Any root `.env`, database, log, or virtual environment created in the root directory is at immediate risk of being staged to git.
2. **Secrets Scan:**
   Grep searches for `sk-`, `sk-proj-`, and `pcsk_` across all source files confirmed that **no live production API keys are committed**. Only placeholders (`sk-proj-your-key-here`, `sk-placeholder`) are present.
3. **SQL Injection Surface:**
   The SQL agent uses LangChain's `create_sql_agent` with an unrestricted SQLite connection string. While restricted to two tables by table name, SQLite does not run with read-only connection pragmas (`mode=ro`), meaning an adversarial prompt injection could theoretically attempt DDL or DML statements.
4. **Document Prompt Injection:**
   PDF text retrieved from RAG is concatenated directly into the system prompt without boundary fences or untrusted input warnings.

---

## 8. Baseline Startup Instructions (Windows)

### Prerequisites Check
Confirm runtime availability in PowerShell:
```powershell
git --version
python --version
node --version
npm --version
```
*Current environment status: Git 2.53 ✅, Python 3.12.10 ✅, Node v24.18.0 ✅, npm 11.16.0 ✅.*

### Step 1: Initialize Database & Seed Data
From the `backend` directory:
```powershell
cd c:\DayScout\backend
.\venv\Scripts\python init_db.py
.\venv\Scripts\python data\seed_data.py
```
*Expected Output:*
- `✅ Database initialized with Enterprise tables.`
- `Database seeded successfully: datascout.db`

### Step 2: Configure Environment Files
- Backend: Ensure `c:\DayScout\backend\.env` contains:
  ```env
  OPENAI_API_KEY=sk-proj-your-key-here
  PINECONE_API_KEY=pcsk_your-key-here
  PINECONE_INDEX_NAME=datascout
  DEBUG=false
  ```
- Frontend: Ensure `c:\DayScout\frontend\.env.local` contains:
  ```env
  NEXT_PUBLIC_API_URL=http://localhost:8000
  ```

### Step 3: Run the Backend
```powershell
cd c:\DayScout\backend
.\venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
*Verify at:* `http://localhost:8000/health` and `http://localhost:8000/api/stats`

### Step 4: Run the Frontend
In a separate terminal:
```powershell
cd c:\DayScout\frontend
npm run dev
```
*Access Application at:* `http://localhost:3000`

---

## 9. Recommended Multi-Phase Roadmap to IntelliOps AI

```
Phase 0: Repository & Architectural Audit (Current Checkpoint)
   │
   ▼
Phase 1: Run & Verify Baseline Application (Resolve pip pins, seed SQLite, run baseline frontend)
   │
   ▼
Phase 2: Establish Secure Development Foundation (Root .gitignore, clean env handling)
   │
   ▼
Phase 3: Design IntelliOps AI Target Architecture (LangGraph multi-agent graph with ML nodes)
   │
   ▼
Phase 4: Design & Build Comprehensive Business Database (Customers, Orders, Products, Inventory, Campaigns)
   │
   ▼
Phase 5: Secure Natural Language SQL Analytics Engine (Read-only execution, schema inspection, parameterization)
   │
   ▼
Phase 6: Genuine Machine Learning Suite (Sales Forecasting, Churn Classifier, Demand Prediction, Anomaly Detection)
   │
   ▼
Phase 7: Dedicated ML Agent (Inference routing, metric evaluation, model explainability)
   │
   ▼
Phase 8: Robust Local & Cloud RAG Engine (Fix embeddings dimension mismatch, add local Chroma/FAISS fallback)
   │
   ▼
Phase 9: Master Decision Orchestrator (Synthesizing Facts vs. Predictions vs. Hypotheses vs. Recommendations)
   │
   ▼
Phase 10: Business Analytics & Contribution Engine (Revenue bridge, period-over-period variance decomposition)
   │
   ▼
Phase 11: Professional Decision Intelligence UI & Visualizations (Real data charts, Executive workspace)
   │
   ▼
Phase 12: Automated Verification, Security Hardening & Interview Documentation
```

---

## 10. Audit Conclusion & Next Single Action

The DataScout codebase provides a viable starting scaffold for FastAPI and Next.js, but its AI/ML/Data capabilities are currently superficial (no genuine ML models, brittle RAG dimensioning, missing tests, and fallback mock charts). 

**Next Single Action:**  
Proceed to **Phase 1 (Run the Original Application)**:
1. Normalize `backend/requirements.txt` to eliminate the resolver conflict with `pinecone-client`.
2. Complete backend package installation in the Python 3.12 virtual environment.
3. Initialize and seed `datascout.db`.
4. Launch both backend and frontend servers to capture and document the working baseline status.
