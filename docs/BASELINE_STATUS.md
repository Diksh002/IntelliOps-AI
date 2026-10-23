# IntelliOps AI — Baseline Status & Windows Execution Guide
**Codebase:** DataScout Enterprise Platform  
**Target Platform:** IntelliOps AI  
**Execution Date:** October 21, 2026  
**Auditor / Engineer:** Senior Engineering Team (Pair Programming with Antigravity AI)  
**Status:** Baseline Verified & Running Locally (Phase 1 Checkpoint)

---

## 1. Verified Runtime Versions

The baseline application was verified and tested on Windows 11 with PowerShell:

| Runtime / Tool | Verified Version | Status |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 (x64) | Active Host |
| **Shell** | Windows PowerShell 5.1 / PowerShell 7 | Tested |
| **Git** | 2.53.0.windows.2 | Verified |
| **Python** | 3.12.10 (CPython 64-bit) | Active in `backend/venv` |
| **Node.js** | v24.18.0 | Verified |
| **npm** | 11.16.0 | Verified |
| **Database** | SQLite 3 (`datascout.db`) | Verified |

---

## 2. Dependencies Installed

### Backend (Python 3.12 Virtual Environment)
Installed inside `c:\DayScout\backend\venv`:
- `fastapi` (0.157.0)
- `uvicorn` (0.54.0)
- `pydantic` (2.14.1) & `pydantic-core` (2.50.1)
- `python-dotenv` (1.2.4)
- `python-multipart` (0.0.32)
- `httpx` (0.28.1)
- `starlette` (1.9.0)
- `anyio` (4.15.1)
- Standard library modules utilized: `sqlite3`, `random`, `json`, `datetime`, `unittest`.

### Frontend (Next.js 16 App Router)
Installed via `npm install` inside `c:\DayScout\frontend`:
- `next` (16.0.5)
- `react` / `react-dom` (19.2.0)
- `tailwindcss` (v4) & `@tailwindcss/postcss`
- `recharts` (3.7.0)
- `zustand` (5.0.8)
- `@tanstack/react-query` (5.90.11)
- `framer-motion` (12.23.24)
- `lucide-react` (0.555.0)
- `sonner` (2.0.7)

---

## 3. Database Initialization & Seeding Steps

The application stores data in a local SQLite file located at `c:\DayScout\backend\datascout.db`.

### Step-by-Step Commands (PowerShell)
```powershell
# Navigate to backend directory
cd c:\DayScout\backend

# 1. Initialize schema tables
.\venv\Scripts\python init_db.py

# 2. Seed deterministic transaction and payroll data
.\venv\Scripts\python data\seed_data.py
```

### Verification Query
```powershell
.\venv\Scripts\python -c "import sqlite3; conn = sqlite3.connect('datascout.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM transactions'); print('Transactions:', cursor.fetchone()[0]); cursor.execute('SELECT COUNT(*) FROM payroll'); print('Payroll:', cursor.fetchone()[0]); conn.close()"
```
*Expected Output:*
```text
Transactions: 1000
Payroll: 3
```

### Idempotency Guarantee
The seeding script has been verified as idempotent: if re-executed, it checks existing row counts and skips insertion rather than creating duplicates.

---

## 4. Environment Configuration

### Backend: `c:\DayScout\backend\.env`
```env
# OpenAI Configuration (leave placeholder if running in offline mode)
OPENAI_API_KEY=your-openai-api-key-here

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_INDEX_NAME=datascout
PINECONE_HOST=https://datascout-placeholder.svc.aped-4627-b74a.pinecone.io

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
```

### Frontend: `c:\DayScout\frontend\.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 5. Startup Commands for Windows

### Backend Startup (Terminal 1)
```powershell
cd c:\DayScout\backend
.\venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- **Service Address:** `http://localhost:8000`
- **Interactive OpenAPI Docs:** `http://localhost:8000/docs`
- **Health Endpoint:** `http://localhost:8000/health`

### Frontend Startup (Terminal 2)
```powershell
cd c:\DayScout\frontend
npm run dev
```
- **Web App Address:** `http://localhost:3000`

---

## 6. Endpoints Tested & Results

| Method | Endpoint | Status | Verified Payload / Behavior |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | **200 OK** | `{"status": "healthy", "database": "connected", "ai_providers": {"openai": "not_configured", "pinecone": "configured"}}` |
| `GET` | `/api/stats` | **200 OK** | `{"revenue": "$2.4M", "documents": 0, "queries": 0, "agents_active": 4}` |
| `GET` | `/api/analytics/summary` | **200 OK** | Returns query counts, latency averages, and agent breakdown from `agent_logs`. |
| `GET` | `/api/history` | **200 OK** | Returns last 50 queries from `query_audit`. |
| `GET` | `/api/settings` | **200 OK** | `{"openai_model": "gpt-4o", "theme": "dark", "notifications": "true", "auto_save": "true"}` |
| `GET` | `/api/documents` | **200 OK** | Returns array of uploaded PDF documents metadata. |
| `POST` | `/chat` | **200 OK** | Resilient error contract returned when `OPENAI_API_KEY` is missing: informs user to configure key without server crash or mock charts. |

