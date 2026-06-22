# Agentic Architecture (LangGraph + Human-in-the-Loop)

This document describes the new production-grade architecture that runs
alongside the legacy single-shot pipeline in `main_app.py` / `api.py`.

## Why agentic?

The legacy pipeline runs all 21 AI checks in one Flask request, generates a
DOCX with comments, and returns it. There is no opportunity for a human to
veto an AI-suggested comment before it lands in the document. For a regulated
domain (DHF / GDP), that is unacceptable: every AI-authored comment must be
reviewed.

The agentic redesign solves this by modelling the workflow as a LangGraph
state machine that pauses at a checkpoint, exposes the AI's draft comments to
a human via REST, and only mutates the DOCX after explicit approval.

## Graph topology

```
        ┌────────────────┐
START ──▶ load_documents │  parse DOCX + template
        └──────┬─────────┘
               ▼
        ┌────────────────┐
        │  run_checks    │  fan-out 19 LLM checks in parallel (ThreadPool)
        └──────┬─────────┘
               ▼
        ┌────────────────┐
        │ draft_comments │  anchor findings to nearest heading,
        └──────┬─────────┘  produce DraftComment[] (status=pending)
               ▼
   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  HITL INTERRUPT
               ▼
        ┌────────────────────┐
        │ await_human_review │  no-op resume marker
        └──────┬─────────────┘
               ▼
        ┌────────────────┐
        │ apply_comments │  insert ONLY approved comments into the DOCX,
        └──────┬─────────┘  emit markdown report
               ▼
              END
```

## Files

| File | Purpose |
|---|---|
| `backend/agentic/config.py`   | Loads `.env`, exposes typed `Settings` |
| `backend/agentic/state.py`    | `AgentState` (TypedDict) + `DraftComment` |
| `backend/agentic/nodes.py`    | All graph nodes; reuses existing `ai_checks.py` |
| `backend/agentic/graph.py`    | Graph wiring + `MemorySaver` checkpointer |
| `backend/agentic_api.py`      | Flask REST API (port 5003) |
| `frontend/templates/review.html`   | HITL review UI |
| `frontend/static/js/agentic.js`    | Review controller |
| `frontend/static/css/agentic.css`  | Review styles |

## Human-in-the-loop mechanics

LangGraph compiles the graph with `interrupt_before=["await_human_review"]`
and a `MemorySaver` checkpointer. When the API calls `app.invoke(initial,
{"configurable": {"thread_id": session_id}})`:

1. Nodes `load_documents → run_checks → draft_comments` execute.
2. The graph stops *before* `await_human_review` and persists state.
3. `app.get_state(cfg).values["draft_comments"]` is what the API surfaces.
4. The reviewer approves / rejects / edits each comment via REST.
5. The API mutates state via `app.update_state(cfg, {"draft_comments": ...})`.
6. `app.invoke(None, cfg)` resumes from the checkpoint; only approved
   comments make it into the DOCX.

Any pending (unreviewed) comment is force-rejected on resume so unreviewed
AI text can never end up in a final document — a key compliance property.

## REST API

| Method | Path | Purpose |
|---|---|---|
| `POST`   | `/api/sessions` | Upload doc + template, start the agent |
| `GET`    | `/api/sessions/<sid>` | Status + progress |
| `GET`    | `/api/sessions/<sid>/comments` | Draft comments awaiting review |
| `PATCH`  | `/api/sessions/<sid>/comments/<cid>` | Single approve/reject/edit |
| `POST`   | `/api/sessions/<sid>/bulk` | Bulk decision update |
| `POST`   | `/api/sessions/<sid>/resume` | Continue the graph |
| `GET`    | `/api/sessions/<sid>/download/<artifact>` | `review_doc` \| `report_md` |
| `DELETE` | `/api/sessions/<sid>` | Cleanup |
| `GET`    | `/api/health` | Health probe |

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

## Local run

```powershell
# 1. install
cd backend
pip install -r requirements.txt

# 2. configure
cd ..
copy .env.example .env       # fill in real values

# 3. start everything
scripts\start-agentic.bat
```

Open <http://localhost:5000/review>.

## Production / Azure path

The architecture is deliberately Azure-friendly:

| Concern | Local | Azure (production) |
|---|---|---|
| LLM      | Azure OpenAI (already supported) | Azure OpenAI + Managed Identity |
| Checkpointer | `MemorySaver` | `langgraph-checkpoint-postgres` against Azure Database for PostgreSQL |
| File storage | `./.agent_workspace/<sid>/` | Azure Blob Storage (mounted or via SDK) |
| API host  | `python agentic_api.py` | App Service / Container Apps + `gunicorn` |
| Frontend  | `python app.py` | Azure Static Web Apps or App Service |
| Secrets   | `.env` | Key Vault references in App Service config |
| Auth      | none | Azure AD via App Service Easy Auth in front of `/api/*` |
| Telemetry | stdout | Application Insights via OpenTelemetry |

Switching the checkpointer is a one-line change in
`backend/agentic/graph.py`.

## Why each AI check is not its own node

Each of the 21 AI checks could be modelled as a discrete LangGraph node, but
that would inflate the graph without changing behaviour: the checks are
embarrassingly parallel and share no intermediate state. A single
`run_checks` node with a `ThreadPoolExecutor` keeps the graph readable while
preserving parallelism. If we later want per-check retries / circuit
breakers, those become natural per-check sub-graphs.
