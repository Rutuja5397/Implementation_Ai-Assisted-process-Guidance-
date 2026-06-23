# CLAUDE.md

This file provides guidance to Claude Code when working with the **Crane AI – Process Guidance Tool** prototype.

## What This System Is

An **AI-assisted industrial troubleshooting system** for crane maintenance engineers. It is NOT a chatbot — it is a structured, evidence-based diagnostic workflow tool.

Core principle: engineers provide structured intake data → AI retrieves relevant knowledge → AI guides step-by-step diagnosis → measurements are recorded → a traceable fault report is generated.

## Architecture

```
Streamlit Frontend (frontend/app.py)
        ↓ HTTP (REST)
FastAPI Backend (backend/main.py)
        ├── Auth (backend/auth.py)          – JWT + bcrypt
        ├── Session Manager (main.py)       – SQLite via SQLAlchemy
        ├── RAG System (backend/rag_system.py) – ChromaDB + sentence-transformers
        ├── AI Agent (backend/ai_agent.py)  – Claude claude-sonnet-4-6 via Anthropic API
        └── Report Generator (backend/report_generator.py) – AI-synthesised JSON report
```

**Database:** SQLite (`crane_ai.db`) — 7 tables: `users`, `sessions`, `messages`, `measurements`, `reports`, `knowledge_gaps`, `notifications`

**Vector store:** ChromaDB (persisted at `./chroma_db/`) — collection `crane_knowledge`

**Embedding model:** `all-MiniLM-L6-v2` (sentence-transformers, runs locally)

**LLM:** `claude-sonnet-4-6` via `anthropic` Python SDK

## Project Structure

```
Process Guidance /
├── backend/
│   ├── __init__.py
│   ├── database.py          # SQLAlchemy engine, SessionLocal, Base, init_db()
│   ├── models.py            # ORM models: User, TroubleshootingSession, Message, Measurement, Report
│   ├── schemas.py           # Pydantic v2 schemas for all request/response types
│   ├── auth.py              # hash_password, verify_password, JWT create/decode, user CRUD
│   ├── rag_system.py        # RAGSystem class: initialize(), reinitialize(), retrieve()
│   ├── ai_agent.py          # get_ai_response(), generate_opening_message(), build_system_prompt()
│   ├── report_generator.py  # generate_report() – calls Claude, returns models.Report
│   └── main.py              # FastAPI app – 39 endpoints (incl. resolve gap, notifications)
├── agents/                  # Multi-agent pipeline (AGT-02 through AGT-09)
│   ├── base_agent.py        # BaseAgent abstract class, AgentError
│   ├── intake_agent.py, retrieval_agent.py, diagnostic_agent.py
│   ├── parameter_agent.py, procedure_agent.py, safety_agent.py
│   ├── report_agent.py, knowledge_feedback_agent.py
├── orchestration/
│   └── session_orchestrator.py  # AGT-01: coordinates all agent pipelines
├── access_control/
│   ├── permissions.py       # ROLE_PERMISSIONS dict + permission constants
│   └── rbac.py              # require_role() / require_permission() FastAPI dependencies
├── frontend/
│   └── app.py               # Streamlit app – screens: login, intake, guidance, dashboard, admin
├── data/
│   └── knowledge_base/      # 9 .txt technical manual documents (indexed into ChromaDB)
│       ├── hoist_motor.txt, hoist_brake.txt, wire_rope.txt, gearbox.txt
│       ├── control_system.txt, limit_switch.txt, trolley_bridge_motor.txt
│       ├── hook_block.txt, power_supply.txt, general_procedures.txt
├── chroma_db/               # Auto-created: ChromaDB persistent storage
├── crane_ai.db              # Auto-created: SQLite database
├── .env                     # Local secrets (not committed)
├── .env.example             # Template
├── requirements.txt
└── start.sh
```

## Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
cp .env.example .env
# Edit .env → set ANTHROPIC_API_KEY=sk-ant-...

# 3a. Start backend (FastAPI)
uvicorn backend.main:app --reload --port 8000

# 3b. Start frontend (Streamlit) — in a second terminal
streamlit run frontend/app.py --server.port 8501

# Or use the combined script:
./start.sh

# Check backend is running
curl http://localhost:8000/health