---

## 7. Frontend Verification in Browser

Tested via automated headless browser subagent at `http://localhost:3000`:
1. **Overview Dashboard (`/dashboard`)**:
   - Rendered 4 KPI cards: Total Revenue ($2.4M), Documents Processed (0), Active Queries (0), Agents Running (4).
   - Sidebar navigation, recent activity feed, quick action buttons rendered without error.
2. **Analytics Center (`/analytics`)**:
   - Query traffic metrics, average latency, and success rates retrieved live from `GET /api/analytics/summary`.
3. **Query Lab (`/query`)**:
   - Natural language input prompt, example query badges, and message thread loaded correctly.
4. **Console & Network**:
   - Zero JavaScript runtime errors, 0 failed network requests.
   - Fast Refresh and Next.js Turbopack dev server operational.

---

## 8. Errors Discovered & Fixes Applied

| Issue Identified | Root Cause | Fix Applied | Result |
| :--- | :--- | :--- | :--- |
| **Windows Console Unicode Crash** | `init_db.py` attempted to print Unicode character `\u2705` (`✅`), causing `UnicodeEncodeError: 'charmap' codec can't encode character` under Windows ANSI `cp1252` code page. | Replaced Unicode emoji with ASCII string `[OK]`. | `init_db.py` runs cleanly on any Windows terminal. |
| **Non-Idempotent Seeding** | `seed_data.py` unconditionally inserted 1,000 transactions and 3 payroll records every run. | Added row count checks (`SELECT COUNT(*)`) before insertion. | Seeding is safe to rerun without duplicating data. |
| **Unnecessary Heavy Dependencies in Seeder** | `seed_data.py` imported `pandas` (unused) and `numpy` (only for basic uniform/choice randoms), causing long wheel download stalls on slow connections. | Replaced with Python standard library `random` module seeded with `seed(42)`. | Seed generation executes deterministically in 0.05 seconds with zero external dependencies. |
| **Missing `python-multipart`** | FastAPI endpoints using `UploadFile` / `File(...)` require `python-multipart`, which was absent from default venv packages. | Installed `python-multipart==0.0.32`. | Multipart file uploads function correctly. |
| **Unhandled Missing API Key Crash** | Missing `OPENAI_API_KEY` caused unhandled `ValueError` inside `/chat`, producing 500 error logs. | Added explicit configuration verification in `/chat` returning clean diagnostic status. | Server remains resilient and explains configuration requirements. |
| **Hardcoded Mock Visualization Fallback** | In `main.py`, queries without SQL data injected a hardcoded fake sales array into the visualizer (violating Rule 7). | Removed the fake data injection; visualizer only receives verified SQL data. | Preserves data integrity. |

---

## 9. Baseline Automated Tests

Because the repository was missing the advertised `backend/tests/` suite, a formal smoke test suite was created at [backend/tests/test_baseline_smoke.py](file:///c:/DayScout/backend/tests/test_baseline_smoke.py).

### Test Suite Execution
```powershell
cd c:\DayScout\backend
.\venv\Scripts\python -m unittest tests/test_baseline_smoke.py
```

### Test Results
```text
C:\DayScout\backend\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
........
----------------------------------------------------------------------
Ran 8 tests in 0.061s

OK
```
- `test_01_database_file_exists`: **PASSED**
- `test_02_database_schema_integrity`: **PASSED**
- `test_03_database_records_present`: **PASSED**
- `test_04_health_endpoint`: **PASSED**
- `test_05_stats_endpoint`: **PASSED**
- `test_06_analytics_summary_endpoint`: **PASSED**
- `test_07_settings_endpoint`: **PASSED**
- `test_08_chat_resilience_without_api_key`: **PASSED**

---

## 10. Features Blocked & Remaining Known Issues

1. **AI Agents (Supervisor, Natural-Language SQL, LLM Visualizer)**:
   - Blocked by lack of a configured live `OPENAI_API_KEY`.
   - Local fallback proposal: In Phase 3–5, we can implement an offline rule-based intent router and direct SQL query engine for development without requiring paid cloud APIs.
2. **RAG Agent (Pinecone)**:
   - Blocked by missing cloud Pinecone index credentials and the previously documented embedding dimension mismatch (`512` vs `1024`).
   - Local fallback proposal: In Phase 8, implement a local vector store (e.g. ChromaDB or SQLite-vec / FAISS) with local embeddings so RAG works without cloud dependencies.
3. **Missing Business Intelligence Entities**:
   - The current SQLite schema only has flat `transactions` and `payroll` tables. Lacks `customers`, `products`, `orders`, `inventory`, `campaigns`, and `support_tickets` needed for customer churn and demand forecasting.

---

## 11. Instructions for Safely Stopping the Servers

To stop running background services in PowerShell:
- **Interactive Terminal:** Press `Ctrl + C` in each terminal window running `uvicorn` and `npm run dev`.
- **Background / Port Cleanup:**
```powershell
# Stop backend on port 8000
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# Stop frontend on port 3000
Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```
