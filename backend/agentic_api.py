"""
Production-ready REST API for the agentic DHF review pipeline.

Endpoints
---------
POST /api/sessions                            create session, kick off graph (async)
GET  /api/sessions/<sid>                      session status + progress
GET  /api/sessions/<sid>/comments             draft comments awaiting review
PATCH /api/sessions/<sid>/comments/<cid>      approve / reject / edit a single comment
POST /api/sessions/<sid>/bulk                 bulk decisions {decisions: [{id, decision, edited_message?}]}
POST /api/sessions/<sid>/resume               resume the graph after review
GET  /api/sessions/<sid>/download/<artifact>  artifact in {review_doc, report_md}
DELETE /api/sessions/<sid>                    delete session + files
GET  /api/health                              health probe

Notes
-----
* Graph state is held in-process via LangGraph's MemorySaver. For multi-worker
  Azure deployments swap MemorySaver for the Postgres / Redis checkpointer in
  `agentic/graph.py` (one-line change).
* Long-running graph execution runs in a daemon thread per session so HTTP
  requests stay responsive.
"""
from __future__ import annotations

import os
import sys
import threading
import traceback
import uuid
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Make backend/ importable when running as a script.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from agentic.config import settings  # noqa: E402
from agentic.graph import get_app  # noqa: E402
from agentic.nodes import get_live_progress, node_clear_live_progress  # noqa: E402
from auth import register_auth  # noqa: E402

# Monitoring: capture usage metrics
_MONITORING_DIR = os.path.join(os.path.dirname(_BACKEND_DIR), "monitoring")
if _MONITORING_DIR not in sys.path:
    sys.path.insert(0, os.path.dirname(_MONITORING_DIR))
try:
    from monitoring import get_collector, get_storage
    _monitoring_collector = get_collector()
    print("[agentic_api] ✅ Monitoring enabled")
except ImportError as e:
    _monitoring_collector = None
    get_storage = None  # type: ignore
    print(f"[agentic_api] ⚠️ Monitoring disabled: {e}")

ALLOWED_EXT = {"docx"}


# Emails permitted to download the monitoring/usage report.
# Override with a comma-separated list via GDP_CHECKER_MONITORING_ADMINS.
_DEFAULT_MONITORING_ADMINS = [
    "partner.saurabh.kumar_1@philips.com",
    "ashima.arora@philips.com",
    "iswarya.nagappan@philips.com",
    "nishant.mishra_1@philips.com",
    "ivan.adanja@philips.com",
]
_MONITORING_ALLOWED_EMAILS = {
    e.strip().lower()
    for e in os.getenv(
        "GDP_CHECKER_MONITORING_ADMINS", ",".join(_DEFAULT_MONITORING_ADMINS)
    ).split(",")
    if e.strip()
}

# API key for machine-to-machine access to the monitoring data endpoints
# (dashboards, ETL jobs). Set GDP_CHECKER_MONITORING_API_KEY on the VM.
# When unset, the JSON data endpoints stay disabled (return 503) so data is
# never exposed without an explicit key.
_MONITORING_API_KEY = (os.getenv("GDP_CHECKER_MONITORING_API_KEY") or "").strip()


def _check_monitoring_api_key() -> bool:
    """Validate the API key from the Authorization or X-API-Key header."""
    if not _MONITORING_API_KEY:
        return False
    provided = (request.headers.get("X-API-Key") or "").strip()
    if not provided:
        auth_header = (request.headers.get("Authorization") or "").strip()
        if auth_header.lower().startswith("bearer "):
            provided = auth_header[7:].strip()
    if not provided:
        return False
    # Constant-time comparison to avoid timing attacks.
    import hmac
    return hmac.compare_digest(provided, _MONITORING_API_KEY)