# Backend API docs (auto-generated)
open http://localhost:8000/docs
```

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/signup` | Create user account |
| POST | `/auth/login` | Login → returns JWT |
| POST | `/sessions` | Create session from intake form + generates opening AI message |
| POST | `/sessions/{id}/chat` | Send engineer message, get AI response + evidence |
| POST | `/sessions/{id}/measurements` | Record a measurement |
| POST | `/sessions/{id}/report` | Generate final fault report via AI |
| GET | `/dashboard` | All sessions for current user (filterable) |
| GET | `/dashboard/stats` | Summary statistics |
| GET | `/reports/{id}` | Fetch a specific report |
| GET | `/knowledge-gaps` | Get knowledge gap records (KE, SME) |
| PUT | `/knowledge-gaps/{id}/resolve` | KE: update KB file + re-index + notify ME/SME |
| GET | `/notifications` | Get own notifications |
| GET | `/notifications/unread-count` | Get unread notification count |
| PUT | `/notifications/{id}/read` | Mark notification as read |
| PUT | `/notifications/read-all` | Mark all notifications as read |

## UI Screens

1. **Login / Signup** — JWT auth, stored in `st.session_state`
2. **Issue Intake Form** — Crane → Component → Problem → Optional context; creates session + triggers opening AI message
3. **AI Guidance Interface** — Chat panel (left) + Measurements / Evidence / Session State tabs (right); shows KB-updated banner if gap was resolved
4. **Crane Dashboard** — Session history, filters, embedded reports, charts; KE tab has gap editor
5. **Admin Panel** — User management, role assignment (ADM only)

## Important Behaviours

- **AI does not re-ask intake data.** The system prompt explicitly injects crane, component, problem, environment, recent changes, and error codes. The AI is instructed to start at diagnostic depth.
- **RAG is component-aware.** Retrieval queries ChromaDB with a `where` filter on `source` (component file) first (3 chunks), then falls back to general retrieval (2 chunks). Total 5 chunks per turn.
- **Session state is tracked in DB.** The AI returns a `{"session_update": {...}}` JSON block embedded in every response. `main.py` parses and writes `completed_steps`, `likely_causes`, and `current_hypothesis` to the `sessions` table.
- **Reports are AI-synthesised JSON.** `report_generator.py` sends full session transcript + measurements to Claude and parses a structured JSON report.
- **Knowledge Gap Resolution is in-app.** KE resolves gaps via an editor in the dashboard. On submit: `.txt` file is updated, `RAGSystem.reinitialize()` re-indexes ChromaDB, the session transitions KNOWLEDGE_GAP_FLAGGED → IN_PROGRESS, and ME/SME are notified.
- **Notifications are per-user.** The `notifications` table has one row per user per event. Unread count is shown as a badge on the bell icon in the top navigation bar.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *required* | Anthropic API key |
| `SECRET_KEY` | `crane-ai-default-secret-...` | JWT signing key — **change in production** |
| `DATABASE_URL` | `sqlite:///./crane_ai.db` | SQLAlchemy DB URL |
| `CHROMA_DB_PATH` | `./chroma_db` | ChromaDB persistence directory |
| `KNOWLEDGE_BASE_PATH` | `./data/knowledge_base` | Directory of .txt knowledge files |
| `BACKEND_URL` | `http://localhost:8000` | Used by Streamlit to call FastAPI |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | JWT token TTL (8 hours) |

## Adding Knowledge

To add a new component or crane manual:

1. Create a `.txt` file in `data/knowledge_base/` following the existing format (see `hoist_motor.txt` for structure)
2. Add the filename mapping in `backend/rag_system.py` → `COMPONENT_FILE_MAP`
3. Delete `./chroma_db/` to force re-indexing, then restart the backend

## Adding a New Crane Type

1. Add the crane name + component list to `CRANE_COMPONENTS` in `frontend/app.py`
2. No backend changes needed — crane type is a free-form string throughout

## Known Limitations (Prototype)

- ChromaDB is re-indexed on first startup only; deleting `chroma_db/` forces a fresh index
- No multi-user isolation of sessions across engineers (all sessions visible per user only)
- No file upload for custom manuals yet (knowledge base is static .txt files)
- No real-time streaming of AI responses (full response waits for completion)
- SQLite not suitable for production multi-user load; switch to PostgreSQL via `DATABASE_URL`

## Thesis Context

This prototype implements the **Process Guidance** component of an AI-assisted Knowledge Management system for crane maintenance (Master Thesis, RPTU / Fraunhofer IESE, 2025). It demonstrates:
- RAG-based retrieval of structured technical knowledge
- Structured intake → context snapshot → guided reasoning workflow
- Session traceability and report generation
- Multi-screen industrial UI appropriate for field engineers
