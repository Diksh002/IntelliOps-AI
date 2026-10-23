# DataScout Backend API

> **FastAPI Multi-Agent Backend**  
> Version 1.0.0 | Production Ready

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

AI-powered multi-agent backend for intelligent data analysis, natural language SQL queries, document search, and dynamic visualization.

---

## Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API Key
- Pinecone API Key

### Installation

```bash
# Clone repository
git clone https://github.com/MBilalKhanAI/DataScout-backend.git
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys

# Initialize database
python init_db.py

# Run server
uvicorn main:app --reload
```

**API will be available at:** http://localhost:8000

**API Documentation:** http://localhost:8000/docs

---

## Multi-Agent System

### Supervisor Agent
- **Purpose:** Intelligent query routing using LangGraph
- **Model:** GPT-4o with structured output
- **Routes to:** SQL Agent, RAG Agent, or Clarify

### SQL Agent
- **Purpose:** Natural language to SQL conversion
- **Features:** Table restrictions, audit logging, structured data extraction
- **Model:** GPT-4o with LangChain SQL agent

### RAG Agent
- **Purpose:** Document search and retrieval
- **Features:** Pinecone vector database, source citation
- **Model:** GPT-4o with text-embedding-3-large (1024 dims)

### Visualizer Agent
- **Purpose:** Automatic chart generation from data
- **Features:** Intelligent chart type selection, Recharts config
- **Model:** GPT-4o with structured output

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/chat` | POST | Main chat with agent routing |
| `/api/analytics/summary` | GET | Real-time metrics |
| `/api/history` | GET | Query history (last 50) |
| `/api/settings` | GET/POST | User preferences |
| `/api/documents` | GET | List documents |
| `/api/documents/upload` | POST | Upload PDF (background ingestion) |
| `/api/agents/execute` | POST | Execute specific agent |
| `/api/agents/custom` | GET/POST/DELETE | Custom agent CRUD |

**API Documentation:** See endpoint descriptions above or check `/docs` when server is running (FastAPI auto-generates interactive API docs)

---

## Configuration

Create `.env` file:

```env
# OpenAI
OPENAI_API_KEY=sk-proj-your-key-here

# Pinecone
PINECONE_API_KEY=pcsk_your-key-here
PINECONE_INDEX_NAME=datascout
PINECONE_HOST=https://datascout-xxxxx.svc.aped-4627-b74a.pinecone.io

# Optional: LangSmith Tracing
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=lsv2_pt_your-key-here
LANGCHAIN_PROJECT=datascout-enterprise
```

---

## Project Structure

```
backend/
├── agents/                    # AI Agent Implementations
│   ├── supervisor.py         # LangGraph orchestrator (303 lines)
│   ├── sql_agent.py          # SQL query agent (237 lines)
│   ├── rag_agent.py          # Document search (172 lines)
│   ├── visualizer_agent.py   # Chart generator (212 lines)
│   └── graph.py              # LangGraph workflow
│
├── services/                  # Business Logic
│   └── ingestion.py          # PDF processing (195 lines)
│
├── tests/                     # Test Suite (8 files)
│   ├── test_supervisor.py
│   ├── test_sql_agent.py
│   ├── test_rag_agent.py
│   └── test_visualizer.py
│
├── main.py                    # FastAPI Application (556 lines)
├── init_db.py                # Database initialization
├── requirements.txt          # Dependencies
├── .env.example              # Environment template
└── datascout.db              # SQLite database (auto-created)
```

---

## 🗄️ Database Schema

```sql
-- Core Tables
documents (id, name, size, upload_date, status, entities_count)
agent_logs (id, agent_name, query, status, timestamp, duration_ms)
query_audit (id, timestamp, query, result)
custom_agents (id, name, description, system_prompt, tools, created_at)
user_settings (key PRIMARY KEY, value, updated_at)

-- Seed Data
transactions (1000 rows) - Sample financial data
payroll (3 rows) - Sample employee data
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python tests/test_supervisor.py

# Test with coverage
pytest --cov=agents tests/
```

**Coverage:** 70%

---

## Security Features

- ✅ SQL injection prevention (parameterized queries)
- ✅ Table-level access control (transactions, payroll only)
- ✅ Audit logging for all queries
- ✅ Environment variable validation
- ✅ Error handling with detailed logging

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python init_db.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Google Cloud Run

```bash
gcloud run deploy datascout-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 📊 Performance

| Operation | Avg Time |
|-----------|----------|
| SQL Query | ~800ms |
| RAG Search | ~1200ms |
| Chart Generation | ~400ms |
| Document Upload | 2-5s (background) |

---

## 🔗 Frontend Integration

**Frontend Repo:** [DataScout-frontend](https://github.com/MBilalKhanAI/DataScout-frontend)

**API URL:** Set in frontend `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 📝 Dependencies

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
langchain>=0.1.0
langchain-openai>=0.0.2
langchain-pinecone>=0.0.1
pinecone-client>=3.0.0
python-dotenv>=1.0.0
pypdf>=3.17.0
tiktoken>=0.5.0
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

## 📧 Contact

- **Email:** drmbilal172@gmail.com
- **GitHub:** [@MBilalKhanAI](https://github.com/MBilalKhanAI)
- **LinkedIn:** [Muhammad Bilal Khan](https://www.linkedin.com/in/muhammad-bilal-khan-885ai654)

---

**Built with FastAPI, LangChain, LangGraph, and GPT-4o**