def _allowed(name: str) -> bool:
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# ---------------------------------------------------------------------------
# Session bookkeeping
# ---------------------------------------------------------------------------
class SessionRegistry:
    """Tracks per-session metadata that doesn't belong in graph state.

    The authoritative graph state lives in the LangGraph checkpointer; we only
    cache lightweight info (status flag, thread handle, error) here.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: Dict[str, Dict[str, Any]] = {}

    def create(self, sid: str, workspace: str) -> Dict[str, Any]:
        with self._lock:
            self._items[sid] = {
                "status": "running",         # running | awaiting_review | resuming | done | error
                "error": None,
                "workspace": workspace,
                "thread": None,
            }
            return self._items[sid]

    def update(self, sid: str, **fields: Any) -> None:
        with self._lock:
            if sid in self._items:
                self._items[sid].update(fields)

    def get(self, sid: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._items.get(sid)

    def delete(self, sid: str) -> None:
        with self._lock:
            self._items.pop(sid, None)


REGISTRY = SessionRegistry()


def _summarise_pre_pass(pp):
    """Lightweight summary of the structured-context dict for the API."""
    if not pp:
        return None
    return {
        "template_id":         pp.get("template_id"),
        "authors":             pp.get("authors", []),
        "glossary_terms":      len(pp.get("glossary") or {}),
        "req_tags":            len(pp.get("req_tags") or []),
        "ver_tags":            len(pp.get("ver_tags") or []),
        "test_cases":          len(pp.get("test_cases") or []),
        "revision_entries":    len(pp.get("revision_history") or []),
    }


def _config_for(sid: str) -> Dict[str, Any]:
    return {"configurable": {"thread_id": sid}}


def _run_graph(sid: str, initial_state: Dict[str, Any]) -> None:
    """Invoke the graph until it either finishes or hits the HITL interrupt."""
    app_graph = get_app()
    cfg = _config_for(sid)
    try:
        # Streaming would let us push progress events; for simplicity we just
        # run to the next stop point and inspect the checkpoint afterwards.
        app_graph.invoke(initial_state, cfg)
        snap = app_graph.get_state(cfg)
        # If the graph stopped at an interrupt, `next` is non-empty.
        if snap.next:
            REGISTRY.update(sid, status="awaiting_review")
            # Monitoring: record findings and comments generated
            if _monitoring_collector:
                values = dict(snap.values or {})
                findings = values.get("findings", []) or []
                draft_comments = values.get("draft_comments", []) or []
                _monitoring_collector.record_findings(sid, findings)
                _monitoring_collector.record_comments_generated(sid, len(draft_comments))
        else:
            REGISTRY.update(sid, status="done")
            # Monitoring: complete session (no HITL review needed)
            if _monitoring_collector:
                _monitoring_collector.complete_session(sid, status="completed")
    except Exception as e:
        traceback.print_exc()
        REGISTRY.update(sid, status="error", error=str(e))
        # Monitoring: record error on initial run
        if _monitoring_collector:
            _monitoring_collector.complete_session(sid, status="error", error_message=str(e))


def _resume_graph(sid: str) -> None:
    app_graph = get_app()
    cfg = _config_for(sid)
    try:
        app_graph.invoke(None, cfg)  # `None` means: continue from checkpoint
        snap = app_graph.get_state(cfg)
        if snap.next:
            REGISTRY.update(sid, status="awaiting_review")
        else:
            REGISTRY.update(sid, status="done")
            # Monitoring: complete session after HITL review
            if _monitoring_collector:
                _monitoring_collector.complete_session(sid, status="completed")
    except Exception as e:
        traceback.print_exc()
        REGISTRY.update(sid, status="error", error=str(e))
        # Monitoring: record error
        if _monitoring_collector:
            _monitoring_collector.complete_session(sid, status="error", error_message=str(e))


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

    origins = settings.cors_origins
    CORS(
        app,
        resources={r"/api/*": {"origins": "*" if origins == "*" else [o.strip() for o in origins.split(",")]}},
        supports_credentials=True,
    )

    # LDAP login + session guard for all protected /api/* routes.
    register_auth(app)

    graph_app = get_app()  # warm the singleton

    # ---------- helpers ----------
    def _snapshot(sid: str):
        return graph_app.get_state(_config_for(sid))

    def _state_values(sid: str) -> Dict[str, Any]:
        snap = _snapshot(sid)
        return dict(snap.values or {})

    def _patch_state(sid: str, patch: Dict[str, Any]) -> None:
        graph_app.update_state(_config_for(sid), patch)

    # ---------- routes ----------
    @app.get("/api/health")
    def health():
        return jsonify({
            "ok": True,
            "llm_configured": settings.has_any_llm(),
            "azure": settings.has_azure(),
        })

    @app.get("/api/checks")
    def list_checks():
        """Phase-2: catalog the reviewer can use to pick checks for a job."""
        from agentic.nodes import CHECK_REGISTRY  # local import to avoid cycle
        import ai_checks as _ai_mod
        prompts = getattr(_ai_mod, "_AI_PROMPTS", {}) or {}
        out = []
        for cid, _fn, _kind, _needs_t, _needs_b in CHECK_REGISTRY:
            entry = prompts.get(cid, {}) or {}
            out.append({
                "id":                 cid,
                "display_name":       entry.get("display_name") or cid,
                "description":        entry.get("description", ""),
                "severity":           entry.get("severity", "Moderate"),
                "enabled_by_default": entry.get("enabled_by_default", True),
                "applies_to":         entry.get("applies_to", ["ANY"]),
            })
        return jsonify({"checks": out})

    @app.get("/api/templates")
    def list_templates():
        """Phase-2: serve the template registry to the UI."""
        from agentic.nodes import TEMPLATE_REGISTRY  # local import to avoid cycle
        return jsonify({"templates": TEMPLATE_REGISTRY})

    @app.post("/api/sessions")
    def create_session():
        if "document" not in request.files or "template" not in request.files:
            return jsonify({"error": "Both 'document' and 'template' files are required"}), 400
        doc = request.files["document"]
        tmpl = request.files["template"]
        if not (doc.filename and tmpl.filename):
            return jsonify({"error": "Empty filenames"}), 400
        if not _allowed(doc.filename) or not _allowed(tmpl.filename):
            return jsonify({"error": "Only .docx files are accepted"}), 400

        sid = uuid.uuid4().hex
        workspace = settings.workspace_dir / sid
        workspace.mkdir(parents=True, exist_ok=True)

        doc_name = secure_filename(doc.filename)
        tmpl_name = secure_filename(tmpl.filename)
        doc_path = workspace / doc_name
        tmpl_path = workspace / tmpl_name
        doc.save(doc_path)
        tmpl.save(tmpl_path)

        brand = request.form.get("brand", settings.brand)
        enabled_raw = request.form.get("enabled_checks", "")
        enabled = [c.strip() for c in enabled_raw.split(",") if c.strip()] if enabled_raw else []
        document_type = (request.form.get("document_type") or "").strip() or None
        # Phase-1 noise controls (optional). Defaults applied in node_draft_comments.
        min_severity = (request.form.get("min_severity") or "").strip() or None
        max_per_section_raw = (request.form.get("max_per_section") or "").strip()
        try:
            max_per_section = int(max_per_section_raw) if max_per_section_raw else None
        except ValueError:
            max_per_section = None

        initial: Dict[str, Any] = {
            "session_id": sid,
            "doc_path": str(doc_path),
            "template_path": str(tmpl_path),
            "doc_filename": doc_name,
            "template_filename": tmpl_name,
            "brand": brand,
            "enabled_checks": enabled,
            "workspace_dir": str(workspace),
            "errors": [],
            "progress": {"percent": 1, "label": "Queued", "stage": "pending"},
        }
        if document_type:
            initial["document_type"] = document_type
        if min_severity:
            initial["min_severity"] = min_severity
        if max_per_section is not None:
            initial["max_per_section"] = max_per_section

        REGISTRY.create(sid, str(workspace))

        # Monitoring: track session start
        if _monitoring_collector:
            # Get user email from:
            # 1. Form data (if frontend sends it)
            # 2. Auth module's current_user() (returns username which is email)
            # 3. Fallback to anonymous
            user_email = request.form.get("user_email", "")
            if not user_email:
                from auth import current_user
                user_email = current_user() or "anonymous@philips.com"
            _monitoring_collector.start_session(
                session_id=sid,
                user_email=user_email,
                document_name=doc_name,
                template_name=tmpl_name,
            )

        t = threading.Thread(target=_run_graph, args=(sid, initial), daemon=True)
        REGISTRY.update(sid, thread=t)
        t.start()
        return jsonify({"session_id": sid, "status": "running"}), 202

    @app.get("/api/sessions/<sid>")
    def get_session(sid: str):
        meta = REGISTRY.get(sid)
        if not meta:
            return jsonify({"error": "unknown session"}), 404
        values = _state_values(sid)
        # Live progress from the running node takes priority over the last
        # checkpointed progress so the UI sees real-time updates.
        live = get_live_progress(sid) or {}
        progress = dict(values.get("progress", {}) or {})
        if live:
            progress.update({
                "percent": live.get("percent", progress.get("percent", 0)),
                "label":   live.get("label",   progress.get("label", "")),
                "stage":   live.get("stage",   progress.get("stage", "")),
            })
        return jsonify({
            "session_id": sid,
            "status": meta["status"],
            "error": meta.get("error"),
            "progress": progress,
            "live": {
                "completed": live.get("completed"),
                "total":     live.get("total"),
                "in_flight": live.get("in_flight", []),
            } if live else None,
            "findings_count": len(values.get("findings", []) or []),
            "draft_comment_count": len(values.get("draft_comments", []) or []),
            "document_type": values.get("document_type"),
            "template_match": values.get("template_match"),
            "pre_pass_summary": _summarise_pre_pass(values.get("pre_pass")),
            "errors": values.get("errors", []),
            "has_review_doc": bool(values.get("review_doc_path")),
            "has_report_md": bool(values.get("report_md_path")),
        })

    @app.get("/api/sessions/<sid>/comments")
    def list_comments(sid: str):
        if not REGISTRY.get(sid):
            return jsonify({"error": "unknown session"}), 404
        values = _state_values(sid)
        return jsonify({
            "draft_comments": values.get("draft_comments", []),
            "headings": values.get("headings", []),
        })

    def _apply_decision(sid: str, decisions: list) -> tuple:
        values = _state_values(sid)
        drafts = list(values.get("draft_comments", []) or [])
        if not drafts:
            return (jsonify({"error": "no draft comments to update"}), 400)
        by_id = {d["id"]: d for d in drafts}
        updated = 0
        for entry in decisions:
            cid = entry.get("id")
            if cid not in by_id:
                continue
            decision = entry.get("decision")
            if decision not in ("approved", "rejected", "pending"):
                continue
            by_id[cid]["decision"] = decision
            if "edited_message" in entry and isinstance(entry["edited_message"], str):
                by_id[cid]["edited_message"] = entry["edited_message"]
            if "rationale" in entry and isinstance(entry["rationale"], str):
                by_id[cid]["rationale"] = entry["rationale"]
            updated += 1
        _patch_state(sid, {"draft_comments": drafts})
        return (jsonify({"updated": updated, "total": len(drafts)}), 200)

    @app.patch("/api/sessions/<sid>/comments/<cid>")
    def patch_comment(sid: str, cid: str):
        if not REGISTRY.get(sid):
            return jsonify({"error": "unknown session"}), 404
        body = request.get_json(silent=True) or {}
        body["id"] = cid
        return _apply_decision(sid, [body])

    @app.post("/api/sessions/<sid>/bulk")
    def bulk_decisions(sid: str):
        if not REGISTRY.get(sid):
            return jsonify({"error": "unknown session"}), 404
        body = request.get_json(silent=True) or {}
        decisions = body.get("decisions") or []
        if not isinstance(decisions, list):
            return jsonify({"error": "'decisions' must be a list"}), 400
        return _apply_decision(sid, decisions)

    @app.post("/api/sessions/<sid>/resume")
    def resume(sid: str):
        meta = REGISTRY.get(sid)
        if not meta:
            return jsonify({"error": "unknown session"}), 404
        if meta["status"] not in ("awaiting_review", "error"):
            return jsonify({"error": f"cannot resume from status '{meta['status']}'"}), 409
        REGISTRY.update(sid, status="resuming", error=None)
        # Mark any still-pending comments as rejected by default so the user
        # cannot accidentally publish unreviewed AI text.
        values = _state_values(sid)
        drafts = list(values.get("draft_comments", []) or [])
        for d in drafts:
            if d.get("decision") == "pending":
                d["decision"] = "rejected"
        
        # Monitoring: record review decisions before resuming
        if _monitoring_collector:
            approved = sum(1 for d in drafts if d.get("decision") == "approved")
            rejected = sum(1 for d in drafts if d.get("decision") == "rejected")
            edited = sum(1 for d in drafts if d.get("edited_message"))
            _monitoring_collector.record_review(sid, approved=approved, rejected=rejected, edited=edited)
        
        _patch_state(sid, {"draft_comments": drafts, "decisions_complete": True})
        t = threading.Thread(target=_resume_graph, args=(sid,), daemon=True)
        REGISTRY.update(sid, thread=t)
        t.start()
        return jsonify({"status": "resuming"}), 202

    @app.get("/api/sessions/<sid>/download/<artifact>")
    def download(sid: str, artifact: str):
        if not REGISTRY.get(sid):
            return jsonify({"error": "unknown session"}), 404
        values = _state_values(sid)
        path_key = {"review_doc": "review_doc_path", "report_md": "report_md_path"}.get(artifact)
        if not path_key:
            return jsonify({"error": "unknown artifact"}), 400
        path = values.get(path_key)
        if not path or not os.path.exists(path):
            return jsonify({"error": "artifact not ready"}), 404
        return send_file(path, as_attachment=True, download_name=os.path.basename(path))

    @app.get("/api/monitoring/export")
    def monitoring_export():
        """Export all captured usage metrics as a downloadable Excel workbook."""
        if not _monitoring_collector:
            return jsonify({"error": "monitoring disabled"}), 503
        from auth import current_user  # local import to avoid cycle
        user = (current_user() or "").strip().lower()
        if user not in _MONITORING_ALLOWED_EMAILS:
            return jsonify({"error": "forbidden"}), 403
        period = request.args.get("period") or None
        try:
            from monitoring import export_to_excel
        except ImportError:
            return jsonify({"error": "monitoring export unavailable"}), 503

        import tempfile
        from datetime import datetime

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{period}" if period else ""
        fname = f"GDP_Checker_Usage{suffix}_{stamp}.xlsx"
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.close()
        try:
            export_to_excel(tmp.name, period_month=period)
        except RuntimeError as e:
            os.unlink(tmp.name)
            return jsonify({"error": str(e)}), 500
        return send_file(
            tmp.name,
            as_attachment=True,
            download_name=fname,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ---- Machine-to-machine data API (dashboards / ETL) --------------------
    @app.get("/api/monitoring/usage")
    def monitoring_usage():
        """Raw per-session usage records as JSON. API-key protected.

        Auth: send `X-API-Key: <key>` or `Authorization: Bearer <key>`.
        Query params:
          period  filter by month name (e.g. "June")
          user    filter by user_email
          limit   max rows to return (default 1000, max 10000)
          offset  rows to skip for pagination (default 0)
        """
        if not _monitoring_collector or get_storage is None:
            return jsonify({"error": "monitoring disabled"}), 503
        if not _check_monitoring_api_key():
            return jsonify({"error": "invalid or missing API key"}), 401

        storage = get_storage()
        period = request.args.get("period") or None
        user = request.args.get("user") or None

        try:
            limit = min(max(int(request.args.get("limit", 1000)), 1), 10000)
        except ValueError:
            limit = 1000
        try:
            offset = max(int(request.args.get("offset", 0)), 0)
        except ValueError:
            offset = 0

        if period:
            records = storage.get_records_by_period(period)
        elif user:
            records = storage.get_records_by_user(user)
        else:
            records = storage.get_all_records(limit=10000)

        total = len(records)
        page = records[offset:offset + limit]
        return jsonify({
            "total": total,
            "count": len(page),
            "limit": limit,
            "offset": offset,
            "records": [r.to_dict() for r in page],
        })

    @app.get("/api/monitoring/summary")
    def monitoring_summary():
        """Aggregated usage totals as JSON. API-key protected."""
        if not _monitoring_collector or get_storage is None:
            return jsonify({"error": "monitoring disabled"}), 503
        if not _check_monitoring_api_key():
            return jsonify({"error": "invalid or missing API key"}), 401
        storage = get_storage()
        return jsonify(storage.get_summary_stats())

    @app.delete("/api/sessions/<sid>")
    def delete_session(sid: str):
        meta = REGISTRY.get(sid)
        if not meta:
            return jsonify({"error": "unknown session"}), 404
        ws = meta.get("workspace")
        REGISTRY.delete(sid)
        node_clear_live_progress(sid)
        if ws and os.path.isdir(ws):
            import shutil
            shutil.rmtree(ws, ignore_errors=True)
        return jsonify({"deleted": sid})

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"[agentic_api] listening on :{settings.api_port}  azure={settings.has_azure()}  llm={settings.has_any_llm()}")
    app.run(host="0.0.0.0", port=settings.api_port, debug=False, threaded=True)
