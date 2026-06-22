#!/usr/bin/env python3
"""
Document Loader Module
======================

This module provides document loading functionality for the Document Quality Checker.
It extracts paragraphs, tables, headings, and raw text from DOCX files.
"""

from typing import List, Dict, Any
from models import ExtractedDoc, Para

# Import docx dependencies
try:
    from docx import Document as DocxDocument
except ImportError:
    raise SystemExit("❌ python-docx is not installed. Please run: pip install python-docx")


def _safe_table_grid(table) -> List[List[str]]:
    """Extract a table's text grid, tolerant of malformed/irregular tables.

    python-docx raises ``IndexError`` from ``Row.cells`` when a table has an
    inconsistent grid (e.g. merged cells whose spans don't add up, which Word
    sometimes produces). We first try the normal per-row access and fall back
    to reading the underlying ``<w:tc>`` elements directly so a single broken
    table can't crash the whole load.
    """
    grid: List[List[str]] = []
    for row in table.rows:
        try:
            grid.append([cell.text.strip() for cell in row.cells])
        except (IndexError, ValueError):
            # Fall back to raw cell elements for this row.
            try:
                tcs = row._tr.tc_lst
            except Exception:
                tcs = []
            row_text: List[str] = []
            for tc in tcs:
                texts = tc.xpath(".//w:t")
                row_text.append("".join(t.text or "" for t in texts).strip())
            grid.append(row_text)
    return grid


def _detect_empty_cells(grid: List[List[str]], table_index: int,
                        nearest_heading: str) -> List[Dict[str, Any]]:
    """Per-cell emptiness detector.

    Treats the first row as the header row; flags every blank data cell
    *except* when the entire row is blank (likely a spacer / merged row).
    Anchors each finding to the table index, row number, and column name.
    """
    out: List[Dict[str, Any]] = []
    if not grid or len(grid) < 2:
        return out
    headers = [(c or "").strip() for c in grid[0]]
    for row_idx, row in enumerate(grid[1:], start=1):
        if not any((c or "").strip() for c in row):
            continue  # whole row blank → ignore (spacer / merged)
        for col_idx, cell in enumerate(row):
            if (cell or "").strip():
                continue
            col_name = headers[col_idx] if col_idx < len(headers) and headers[col_idx] \
                       else f"col {col_idx + 1}"
            out.append({
                "table_index": table_index,
                "row": row_idx,
                "column_index": col_idx,
                "column_name": col_name,
                "nearest_heading": nearest_heading,
            })
    return out


def load_docx(path: str) -> ExtractedDoc:
    """
    Load a DOCX file and extract its contents into an ExtractedDoc object.

    Now also captures:
      * header_text / footer_text (concatenated across all sections)
      * empty_cells: structural facts about blank cells in tables, used by the
        agent to ground LLM checks instead of letting them guess.
    """
    d = ExtractedDoc()
    doc = DocxDocument(path)

    # ---- Paragraphs ----
    for p in doc.paragraphs:
        style = getattr(p.style, "name", "") or ""
        text = p.text or ""
        d.paragraphs.append(Para(text=text, style=style))

    # ---- Headings (used to anchor empty-cell findings) ----
    for p in d.paragraphs:
        if "Heading" in (p.style or "") and p.text.strip():
            d.headings.append(p.text.strip())

    # ---- Header / Footer (across all sections) ----
    header_parts: List[str] = []
    footer_parts: List[str] = []
    for section in doc.sections:
        try:
            if section.header is not None:
                for p in section.header.paragraphs:
                    if p.text and p.text.strip():
                        header_parts.append(p.text.strip())
            if section.footer is not None:
                for p in section.footer.paragraphs:
                    if p.text and p.text.strip():
                        footer_parts.append(p.text.strip())
        except Exception:
            # python-docx can raise on unusual headers; skip rather than crash
            continue
    d.header_text = "\n".join(header_parts)
    d.footer_text = "\n".join(footer_parts)

    # ---- Tables + per-cell emptiness ----
    last_heading = ""
    heading_set = set(d.headings)
    # Walk paragraphs in order to know which heading precedes each table.
    # python-docx exposes tables and paragraphs separately, so we approximate
    # by mapping every table to the most recently seen heading in body order.
    body_iter_headings: List[str] = []
    for p in doc.paragraphs:
        if "Heading" in (getattr(p.style, "name", "") or "") and p.text.strip():
            body_iter_headings.append(p.text.strip())
    # If we cannot interleave precisely, fall back to "last heading seen".
    for t_idx, t in enumerate(doc.tables):
        grid = _safe_table_grid(t)
        d.tables.append(grid)
        # Best-effort heading anchor: use the last body heading we saw, or the
        # nearest heading by index ratio if we have any.
        if body_iter_headings:
            ratio = (t_idx + 1) / max(len(doc.tables), 1)
            anchor_idx = min(int(ratio * len(body_iter_headings)),
                             len(body_iter_headings) - 1)
            last_heading = body_iter_headings[anchor_idx]
        d.empty_cells.extend(_detect_empty_cells(grid, t_idx, last_heading))

    # ---- Raw text (body + header + footer so downstream prompts see all) ----
    raw_parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table:
            raw_parts.append(" | ".join(cell for cell in row if cell))
    if d.header_text:
        raw_parts.insert(0, f"[HEADER]\n{d.header_text}\n[/HEADER]")
    if d.footer_text:
        raw_parts.append(f"[FOOTER]\n{d.footer_text}\n[/FOOTER]")
    d.raw_text = "\n".join(raw_parts)

    # de-dup heading list while preserving order
    seen = set(); deduped = []
    for h in d.headings:
        if h not in seen:
            seen.add(h); deduped.append(h)
    d.headings = deduped

    return d



