# Changelog - DataScout Backend API

All notable changes to the DataScout Backend API will be documented in this file.

---

## [1.0.0] - 2026-01-24

### 🎉 Initial Production Release

#### Added
- **Multi-Agent System**
  - Supervisor Agent with LangGraph orchestration
  - SQL Agent with natural language processing
  - RAG Agent with Pinecone integration  
  - Visualizer Agent with GPT-4o

- **API Endpoints** (15 total)
  - `/chat` - Multi-agent chat interface
  - `/api/analytics/summary` - Real-time metrics
  - `/api/history` - Query audit log
  - `/api/settings` - User preferences
  - `/api/documents/upload` - PDF upload with background processing

- **Services**
  - PDF ingestion service
  - Background task processing
  - Pinecone vector database integration

- **Database**
  - SQLite with 7 tables
  - Seed data (1000+ transactions)
  - Automatic migrations

#### Security
- SQL injection prevention
- Table-level access control
- Audit logging
- Environment variable validation

---

## [0.9.0] - 2026-01-23

### Added
- Initial agent implementations
- Basic API endpoints
- Database schema

---

[1.0.0]: https://github.com/yourusername/datascout-backend/releases/tag/v1.0.0
