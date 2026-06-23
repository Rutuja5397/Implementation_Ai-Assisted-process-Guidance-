# AI-Assisted Process Guidance Tool

A structured, role-based diagnostic workflow system for crane maintenance engineers.
Built as a Master's Thesis prototype at RPTU / Fraunhofer IESE, 2025.

---

## What It Does

Field engineers report a crane fault through a structured intake form. The AI retrieves
relevant knowledge from technical manuals and guides the engineer step by step through
diagnosis — asking targeted questions, interpreting measurements, and tracking progress.
When a fault is resolved, a structured fault report is generated automatically.

Senior engineers can review escalated cases, annotate diagnoses, and flag missing
knowledge. A Knowledge Engineer resolves gaps by updating the knowledge base in-app,
which re-indexes automatically and notifies the original engineers.

---

## Requirements

- Python 3.10 or higher
- An Anthropic API key ([get one here](https://console.anthropic.com))
- Internet connection (for Claude API calls)

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Rutuja5397/Process-Guidance.git
cd Process-Guidance
git checkout v2-implementation
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure your API key

```bash
cp .env.example .env
```

Open `.env` and set your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Leave all other values as they are for local use.

### 4. Create demo users

```bash
python3 demo_prep.py
```

This creates the following accounts in the local database:

| Role | Username | Password |
|------|----------|----------|
| ME — Field Engineer | `alice` | `test123` |
| SME — Senior Engineer | `bob` | `test123` |
| KE — Knowledge Engineer | `demo_ke` | `demo1234` |
| SUP — Supervisor | `demo_sup` | `demo1234` |
| ADM — Administrator | `carol` | `test123` |

### 5. Start the application

**Option A — Combined script (recommended):**

```bash
./start.sh
```

**Option B — Two separate terminals:**

```bash
# Terminal 1 — Backend (FastAPI)
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend (Streamlit)
streamlit run frontend/app.py --server.port 8501
```

### 6. Open the app

```
http://localhost:8501
```

---

## User Roles

| Role | What They Can Do |
|------|-----------------|
| **ME** — Maintenance Engineer | Fill intake form, follow AI guided diagnosis, record measurements, escalate to SME, generate fault report |
| **SME** — Senior Engineer | Review escalated sessions, add expert annotations, continue diagnosis, flag knowledge gaps |
| **KE** — Knowledge Engineer | View flagged knowledge gaps, update knowledge base files in-app, resolve gaps |
| **SUP** — Supervisor | Read-only view of all sessions across all engineers |
| **ADM** — Administrator | Manage users, assign roles, view audit log |

---

## Key Features

- **Structured intake form** — crane type, component, fault description, environment, recent changes, error codes
- **RAG-based guidance** — AI answers grounded in component-specific technical manuals, not general knowledge
- **Structured question widgets** — Yes/No radio buttons, number inputs with units, multiple choice dropdowns
- **AI confidence indicator** — AI self-reports when knowledge base coverage is low; SME sees automatic warning
- **Known fault lookup** — if the same fault was resolved before, the previous report is shown first
- **Diagnostic phase progress** — Intake → Investigation → Root Cause → Resolution
- **Measurement recording** — voltage, current, temperature, brake gap, insulation resistance
- **AI-generated fault report** — structured JSON report with root cause, steps, recommendations, severity
- **Escalation workflow** — ME escalates to SME with full session history preserved
- **Knowledge gap resolution** — KE updates knowledge base in-app; system re-indexes automatically
- **Audit trail** — every action logged for compliance

---

## Project Structure

```
Process Guidance/
├── backend/
│   ├── main.py              # FastAPI app — all API endpoints
│   ├── ai_agent.py          # Claude integration + RAG retrieval
│   ├── rag_system.py        # ChromaDB vector store
│   ├── auth.py              # JWT authentication
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── database.py          # SQLite database setup
│   └── report_generator.py  # AI-generated fault report
├── frontend/
│   └── app.py               # Streamlit UI — all screens
├── agents/                  # Multi-agent pipeline components
├── orchestration/           # Session orchestrator
├── access_control/          # Role-based permissions
├── data/
│   └── knowledge_base/      # Technical manual .txt files (indexed into ChromaDB)
├── diagrams/                # PlantUML architecture diagrams
├── .env.example             # Environment variable template
├── requirements.txt
├── demo_prep.py             # Creates demo user accounts
└── start.sh                 # Combined startup script
```

---

## Adding Knowledge

To add a new component or extend an existing manual:

1. Create or edit a `.txt` file in `data/knowledge_base/`
2. Follow the existing format (see `hoist_motor.txt` for structure)
3. Delete `chroma_db/` to force re-indexing:
   ```bash
   rm -rf chroma_db/
   ```
4. Restart the backend — it will re-index automatically on startup

Alternatively, use the **Knowledge Engineer role** in the app to update files directly
without touching the file system.

---

## Adding a New Crane Type

Edit `CRANE_COMPONENTS` in `frontend/app.py`:

```python
CRANE_COMPONENTS = {
    "Your Crane Model": ["Component 1", "Component 2", ...],
    ...
}
```

No backend changes needed.

---

## API Documentation

Once the backend is running, the auto-generated API docs are at:

```
http://localhost:8000/docs
```

---

## Known Limitations (Prototype)

- SQLite is used for simplicity — not suitable for production multi-user load
- Knowledge base is manually written for demonstration purposes — not validated by certified engineers
- AI responses should not be acted upon without qualified engineer oversight
- No real-time streaming of AI responses — full response waits for completion
- ChromaDB and SQLite data is local — not suitable for multi-machine deployment without persistent storage

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Backend | FastAPI |
| Database | SQLite via SQLAlchemy |
| Vector Store | ChromaDB |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| LLM | Claude (claude-sonnet-4-6) via Anthropic API |
| Auth | JWT + bcrypt |

---

## Thesis Context

This prototype implements the **Process Guidance** component of an AI-assisted
Knowledge Management system for crane maintenance engineers.

Master's Thesis — RPTU Kaiserslautern-Landau / Fraunhofer IESE, 2025.
