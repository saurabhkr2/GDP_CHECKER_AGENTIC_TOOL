"""
Phase-2 pre-pass context extractor.

Walks the parsed DOCX once and pulls out structured facts that the LLM
checks otherwise have to guess at:

  * glossary       - {acronym: definition}
  * req_tags       - list of REQ-/SR-/SYS- identifiers found in the body
  * ver_tags       - list of VER-/TC-/TST- identifiers found in the body
  * test_cases     - list of dicts (one per test row) with empty-field flags
  * revision_history - list of dicts (version, date, author, description)
  * authors        - list of strings extracted from header / cover page
  * template_id    - string found in the header or footer

This dict is injected as JSON into every LLM check prompt as
"STRUCTURED CONTEXT (authoritative — do not contradict these facts)".
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ---- Acronym / tag regexes -------------------------------------------------
_ACRONYM_RE = re.compile(r"\b([A-Z]{2,6})\b")
_REQ_TAG_RE = re.compile(r"\b(?:REQ|SR|SYS|FR|NFR)[-_][A-Z0-9]+[-_]?\d+\b", re.IGNORECASE)
_VER_TAG_RE = re.compile(r"\b(?:VER|TC|TST|TEST)[-_][A-Z0-9]+[-_]?\d+\b", re.IGNORECASE)
_TEMPLATE_ID_RE = re.compile(
    r"\b(?:Template[-_ ]?ID|TPL[-_ ]?ID|Template)\s*[:#-]?\s*([A-Z][A-Z0-9\-_.]{3,40})",
    re.IGNORECASE,
)
_AUTHOR_RE = re.compile(r"\bAuthor[s]?\s*[:\-]\s*([^\n;,]+)", re.IGNORECASE)
_DEFINITION_RE = re.compile(
    r"^\s*([A-Z][A-Z0-9]{1,8})\s*[:=\-\u2013]\s*(.{3,200})$"
)


# ---- Section finders -------------------------------------------------------
def _index_headings(paragraphs) -> List[tuple]:
    """Return list of (index, style, text) for paragraphs that look like headings."""
    out = []
    for i, p in enumerate(paragraphs):
        style = (p.style or "").lower()
        if "heading" in style:
            out.append((i, style, p.text.strip()))
    return out


def _slice_after_heading(paragraphs, headings, name_match) -> List[str]:
    """Return paragraph texts between a heading whose text matches `name_match`
    (regex) and the next heading."""
    pat = re.compile(name_match, re.IGNORECASE)
    for n, (idx, _style, text) in enumerate(headings):
        if pat.search(text):
            start = idx + 1
            end = headings[n + 1][0] if n + 1 < len(headings) else len(paragraphs)
            return [paragraphs[k].text for k in range(start, end)]
    return []


# ---- Public API ------------------------------------------------------------
def extract_context(doc) -> Dict[str, Any]:
    """Build the structured-context dict.

    `doc` is the ExtractedDoc produced by `doc_loader.load_docx`.
    """
    paragraphs = doc.paragraphs
    headings = _index_headings(paragraphs)
    header = doc.header_text or ""
    footer = doc.footer_text or ""
    body = doc.raw_text or ""

    return {
        "template_id":      _extract_template_id(header, footer, body),
        "authors":          _extract_authors(header, paragraphs[:40]),
        "glossary":         _extract_glossary(paragraphs, headings, doc.tables),
        "req_tags":         sorted(set(_REQ_TAG_RE.findall(body))),
        "ver_tags":         sorted(set(_VER_TAG_RE.findall(body))),
        "revision_history": _extract_revision_history(paragraphs, headings, doc.tables),
        "test_cases":       _extract_test_cases(doc.tables),
    }


# ---- Individual extractors -------------------------------------------------
def _extract_template_id(header: str, footer: str, body: str) -> Optional[str]:
    for source in (header, footer, body[:2000]):
        if not source:
            continue
        m = _TEMPLATE_ID_RE.search(source)
        if m:
            return m.group(1).strip()
    return None


def _extract_authors(header: str, first_paragraphs) -> List[str]:
    candidates: List[str] = []
    if header:
        candidates.extend(m.strip() for m in _AUTHOR_RE.findall(header))
    for p in first_paragraphs:
        for m in _AUTHOR_RE.findall(p.text or ""):
            candidates.append(m.strip())
    # de-dup while preserving order
    seen, out = set(), []
    for c in candidates:
        if c and c.lower() not in seen:
            seen.add(c.lower()); out.append(c)
    return out


def _extract_glossary(paragraphs, headings, tables) -> Dict[str, str]:
    """Find the Abbreviations / Glossary / Terminology section, then parse it.
    Accept either `<ACR> : <def>` paragraphs or 2-column tables."""
    glossary: Dict[str, str] = {}
    section_pat = r"(abbreviation|glossary|terminolog|definition)"
    lines = _slice_after_heading(paragraphs, headings, section_pat)
    for line in lines:
        m = _DEFINITION_RE.match(line or "")
        if m:
            acr, definition = m.group(1).strip(), m.group(2).strip()
            glossary.setdefault(acr, definition)
    # Also walk tables: 2-col rows where first cell is an ALL-CAPS acronym.
    for t in tables:
        if not t or len(t[0]) < 2:
            continue
        for row in t:
            if len(row) < 2:
                continue
            key = (row[0] or "").strip()
            val = (row[1] or "").strip()
            if 2 <= len(key) <= 8 and key.isupper() and val:
                glossary.setdefault(key, val)
    return glossary


def _extract_revision_history(paragraphs, headings, tables) -> List[Dict[str, str]]:
    """Find Revision History section and prefer its table representation."""
    section_pat = r"revision\s*history|change\s*history|document\s*history"
    # We don't know which table belongs to this section reliably, so we accept
    # any table whose header row contains 'version' or 'revision' or 'date'.
    out: List[Dict[str, str]] = []
    for t in tables:
        if not t or len(t) < 2:
            continue
        header_row = [(c or "").strip().lower() for c in t[0]]
        if not any(h in (" ".join(header_row)) for h in ("version", "revision", "date")):
            continue
        for row in t[1:]:
            cells = [(c or "").strip() for c in row]
            if not any(cells):
                continue
            entry = {f"col{i}": v for i, v in enumerate(cells)}
            # Best-effort labelled fields
            for label, value in zip(header_row, cells):
                if label:
                    entry[label] = value
            out.append(entry)
        break  # first matching table is enough
    if out:
        return out
    # Fall back to paragraph lines under the heading.
    lines = _slice_after_heading(paragraphs, headings, section_pat)
    for line in lines:
        if line and line.strip():
            out.append({"raw": line.strip()})
    return out


def _extract_test_cases(tables) -> List[Dict[str, Any]]:
    """A 'test-case table' is one whose header contains test/verdict/result words."""
    out: List[Dict[str, Any]] = []
    keywords = ("test", "verdict", "result", "expected", "actual", "tc")
    for t_idx, t in enumerate(tables):
        if not t or len(t) < 2:
            continue
        header_row = [(c or "").strip() for c in t[0]]
        header_l = " ".join(h.lower() for h in header_row)
        if not any(k in header_l for k in keywords):
            continue
        for r_idx, row in enumerate(t[1:], start=1):
            cells = [(c or "").strip() for c in row]
            if not any(cells):
                continue
            tc = {f"col_{i}": v for i, v in enumerate(cells)}
            empty_cols: List[str] = []
            for i, v in enumerate(cells):
                if not v:
                    col_name = header_row[i] if i < len(header_row) else f"col_{i}"
                    empty_cols.append(col_name)
            tc["__table"] = t_idx
            tc["__row"] = r_idx
            tc["__empty_columns"] = empty_cols
            for label, value in zip(header_row, cells):
                if label:
                    tc[label] = value
            out.append(tc)
    return out


def to_prompt_block(pre_pass: Dict[str, Any], max_chars: int = 3500) -> str:
    """Compact JSON string suitable for injection at the top of an LLM prompt."""
    # Trim large lists for token economy.
    compact = {
        "template_id":      pre_pass.get("template_id"),
        "authors":          pre_pass.get("authors", []),
        "glossary":         dict(list((pre_pass.get("glossary") or {}).items())[:80]),
        "req_tags":         (pre_pass.get("req_tags") or [])[:80],
        "ver_tags":         (pre_pass.get("ver_tags") or [])[:80],
        "revision_history": (pre_pass.get("revision_history") or [])[:20],
        "test_cases":       [
            {k: v for k, v in tc.items() if not k.startswith("col_")}
            for tc in (pre_pass.get("test_cases") or [])[:40]
        ],
    }
    s = json.dumps(compact, ensure_ascii=False, indent=2)
    if len(s) > max_chars:
        s = s[:max_chars] + "\n... [truncated] ..."
    return s
