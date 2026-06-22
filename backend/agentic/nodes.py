"""
LangGraph nodes for the DHF agentic review pipeline.

Each node receives the AgentState and returns a partial dict of fields to
merge back. Nodes are intentionally small and pure-ish so they are easy to
reason about, test, and recompose.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

# Make the backend package importable when running as a script.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from doc_loader import load_docx  # noqa: E402
from models import Finding, Report  # noqa: E402
from reporting import build_markdown  # noqa: E402
from docx_comment_writer import add_comment_to_word  # noqa: E402
import ai_checks as _ai  # noqa: E402
import context_extractor as _ctx  # noqa: E402

from .config import settings
from .state import AgentState, DraftComment

# --------------------------------------------------------------------------- #
# Template registry (Phase 2)
# --------------------------------------------------------------------------- #
import json as _json
_TEMPLATE_REGISTRY_PATH = os.path.join(_BACKEND_DIR, "template_registry.json")
try:
    with open(_TEMPLATE_REGISTRY_PATH, "r", encoding="utf-8") as _f:
        TEMPLATE_REGISTRY: Dict[str, Dict[str, Any]] = _json.load(_f)
except Exception as _e:
    print(f"[agentic] WARNING: could not load template_registry.json: {_e}")
    TEMPLATE_REGISTRY = {}


# --------------------------------------------------------------------------- #
# Live progress (read by the API while the run_checks node is executing).
# LangGraph only persists state on node return, so we expose a side-channel.
# --------------------------------------------------------------------------- #
LIVE_PROGRESS: Dict[str, Dict[str, Any]] = {}
_LIVE_LOCK = threading.Lock()


def get_live_progress(session_id: str) -> Dict[str, Any] | None:
    with _LIVE_LOCK:
        snap = LIVE_PROGRESS.get(session_id)
        return dict(snap) if snap else None


def _set_live(session_id: str, **fields: Any) -> None:
    with _LIVE_LOCK:
        cur = LIVE_PROGRESS.setdefault(session_id, {})
        cur.update(fields)


def _clear_live(session_id: str) -> None:
    with _LIVE_LOCK:
        LIVE_PROGRESS.pop(session_id, None)


# --------------------------------------------------------------------------- #
# Per-check wall-clock budget. A stuck Azure call would otherwise block the
# `as_completed` loop until its 180 s SDK timeout fires.
# --------------------------------------------------------------------------- #
PER_CHECK_TIMEOUT_SECONDS = int(os.getenv("AGENT_PER_CHECK_TIMEOUT", "120"))


# Checks empirically known to be slow (chunked + multiple LLM calls). When
# AGENT_FAST_MODE=1 we skip them by default to keep wall-clock time down.
SLOW_CHECKS = {
    "AI05_SpellingGrammar",      # chunked, every chunk
    "AI06_TemplateCompliance",   # 25 KB chunks × per-chunk template re-send
    "AI15_RiskyModals",          # chunked
    "AI18_BrandCasing",          # chunked
}
FAST_MODE = os.getenv("AGENT_FAST_MODE", "0") in ("1", "true", "True")

# --------------------------------------------------------------------------- #
# Phase-1 noise controls (defaults; overridable per-job via AgentState)
# --------------------------------------------------------------------------- #
DEFAULT_MIN_SEVERITY = os.getenv("AGENT_MIN_SEVERITY", "Moderate")
DEFAULT_MAX_PER_SECTION = int(os.getenv("AGENT_MAX_PER_SECTION", "5"))


# --------------------------------------------------------------------------- #
# Check registry
# --------------------------------------------------------------------------- #
# (check_id, callable, model_kind, needs_template, extra_arg)
# model_kind: "primary" -> AZURE_OPENAI_DEPLOYMENT_PRIMARY, "secondary" -> ..._SECONDARY
_PRIMARY = "primary"
_SECONDARY = "secondary"

CHECK_REGISTRY: List[Tuple[str, Any, str, bool, bool]] = [
    # (id, fn, model_kind, needs_template, needs_brand)
    ("AI01_NA_Justification",     _ai.ai_check_na_justification,        _PRIMARY,   False, False),
    ("AI02_Testability",          _ai.ai_check_requirement_testability, _PRIMARY,   False, False),
    ("AI03_Terminology",          _ai.ai_check_terminology_consistency, _PRIMARY,   False, True),
    ("AI04_RevisionSpecificity",  _ai.ai_check_revision_specificity,    _PRIMARY,   False, False),
    ("AI05_SpellingGrammar",      _ai.ai_check_spelling_grammar,        _PRIMARY,   False, False),
    ("AI06_TemplateCompliance",   _ai.ai_check_template_compliance,     _PRIMARY,   True,  False),
    ("AI07_OpenIssues",           _ai.ai_check_open_issues,             _PRIMARY,   False, False),
    ("AI08_TestVerdicts",         _ai.ai_check_test_verdicts,           _PRIMARY,   False, False),
    ("AI09_TestTraceability",     _ai.ai_check_test_traceability,       _PRIMARY,   False, False),
    ("AI10_Authorship",           _ai.ai_check_authorship,              _PRIMARY,   False, False),
    ("AI11_ExternalFilesQMS",     _ai.ai_check_external_files_qms,      _PRIMARY,   False, False),
    ("AI12_AcronymDefinitions",   _ai.ai_check_acronym_definitions,     _SECONDARY, False, False),
    ("AI13_DateFormat",           _ai.ai_check_date_format,             _PRIMARY,   False, False),
    ("AI14_DoubleSpaces",         _ai.ai_check_double_spaces,           _PRIMARY,   False, False),
    ("AI15_RiskyModals",          _ai.ai_check_risky_modals,            _PRIMARY,   False, False),
    ("AI16_FiguresTables",        _ai.ai_check_figures_tables,          _PRIMARY,   False, False),
    ("AI17_Placeholders",         _ai.ai_check_placeholders,            _PRIMARY,   False, False),
    ("AI18_BrandCasing",          _ai.ai_check_brand_casing,            _SECONDARY, False, True),
    ("AI19_SectionNumbering",     _ai.ai_check_section_numbering,       _PRIMARY,   False, False),
]


def _resolve_model(kind: str) -> str:
    return settings.deployment_secondary if kind == _SECONDARY else settings.deployment_primary


def _make_clients() -> Dict[str, Any]:
    # Re-use the existing init helper. It honours Azure when env is set.
    # We also patch the legacy module-level constants from .env so legacy
    # callers in ai_checks pick up the right endpoint/key.
    if settings.has_azure():
        _ai.AZURE_OPENAI_ENDPOINT = settings.azure_endpoint  # type: ignore[attr-defined]
        _ai.AZURE_OPENAI_API_KEY = settings.azure_api_key    # type: ignore[attr-defined]
        _ai.AZURE_OPENAI_API_VERSION = settings.azure_api_version  # type: ignore[attr-defined]
    api_key = settings.azure_api_key or settings.openai_api_key
    return {
        _PRIMARY: _ai.init_openai_client(api_key, settings.deployment_primary, False),
        _SECONDARY: _ai.init_openai_client(api_key, settings.deployment_secondary, False),
    }


# --------------------------------------------------------------------------- #
# Heading anchoring
# --------------------------------------------------------------------------- #

def _nearest_heading(headings_with_offset: List[Tuple[int, str]], text: str, evidence: str) -> str:
    """Find the heading that immediately precedes the evidence in the document."""
    if not evidence or not headings_with_offset:
        return ""
    pos = text.find(evidence[:80]) if evidence else -1
    if pos < 0:
        return headings_with_offset[0][1] if headings_with_offset else ""
    best = headings_with_offset[0][1]
    for offset, h in headings_with_offset:
        if offset <= pos:
            best = h
        else:
            break
    return best


def _heading_offsets(raw_text: str, headings: List[str]) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    cursor = 0
    for h in headings:
        idx = raw_text.find(h, cursor)
        if idx >= 0:
            out.append((idx, h))
            cursor = idx + len(h)
    return out


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #

def _empty_cell_findings(work) -> List[Dict[str, Any]]:
    """Convert per-cell empty detections from doc_loader into Finding dicts so
    they flow through the same draft / review pipeline as LLM findings.

    This is the structural pre-pass that lets us say 'TC-002 row, Verdict
    column is empty' instead of letting the LLM say 'section appears empty'.
    """
    out: List[Dict[str, Any]] = []
    for ec in (getattr(work, "empty_cells", None) or []):
        msg = (f"Table {ec['table_index'] + 1}, row {ec['row']}: "
               f"column '{ec['column_name']}' is empty.")
        out.append(asdict(Finding(
            check_id="STRUCT_EMPTY_CELL",
            severity="Moderate",
            message=msg,
            evidence=msg,
            section=ec.get("nearest_heading") or None,
        )))
    return out


def node_load_documents(state: AgentState) -> Dict[str, Any]:
    """Parse the uploaded DOCX + template, emit structural findings, and run
    the Phase-2 pre-pass to extract glossary, tags, test cases, etc.

    The structured context dict is later injected at the top of every LLM
    prompt so the model is grounded with authoritative facts instead of
    having to find them in flat text.
    """
    work = load_docx(state["doc_path"])
    tmpl = load_docx(state["template_path"])
    structural = _empty_cell_findings(work)

    pre_pass = _ctx.extract_context(work)
    template_match = _check_template(pre_pass.get("template_id"),
                                     state.get("document_type"))

    print(f"[agentic] pre-pass: template_id={pre_pass.get('template_id')!r} "
          f"authors={len(pre_pass.get('authors') or [])} "
          f"glossary={len(pre_pass.get('glossary') or {})} "
          f"req_tags={len(pre_pass.get('req_tags') or [])} "
          f"ver_tags={len(pre_pass.get('ver_tags') or [])} "
          f"test_cases={len(pre_pass.get('test_cases') or [])} "
          f"rev_history={len(pre_pass.get('revision_history') or [])}")
    if template_match:
        print(f"[agentic] template match: {template_match}")
    if structural:
        print(f"[agentic] structural pre-pass: {len(structural)} empty-cell findings")

    return {
        "raw_text": work.raw_text,
        "template_text": tmpl.raw_text,
        "headings": work.headings,
        "findings": structural,   # seed; node_run_checks will append more
        "pre_pass": pre_pass,
        "template_match": template_match,
        "progress": {"percent": 10, "label": "Documents loaded", "stage": "loading"},
    }


def _check_template(found_id: str | None, document_type: str | None) -> Dict[str, Any]:
    """Look up the discovered template_id in the registry and return a small
    status dict the UI can render and the apply node can include in the
    Markdown report."""
    info: Dict[str, Any] = {"found_id": found_id, "document_type": document_type}
    if not found_id:
        info["status"] = "missing"
        info["message"] = "No Template-ID found in header, footer, or first page."
        return info
    entry = TEMPLATE_REGISTRY.get(found_id)
    if not entry:
        info["status"] = "unknown"
        info["message"] = f"Template-ID '{found_id}' is not in the registry."
        return info
    info["name"] = entry.get("name")
    info["version"] = entry.get("version")
    info["registry_status"] = entry.get("status")
    info["expected_sections"] = entry.get("expected_sections", [])
    info["expected_document_type"] = entry.get("document_type")
    if entry.get("status") == "deprecated":
        info["status"] = "deprecated"
        info["message"] = (f"Template '{found_id}' is deprecated; "
                           f"use '{entry.get('superseded_by')}' instead.")
    elif document_type and entry.get("document_type") \
            and document_type.lower() != entry.get("document_type", "").lower():
        info["status"] = "type_mismatch"
        info["message"] = (f"Template '{found_id}' is for "
                           f"{entry.get('document_type')} but job declared "
                           f"document_type={document_type}.")
    else:
        info["status"] = "ok"
        info["message"] = f"Template '{found_id}' OK ({entry.get('version')})."
    return info


def node_run_checks(state: AgentState) -> Dict[str, Any]:
    """Fan out enabled AI checks in parallel; collect Finding dicts."""
    if not settings.has_any_llm():
        return {
            "findings": [],
            "errors": [*state.get("errors", []), "No LLM credentials configured"],
            "progress": {"percent": 60, "label": "Skipped (no LLM)", "stage": "checking"},
        }

    clients = _make_clients()
    enabled = set(state.get("enabled_checks") or [])
    raw_text = state["raw_text"]
    template_text = state["template_text"]
    brand = state.get("brand") or settings.brand
    document_type = (state.get("document_type") or "").strip()
    pre_pass = state.get("pre_pass") or {}

    # Phase-2: inject structured context at the top of the text the LLM sees.
    if pre_pass:
        ctx_block = _ctx.to_prompt_block(pre_pass)
        raw_text = (
            "=== STRUCTURED CONTEXT (authoritative \u2014 do not contradict) ===\n"
            f"{ctx_block}\n"
            "=== END STRUCTURED CONTEXT ===\n\n"
            f"{raw_text}"
        )

    # Honor per-check `enabled_by_default` and `applies_to` from ai_prompts.json.
    prompts = getattr(_ai, "_AI_PROMPTS", {}) or {}
    skipped_disabled: List[str] = []
    skipped_doctype: List[str] = []

    def _doc_type_matches(cid: str) -> bool:
        if not document_type:
            return True
        applies = prompts.get(cid, {}).get("applies_to") or ["ANY"]
        return "ANY" in applies or document_type in applies

    tasks: List[Tuple[str, Any, tuple]] = []
    skipped_slow: List[str] = []
    for cid, fn, kind, needs_template, needs_brand in CHECK_REGISTRY:
        if enabled:
            if cid not in enabled:
                continue
        else:
            # No explicit selection → respect the JSON default + doc-type filter.
            if not prompts.get(cid, {}).get("enabled_by_default", True):
                skipped_disabled.append(cid)
                continue
            if not _doc_type_matches(cid):
                skipped_doctype.append(cid)
                continue
        if FAST_MODE and not enabled and cid in SLOW_CHECKS:
            # Fast mode skips known-slow checks unless the caller explicitly
            # asks for them via enabled_checks.
            skipped_slow.append(cid)
            continue
        client = clients.get(kind)
        if client is None:
            continue
        model = _resolve_model(kind)
        args: tuple
        if needs_template:
            args = (client, model, raw_text, template_text)
        elif needs_brand:
            args = (client, model, raw_text, brand)
        else:
            args = (client, model, raw_text)
        tasks.append((cid, fn, args))

    # Carry forward the structural findings produced by node_load_documents.
    findings: List[Dict[str, Any]] = list(state.get("findings", []) or [])
    errors: List[str] = list(state.get("errors", []))

    if not tasks:
        return {
            "findings": findings,
            "errors": errors,
            "progress": {"percent": 60, "label": "No checks selected", "stage": "checking"},
        }

    print(f"[agentic] running {len(tasks)} AI checks in parallel "
          f"(brand={brand}, raw_text={len(raw_text)} chars, "
          f"per_check_timeout={PER_CHECK_TIMEOUT_SECONDS}s, "
          f"fast_mode={FAST_MODE})")
    if skipped_disabled:
        print(f"[agentic] disabled-by-default (use enabled_checks to opt in): {skipped_disabled}")
    if skipped_doctype:
        print(f"[agentic] skipped by document_type={document_type!r}: {skipped_doctype}")
    if skipped_slow:
        print(f"[agentic] FAST_MODE: skipping slow checks {skipped_slow}")

    sid = state["session_id"]
    total = len(tasks)
    started_at = time.time()
    _set_live(sid, completed=0, total=total,
              in_flight=[c[0] for c in tasks],
              percent=10, label=f"Running 0/{total} checks", stage="checking")

    completed = 0
    timings: Dict[str, float] = {}
    # One worker per task → real parallelism, not 8-at-a-time.
    with ThreadPoolExecutor(max_workers=total) as pool:
        future_map: Dict[Any, Tuple[str, float]] = {}
        for cid, fn, args in tasks:
            fut = pool.submit(fn, *args)
            future_map[fut] = (cid, time.time())

        pending = set(future_map.keys())
        deadline = time.time() + PER_CHECK_TIMEOUT_SECONDS + 30
        while pending:
            done_now = []
            try:
                # Block at most 5 s so we can refresh in-flight progress.
                for fut in as_completed(list(pending), timeout=5):
                    done_now.append(fut)
                    if len(done_now) >= len(pending):
                        break
            except Exception:
                pass  # 5 s tick: just refresh progress and re-check deadline

            for fut in done_now:
                pending.discard(fut)
                cid, t0 = future_map[fut]
                dt = time.time() - t0
                timings[cid] = dt
                try:
                    result = fut.result(timeout=0) or []
                    added = 0
                    for f in result:
                        if isinstance(f, Finding):
                            findings.append(asdict(f))
                            added += 1
                    print(f"[agentic]   ✓ {cid:<28} {added:>3} findings  ({dt:5.1f}s)")
                except Exception as e:
                    print(f"[agentic]   ✗ {cid:<28} ERROR ({dt:5.1f}s): {e}")
                    errors.append(f"{cid}: {e}")
                completed += 1

            in_flight = [future_map[p][0] for p in pending]
            pct = 10 + int(55 * completed / total)
            label = (f"AI checks {completed}/{total}"
                     + (f" — waiting on {len(in_flight)}" if in_flight else ""))
            _set_live(sid, completed=completed, total=total,
                      in_flight=in_flight, percent=pct, label=label,
                      stage="checking")

            if pending and time.time() > deadline:
                stuck = [future_map[p][0] for p in pending]
                print(f"[agentic] hard deadline reached, abandoning "
                      f"{len(stuck)} stuck checks: {stuck}")
                for p in pending:
                    cid, t0 = future_map[p]
                    timings[cid] = time.time() - t0
                    errors.append(f"{cid}: timed out after {time.time()-t0:.0f}s")
                    p.cancel()
                pending.clear()
                break

    elapsed = time.time() - started_at

    # Per-check timing summary, slowest first - so the user can immediately
    # see which check is the bottleneck and disable it via enabled_checks.
    if timings:
        ranked = sorted(timings.items(), key=lambda kv: kv[1], reverse=True)
        print("[agentic] per-check timings (slowest first):")
        for cid, dt in ranked[:10]:
            print(f"[agentic]   {dt:6.1f}s  {cid}")

    print(f"[agentic] checks complete in {elapsed:.1f}s: "
          f"{len(findings)} findings, {len(errors)} errors")
    _set_live(sid, completed=total, in_flight=[], percent=65,
              label=f"Completed {total} checks ({elapsed:.0f}s)", stage="drafting")

    return {
        "findings": findings,
        "errors": errors,
        "progress": {
            "percent": 65,
            "label": f"Completed {total} checks ({elapsed:.0f}s); {len(findings)} findings",
            "stage": "checking",
        },
    }


_SEVERITY_RANK = {"Critical": 0, "Major": 1, "Moderate": 2, "Minor": 3}
_DOC_WIDE_HEADING = "Document-wide"


def _group_key_for_finding(raw_text: str, offsets: List[Tuple[int, str]],
                           f: Dict[str, Any]) -> str:
    """Decide which heading bucket a finding belongs to."""
    explicit = (f.get("section") or "").strip()
    if explicit:
        return explicit
    evidence = (f.get("evidence") or "").strip()
    if evidence:
        h = _nearest_heading(offsets, raw_text, evidence)
        if h:
            return h
    return _DOC_WIDE_HEADING


def _max_severity(items: List[Dict[str, Any]]) -> str:
    best = "Minor"
    best_rank = _SEVERITY_RANK[best]
    for it in items:
        s = it.get("severity", "Moderate")
        r = _SEVERITY_RANK.get(s, 4)
        if r < best_rank:
            best_rank = r
            best = s
    return best


def _display_name(check_id: str) -> str:
    """Return the user-friendly name configured in ai_prompts.json.

    Falls back to a humanised version of the raw id (e.g. 'AI17_Placeholders'
    -> 'Placeholders') and provides explicit labels for non-LLM internal
    check ids so the reviewer never sees the technical AIxx_ string.
    """
    prompts = getattr(_ai, "_AI_PROMPTS", {}) or {}
    entry = prompts.get(check_id) or {}
    name = entry.get("display_name")
    if name:
        return name
    if check_id == "STRUCT_EMPTY_CELL":
        return "Empty Table Cell"
    if check_id == "AGENT_INFO":
        return "Agent Note"
    base = check_id.split("_", 1)[-1] if "_" in check_id else check_id
    out = []
    for i, ch in enumerate(base):
        if i > 0 and ch.isupper() and base[i - 1].islower():
            out.append(" ")
        out.append(ch)
    return "".join(out)


def _build_summary(heading: str, items: List[Dict[str, Any]]) -> str:
    """Render the comment body that will be inserted under the heading.

    Uses the user-friendly display name (e.g. 'Placeholder Detection') rather
    than the raw check id (e.g. 'AI17_Placeholders') and labels the author as
    the DHF QA Agent so reviewers immediately know the comment is AI-drafted.
    """
    items = sorted(items, key=lambda x: _SEVERITY_RANK.get(x.get("severity", "Moderate"), 4))
    lines: List[str] = []
    lines.append(f"DHF QA Agent (AI) - {len(items)} issue(s) for: {heading}")
    for i, it in enumerate(items, 1):
        sev = it.get("severity", "Moderate")
        name = _display_name(it.get("check_id", ""))
        msg = (it.get("message") or "").strip().replace("\n", " ")
        if len(msg) > 280:
            msg = msg[:277].rstrip() + "..."
        lines.append(f"{i}. {name} (Severity: {sev}) - {msg}")
        ev = (it.get("evidence") or "").strip().replace("\n", " ")
        if ev:
            if len(ev) > 160:
                ev = ev[:157].rstrip() + "..."
            lines.append(f"   Evidence: \"{ev}\"")
    return "\n".join(lines)


def _finding_hash(f: Dict[str, Any], heading: str) -> str:
    """Stable identity for de-duplication: same check + same heading + same
    evidence text (case-insensitive) is considered a duplicate."""
    key = "|".join([
        (f.get("check_id") or "").strip(),
        (heading or "").strip().lower(),
        (f.get("evidence") or f.get("message") or "").strip().lower()[:200],
    ])
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def node_draft_comments(state: AgentState) -> Dict[str, Any]:
    """Group findings by heading and produce ONE reviewable card per group.

    Phase-1 noise controls applied here (in order):
      1. Severity threshold      (drop anything below `min_severity`)
      2. Duplicate-hash dedupe   (same check + heading + evidence collapsed)
      3. Per-section cap         (top-N by severity per heading)
    """
    raw_text = state.get("raw_text", "")
    headings = state.get("headings", [])
    offsets = _heading_offsets(raw_text, headings)
    findings = state.get("findings", []) or []

    min_sev = state.get("min_severity") or DEFAULT_MIN_SEVERITY
    if min_sev not in _SEVERITY_RANK:
        min_sev = DEFAULT_MIN_SEVERITY
    sev_threshold = _SEVERITY_RANK[min_sev]
    max_per_section = int(state.get("max_per_section") or DEFAULT_MAX_PER_SECTION)
    if max_per_section <= 0:
        max_per_section = DEFAULT_MAX_PER_SECTION

    raw_count = len(findings)

    # 1) Severity filter. Structural findings are always kept (they are facts).
    filtered: List[Dict[str, Any]] = []
    for f in findings:
        if f.get("check_id") == "STRUCT_EMPTY_CELL":
            filtered.append(f); continue
        sev = f.get("severity", "Moderate")
        if _SEVERITY_RANK.get(sev, 4) <= sev_threshold:
            filtered.append(f)
    after_sev = len(filtered)

    # Bucket findings by heading.
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for f in filtered:
        key = _group_key_for_finding(raw_text, offsets, f)
        buckets.setdefault(key, []).append(f)

    # 2) Dedupe inside each bucket.
    deduped_total = 0
    for heading, items in list(buckets.items()):
        seen: set = set()
        unique: List[Dict[str, Any]] = []
        for it in items:
            h = _finding_hash(it, heading)
            if h in seen:
                continue
            seen.add(h); unique.append(it)
        buckets[heading] = unique
        deduped_total += len(unique)

    # 3) Per-section cap (most-severe first).
    capped_total = 0
    for heading, items in list(buckets.items()):
        items.sort(key=lambda x: _SEVERITY_RANK.get(x.get("severity", "Moderate"), 4))
        if len(items) > max_per_section:
            items = items[:max_per_section]
        buckets[heading] = items
        capped_total += len(items)

    print(f"[agentic] noise filter: raw={raw_count} -> sev>={min_sev}={after_sev} "
          f"-> dedupe={deduped_total} -> cap@{max_per_section}={capped_total}")

    drafts: List[DraftComment] = []
    for heading, items in buckets.items():
        max_sev = _max_severity(items)
        summary = _build_summary(heading, items)
        # Compact item list for the UI's expandable detail view.
        compact_items = []
        for it in items:
            compact_items.append({
                "check_id": it.get("check_id", ""),
                "severity": it.get("severity", "Moderate"),
                "message": (it.get("message") or "").strip(),
                "evidence": (it.get("evidence") or "").strip(),
            })
        drafts.append({
            "id": uuid.uuid4().hex[:12],
            "check_id": f"GROUP({len(items)})",
            "severity": max_sev,
            "heading": None if heading == _DOC_WIDE_HEADING else heading,
            "evidence": "",  # the bucket isn't anchored to a single quote
            "message": summary,
            "decision": "pending",
            # extra fields the UI knows about; LangGraph state happily carries them
            "items": compact_items,            # type: ignore[typeddict-item]
            "issue_count": len(items),         # type: ignore[typeddict-item]
        })

    # Sort: most-severe groups first, then by heading text.
    drafts.sort(key=lambda d: (
        _SEVERITY_RANK.get(d.get("severity", "Moderate"), 4),
        (d.get("heading") or "~"),
    ))

    # Always give the reviewer at least one card so the UI is never blank.
    if not drafts:
        errors = state.get("errors", []) or []
        if errors:
            msg = ("AI checks completed with errors and produced no findings. "
                   "Review the errors below and re-run if needed.\n\n" + "\n".join(errors[:10]))
            sev = "Major"
        elif not settings.has_any_llm():
            msg = ("No LLM credentials are configured (.env). The agent ran but "
                   "could not call any AI check. Configure AZURE_OPENAI_* and re-run.")
            sev = "Major"
        else:
            msg = "No quality issues were detected by the AI checks for this document."
            sev = "Minor"
        drafts.append({
            "id": uuid.uuid4().hex[:12],
            "check_id": "AGENT_INFO",
            "severity": sev,
            "heading": None,
            "evidence": "",
            "message": msg,
            "decision": "rejected",   # informational; nothing to insert by default
        })

    print(f"[agentic] drafted {len(drafts)} review cards "
          f"(from {len(findings)} raw findings)")

    return {
        "draft_comments": drafts,
        "progress": {
            "percent": 75,
            "label": f"{len(drafts)} draft comments awaiting review",
            "stage": "awaiting_review",
        },
    }


def node_await_human_review(state: AgentState) -> Dict[str, Any]:
    """No-op marker node. The graph is configured to interrupt BEFORE this node
    so the API can collect human decisions before resuming."""
    return {
        "progress": {
            "percent": 80,
            "label": "Resuming with human decisions",
            "stage": "applying",
        },
    }


def _rebuild_report_from_decisions(state: AgentState) -> Report:
    """Build a Report whose ai_findings only contain approved (and possibly
    edited) draft groups. Rejected ones are dropped.

    Each approved DRAFT GROUP becomes a single Finding entry whose `message`
    is the (possibly edited) summary text. This is what the markdown report
    renders.
    """
    report = Report()
    drafts = state.get("draft_comments", [])
    for d in drafts:
        if d.get("decision") != "approved":
            continue
        message = d.get("edited_message") or d.get("message", "")
        finding = Finding(
            check_id=d.get("check_id", "AI"),
            severity=d.get("severity", "Moderate"),
            message=message,
            evidence="",
            section=d.get("heading"),
        )
        report.ai_findings[finding.check_id].append(finding)
    return report


def _build_summary_entries(state: AgentState) -> List[Dict[str, str]]:
    """List of {'heading','summary'} for the heading-anchored Word writer."""
    out: List[Dict[str, str]] = []
    for d in state.get("draft_comments", []) or []:
        if d.get("decision") != "approved":
            continue
        body = (d.get("edited_message") or d.get("message") or "").strip()
        if not body:
            continue
        out.append({
            "heading": (d.get("heading") or "").strip(),
            "summary": body,
        })
    return out


def node_apply_comments(state: AgentState) -> Dict[str, Any]:
    """Write ONE consolidated comment per approved heading-group into the DOCX
    and emit a markdown report listing the same summaries."""
    workspace = state.get("workspace_dir") or str(settings.workspace_dir / state["session_id"])
    os.makedirs(workspace, exist_ok=True)

    doc_filename = state.get("doc_filename") or os.path.basename(state["doc_path"])
    base = os.path.splitext(doc_filename)[0]
    review_doc_path = os.path.join(workspace, f"{base}_review.docx")
    report_md_path = os.path.join(workspace, "review_report.md")

    summaries = _build_summary_entries(state)
    errors = list(state.get("errors", []) or [])

    if summaries:
        try:
            from docx_summary_writer import add_summary_comments_to_word
            result = add_summary_comments_to_word(
                state["doc_path"], review_doc_path, summaries,
                author="DHF QA Agent",
            )
            print(f"[agentic] inserted {result['attached']}/{result['total']} "
                  f"summary comments; unmatched={len(result['unmatched'])}")
            if result["unmatched"]:
                for um in result["unmatched"][:5]:
                    errors.append(f"unmatched heading: {um['heading']}")
        except Exception as e:
            shutil.copy2(state["doc_path"], review_doc_path)
            errors.append(f"comment writer: {e}")
    else:
        # Nothing approved → still produce a clean copy so the user can download.
        shutil.copy2(state["doc_path"], review_doc_path)

    # Markdown summary mirrors what landed in the DOCX.
    try:
        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write(f"# DHF QA Review — {doc_filename}\n\n")
            f.write(f"- Brand: {state.get('brand', settings.brand)}\n")
            f.write(f"- Template: {state.get('template_filename', '')}\n")
            doc_type = state.get("document_type")
            if doc_type:
                f.write(f"- Document type: {doc_type}\n")
            tm = state.get("template_match") or {}
            if tm:
                f.write(f"- Template match: {tm.get('status','?')} "
                        f"(found_id={tm.get('found_id')!r}) \u2014 {tm.get('message','')}\n")
            pp = state.get("pre_pass") or {}
            if pp:
                f.write(
                    f"- Pre-pass: "
                    f"glossary={len(pp.get('glossary') or {})}, "
                    f"req_tags={len(pp.get('req_tags') or [])}, "
                    f"ver_tags={len(pp.get('ver_tags') or [])}, "
                    f"test_cases={len(pp.get('test_cases') or [])}, "
                    f"revision_entries={len(pp.get('revision_history') or [])}, "
                    f"authors={len(pp.get('authors') or [])}\n"
                )
            f.write(f"- Approved heading-comments: {len(summaries)}\n")
            f.write(f"- Total raw findings: {len(state.get('findings', []) or [])}\n")
            if errors:
                f.write(f"- Notes/Errors: {len(errors)}\n")
            f.write("\n---\n\n")
            for entry in summaries:
                f.write(f"## {entry['heading'] or '(document-wide)'}\n\n")
                f.write("```\n")
                f.write(entry["summary"])
                f.write("\n```\n\n")
            if errors:
                f.write("\n## Notes\n\n")
                for e in errors:
                    f.write(f"- {e}\n")
    except Exception as e:
        errors.append(f"reporter: {e}")

    return {
        "review_doc_path": review_doc_path,
        "report_md_path": report_md_path,
        "errors": errors,
        "progress": {"percent": 100, "label": "Done", "stage": "done"},
    }


def node_clear_live_progress(session_id: str) -> None:
    """Allow the API to drop the side-channel entry after the session ends."""
    _clear_live(session_id)
