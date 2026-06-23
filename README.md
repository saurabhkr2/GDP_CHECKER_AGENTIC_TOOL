# Document Quality Compliance Checker (Agentic)

A web-based application that performs automated quality checks on GDP-compliant
documents using an **agentic LangGraph pipeline with Human-in-the-Loop (HITL)
review**. Every AI-drafted comment must be approved by a human before it lands
in the final DOCX — a key compliance property for regulated (DHF / GDP) domains.

See [backend/AGENTIC_ARCHITECTURE.md](backend/AGENTIC_ARCHITECTURE.md) for the
full architecture.

---

## 🚀 Quick Start

```powershell
# 1. Configure credentials
copy .env.example .env          # fill in Azure OpenAI keys

# 2. Install backend dependencies
pip install -r backend\requirements.txt

# 3. Start the agentic backend (5003) + frontend (5000)
scripts\start-agentic.bat       # Windows
./scripts/start-agentic.sh      # macOS/Linux
```

- Backend health: http://localhost:5003/api/health
- Review UI: http://localhost:5000/

---

## 🔐 Login (LDAP)

The review UI is gated behind an LDAP/Active Directory login. On first visit
you are redirected to `http://localhost:5000/login`; sign in with your Philips
email + password. A successful bind creates a server-side session (stored in
Redis, with an in-memory fallback for local dev) and an httponly cookie.

- `POST /api/login` – authenticate, set session cookie
- `POST /api/logout` – destroy the session
- `GET  /api/me` – current logged-in user

Configure LDAP/session behaviour via `.env` (`LDAP_SERVER`, `LDAP_BASE`,
`SESSION_EXPIRE_SECONDS`, `REDIS_HOST`, …). Set `AUTH_ENABLED=0` to disable
login during local development.

---

## 🐳 Run with Docker

The whole stack (Redis + backend + frontend) runs via Docker Compose:

```powershell
copy .env.example .env          # fill in Azure OpenAI + LDAP values
docker compose up --build
```

Then open http://localhost:5000/ (you'll be sent to `/login` first).

> When serving over HTTPS or across different domains, set
> `SESSION_COOKIE_SECURE=1` and `SESSION_COOKIE_SAMESITE=none`, and update
> `CORS_ALLOWED_ORIGINS` / `AGENTIC_API_URL` to your real hostnames.

---

## How It Works

The workflow is modelled as a LangGraph state machine that pauses at a
checkpoint, exposes the AI's draft comments to a human via REST, and only
mutates the DOCX after explicit approval.

```
START → load_documents → run_checks → draft_comments
        ─ ─ ─ HITL INTERRUPT ─ ─ ─
        → await_human_review → apply_comments → END
```

1. Parse the DOCX + template.
2. Fan-out the AI/regex checks in parallel.
3. Anchor findings to nearest headings, producing draft comments (pending).
4. The graph **pauses** before applying anything.
5. A reviewer approves / rejects / edits each comment via the review UI.
6. The graph resumes; only approved comments are written into the DOCX.

Any unreviewed (pending) comment is force-rejected on resume, so unreviewed AI
text can never end up in a final document.

---

## 21 Quality Checks (10 Regex + 11 AI)

**Regex Checks (Deterministic):**
- **CHK01**: Placeholder text detection (TBD, TODO, etc.)
- **CHK03**: Undefined acronym detection
- **CHK08**: N/A justification presence
- **CHK10**: Date format consistency (DDMMMYYYY)
- **CHK15**: Double spaces detection
- **CHK19**: Table of contents validation
- **CHK20**: Brand name/terminology casing
- **CHK21**: Template leftover text
- **CHK23/25**: Figure and table numbering
- **CHK27**: Section numbering consistency
- **CHK29**: Risky modal verbs (can/may/might)

**AI Checks (Requires Azure OpenAI):**
- **AI01**: N/A justification adequacy
- **AI02**: Requirement testability
- **AI03**: Terminology consistency
- **AI04**: Revision history specificity
- **AI05**: Section completeness
- **AI06**: Requirement clarity
- **AI07**: Traceability links
- **AI08**: Design rationale
- **AI09**: Risk assessment
- **AI10**: Compliance verification
- **AI12**: Acronym definitions

