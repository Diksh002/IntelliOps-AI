# IntelliOps AI

> **Enterprise AI-Powered Multi-Agent Operational Intelligence & Analytics Platform**  
> Version 1.0.0 | Monorepo Architecture

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)

IntelliOps AI is an enterprise-grade AI platform combining specialized multi-agent orchestration, natural language SQL querying with AST security guardrails, document retrieval (RAG), dynamic data visualization, and an audited machine learning sales data preparation pipeline.

---

## 🌟 Key Features & Implementation Status

### 🤖 Multi-Agent Orchestration (Phases 0–3)
- **Supervisor Agent**: LangGraph-powered intelligent intent routing with GPT-4o.
- **Guarded SQL Agent**: Natural language to analytical SQL execution with rigorous AST query validation, table whitelist enforcement, read-only permissions, and query timeout guardrails.
- **Audit Logging**: Comprehensive query execution logging (`agent_audit_logs`) tracking timestamp, agent name, SQL query text, row counts, and status.
- **RAG Agent**: PDF document search and contextual question answering integrated with Pinecone vector database.
- **Visualizer Agent**: Automatic chart configuration generation (Bar, Line, Pie, Area) rendered interactively via Recharts.

### 🗄️ Relational Business Database (Phase 4)
- Normalized SQLite relational database covering 10 business tables:
  - `customers`, `categories`, `products`, `orders`, `order_items`, `payments`, `inventory`, `marketing_campaigns`, `customer_interactions`, `support_tickets`.
- Seed data generation script with strict referential integrity and business consistency (`backend/data/generate_business_data.py`).
- Automated data validation suite (`backend/data/validate_business_data.py`).

### 📈 Sales Forecasting & Evaluation Pipeline (Phases 6A & 6B)
- **Chronological Data Preparation**: Calendar-complete daily sales aggregate over 731 days (2024-01-01 through 2025-12-31) with strict zero-fill gap handling (`backend/ml/prepare_sales_data.py`).
- **Strict Chronological Partitions**:
  - Training: `2024-01-01` to `2025-06-30` (547 days)
  - Validation: `2025-07-01` to `2025-09-30` (92 days)
  - Final Holdout Test: `2025-10-01` to `2025-12-31` (92 days)
- **Feature Engineering & Leakage Isolation**: 20 temporal, lagged, and rolling features strictly restricted to prior observation windows with training-fitted scaling (`backend/ml/sales_features.py`).
- **Pure-Python Architectures**: Zero-dependency implementations of Ridge Regression, Decision Trees, Random Forests, and Two-Stage Hurdle models (`backend/ml/sales_models.py`).
- **Validation-Driven Model Selection**:
  - The **Decision Tree** model was selected using validation MAE ($50,166.76 vs Historical Mean $53,391.21).
- **Honest Test Evaluation & Baseline Comparison**:
  - **No model outperforms every baseline across all metrics.**
  - The Decision Tree's overall test MAE ($52,912.43) is slightly worse than the historical-mean baseline ($52,408.36, +1.0%), though on active trading dates it achieves lower error ($53,057.87 vs $55,570.98).
  - The **Random Forest** achieved the lowest reported test RMSE ($77,154.64 vs baseline $82,450.83).
  - Ridge Regression virtually eliminated systemic underprediction bias (+$546.52 vs baseline -$31,555.12).
- **Verification & Test Coverage**: 25 automated unit and regression tests for data preparation and forecasting (`backend/tests/test_sales_data_preparation.py`, `backend/tests/test_sales_forecast.py`).

---

## 📁 Repository Structure

```
IntelliOps-AI/
├── backend/                        # FastAPI Backend Application
│   ├── agents/                     # LangGraph Agent Implementations
│   │   ├── supervisor.py           # Multi-agent orchestrator
│   │   ├── sql_agent.py            # Natural language SQL agent
│   │   ├── sql_validator.py        # AST parsing & safety validation
│   │   ├── sql_executor.py         # Read-only execution & timeout guard
│   │   ├── rag_agent.py            # Document retrieval agent
│   │   └── visualizer_agent.py     # Dynamic chart configuration
│   ├── data/                       # Synthetic business data generators
│   │   ├── generate_business_data.py
│   │   └── validate_business_data.py
│   ├── ml/                         # Sales forecasting pipeline
│   │   ├── prepare_sales_data.py   # Calendar-complete data prep
│   │   ├── sales_features.py       # Leak-free feature engineering & scaling
│   │   ├── sales_models.py         # Pure-Python ML models & serialization
│   │   ├── train_sales_forecast.py # Model training & validation selection
│   │   └── evaluate_sales_forecast.py # Multi-metric evaluation engine
│   ├── services/                   # Background services & PDF ingestion
│   ├── tests/                      # 61 automated unit and integration tests
│   ├── db_schema.py                # Relational schema DDL definitions
│   ├── init_db.py                  # Database initialization script
│   ├── main.py                     # FastAPI server entry point
│   ├── requirements.txt            # Python dependencies
│   └── .env.example                # Safe environment variable template
│
├── frontend/                       # Next.js 14 Web Application
│   ├── src/
│   │   ├── app/                    # Next.js App Router (Dashboard, Query, Settings)
│   │   ├── components/             # React UI components & Recharts visualizations
│   │   └── lib/                    # API clients and utilities
│   ├── package.json                # Frontend dependencies
│   └── .env.example                # Frontend environment template
│
├── docs/                           # Architecture and phase audit reports
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── SQL_AGENT.md
│   ├── SALES_FORECASTING_DATA.md
│   ├── SALES_FORECASTING_MODEL.md
│   ├── PHASE_6A_REPORT.md
│   ├── PHASE_6B_REPORT.md
│   └── ...
├── .gitignore                      # Monorepo ignore rules (secrets, venvs, DBs)
└── README.md                       # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites
- **Python**: 3.11 or 3.12
- **Node.js**: 18+ and npm
- **API Keys** *(Optional for core UI/DB execution; required for AI agents)*:
  - OpenAI API Key (`OPENAI_API_KEY`)
  - Pinecone API Key (`PINECONE_API_KEY`)

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to provide your OpenAI and Pinecone API keys if testing agent generation.*

5. **Initialize database and seed business data**:
   ```bash
   python init_db.py
   python -m data.generate_business_data
   ```

6. **Start the FastAPI backend server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   *API Swagger documentation available at: `http://localhost:8000/docs`*

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env.local
   ```
   *Defaults to `NEXT_PUBLIC_API_URL=http://localhost:8000`.*

4. **Start Next.js development server**:
   ```bash
   npm run dev
   ```
   *Open `http://localhost:3000` in your browser.*

---

## 🧪 Testing

Run the full backend test suite (61 unit and integration tests):

```bash
cd backend
python -m unittest discover -s tests -p "test_*.py"
```

To run sales data preparation and forecasting tests specifically:
```bash
python -m unittest tests/test_sales_data_preparation.py tests/test_sales_forecast.py
```

---

## 🔒 Security & Safe Engineering

- **No Secrets in Source Control**: All `.env` and `.env.local` files containing secrets or private credentials are strictly excluded via `.gitignore`.
- **SQL AST Safety Validator**: Rejects destructive operations (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`), schema manipulations, and unauthorized tables before execution.
- **Isolated SQLite Execution**: Enforces read-only query semantics with strict query timeout guardrails.
- **Audit Trails**: Every SQL interaction is logged to `agent_audit_logs`.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