---

## Architecture

| Process | Port | Purpose |
|---|---|---|
| Agentic Backend (`agentic_api.py`) | 5003 | LangGraph pipeline + HITL REST API |
| Frontend (`app.py`) | 5000 | Serves the review UI |

**Key Technologies:**
- Backend: Python 3.8+, Flask, LangGraph, Azure OpenAI, python-docx
- Frontend: Vanilla JavaScript ES6+, HTML5, CSS3
- Testing: pytest

## Project Structure

```
backend/
├── agentic_api.py            # Agentic REST API (port 5003)
├── agentic/
│   ├── config.py             # Settings loaded from .env
│   ├── state.py              # AgentState + DraftComment
│   ├── nodes.py              # Graph nodes
│   └── graph.py              # Graph wiring + checkpointer
├── monitoring/               # Usage tracking for IGTS AI Savings
│   ├── schema.py             # GDPCheckerUsageRecord dataclass
│   ├── storage.py            # SQLite persistence
│   ├── collector.py          # Session data collection
│   └── export.py             # CSV export utilities
├── ai_checks.py              # 21 quality check functions
├── ai_prompts.json           # AI check configurations
├── context_extractor.py      # Structured context pre-pass
├── doc_loader.py             # DOCX parsing
├── models.py                 # Data models (Finding, Report, etc.)
├── reporting.py              # Markdown report generation
├── docx_comment_writer.py    # Inline comment insertion
├── docx_summary_writer.py    # Heading-anchored summary comments
├── template_registry.json    # Template catalog
├── AGENTIC_ARCHITECTURE.md   # Architecture documentation
├── requirements.txt
└── tests/                    # Unit tests
frontend/
├── app.py                    # Flask UI server (port 5000)
├── templates/review.html     # HITL review UI
└── static/
    ├── js/agentic.js
    └── css/agentic.css
scripts/
└── start-agentic.bat / .sh   # Start backend + frontend
```

---

## Configuration (`.env`)

```ini
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT_PRIMARY=gpt-5.1
AZURE_OPENAI_DEPLOYMENT_SECONDARY=gpt-5
AGENTIC_API_PORT=5003
FRONTEND_PORT=5000
WORKSPACE_DIR=./.agent_workspace
```

## Testing

```bash
cd backend
pip install -r requirements-test.txt
pytest tests/ -v
```

## Security & Privacy

- **Human-in-the-loop**: No AI comment is applied without explicit approval.
- **Local processing**: Regex checks run locally without external API calls.
- **No data retention**: Documents are processed in per-session workspaces.

---

## 📊 Usage Monitoring (IGTS AI Savings)

The application tracks usage metrics for IGTS AI Savings reporting. Each completed session records:

| Field | Description |
|-------|-------------|
| `timestamp` | Session completion time |
| `reporting_month` | Month name for reporting (e.g., "June") |
| `user_email` | Logged-in user's email |
| `template_doc_name` | Template document filename |
| `draft_doc_name` | Draft document filename |
| `comments_generated` | Total AI comments generated |
| `paragraphs_analyzed` | Number of paragraphs processed |
| `comments_accepted` | Comments approved by reviewer |
| `comments_rejected` | Comments rejected by reviewer |
| `comments_modified` | Comments edited by reviewer |
| `ai_processing_time_sec` | Time spent on AI analysis |
| `human_review_time_sec` | Time spent on human review |
| `productivity_factor` | Multiplier for hours saved (default: 2.0) |
| `productivity_hours_saved` | Calculated hours saved (sessions × factor) |

### Configuration

```ini
# .env
GDP_CHECKER_MONITORING_DB=        # Path to SQLite DB (default: monitoring/data/usage.db)
GDP_CHECKER_PRODUCTIVITY_FACTOR=2.0  # Hours saved per session
```

### Export Data

```python
from monitoring import export_to_csv
export_to_csv("usage_report.csv", start_date="2026-01-01", end_date="2026-06-30")
```

---

## License

Proprietary - Philips Internal Use Only
