"""
Heading-anchored Word comment writer.

Unlike `docx_comment_writer.add_comment_to_word`, which inserts ONE Word
comment per AI finding (often producing 150+ scattered bubbles), this writer
inserts ONE consolidated comment per heading. The comment is anchored to the
paragraph whose text matches the heading, so the reviewer sees a single
threaded note attached directly to the section it concerns.

Each entry it accepts is:

    {
        "heading": str,          # exact heading text (matched to a docx paragraph)
        "summary": str,          # full multi-line comment body to insert
    }

Matching strategy
-----------------
1. Normalise the candidate heading and every paragraph text (collapsed whitespace).
2. Prefer paragraphs whose `pStyle` is a Heading style.
3. Fall back to a case-insensitive equality, then to a "starts with" match.
4. If the heading cannot be located, the comment is attached to the FIRST
   non-empty body paragraph and the heading text is prepended to the summary.
"""
from __future__ import annotations

import os
import re
import shutil
import time
import zipfile
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

from lxml import etree


_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_CT_NS = "{http://schemas.openxmlformats.org/package/2006/content-types}"
_RELS_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_XML_NS = "{http://www.w3.org/XML/1998/namespace}"


def _norm(s: str) -> str:
    return " ".join((s or "").split()).strip().lower()


def _para_text(p) -> str:
    return " ".join("".join(p.itertext()).split())


def _is_heading_para(p) -> bool:
    pStyle = p.find(f"{_W_NS}pPr/{_W_NS}pStyle")
    if pStyle is None:
        return False
    val = pStyle.get(f"{_W_NS}val", "")
    return "Heading" in val or val.lower().startswith("heading")


def _find_heading_paragraph(all_paragraphs, heading: str):
    """Return the best paragraph element to anchor a comment for `heading`."""
    target = _norm(heading)
    if not target:
        return None

    # Strip leading numbering like "5.3.6 " before matching.
    target_no_num = re.sub(r"^[\d\.]+\s*", "", target)

    # Pass 1: heading-style paragraph with exact text.
    for p in all_paragraphs:
        if not _is_heading_para(p):
            continue
        t = _norm(_para_text(p))
        if t == target or _norm(re.sub(r"^[\d\.]+\s*", "", t)) == target_no_num:
            return p

    # Pass 2: any paragraph with exact (normalised) match.
    for p in all_paragraphs:
        t = _norm(_para_text(p))
        if t == target:
            return p

    # Pass 3: starts-with match on heading-style paragraphs.
    for p in all_paragraphs:
        if not _is_heading_para(p):
            continue
        t = _norm(_para_text(p))
        if t.startswith(target_no_num) or target_no_num.startswith(t):
            return p

    # Pass 4: starts-with on any paragraph (last resort, but only if the
    # heading text is reasonably specific).
    if len(target_no_num) >= 6:
        for p in all_paragraphs:
            t = _norm(_para_text(p))
            if t.startswith(target_no_num):
                return p

    return None


def _make_comment_xml_element(comments_root, comment_id: int, author: str, body: str) -> None:
    comment = etree.SubElement(comments_root, f"{_W_NS}comment")
    comment.set(f"{_W_NS}id", str(comment_id))
    comment.set(f"{_W_NS}author", author)
    comment.set(f"{_W_NS}date", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    comment.set(f"{_W_NS}initials", "QA")

    # Each line of the summary becomes its own paragraph so Word renders
    # bullets / multi-line content sensibly.
    safe = "".join(c for c in body if ord(c) >= 32 or c in "\n\r\t")
    for line in safe.split("\n"):
        p = etree.SubElement(comment, f"{_W_NS}p")
        pPr = etree.SubElement(p, f"{_W_NS}pPr")
        pStyle = etree.SubElement(pPr, f"{_W_NS}pStyle")
        pStyle.set(f"{_W_NS}val", "CommentText")
        r = etree.SubElement(p, f"{_W_NS}r")
        etree.SubElement(r, f"{_W_NS}rPr")
        t = etree.SubElement(r, f"{_W_NS}t")
        t.set(f"{_XML_NS}space", "preserve")
        t.text = line


def _attach_comment_to_paragraph(para, comment_id: int) -> None:
    start = etree.Element(f"{_W_NS}commentRangeStart")
    start.set(f"{_W_NS}id", str(comment_id))
    end = etree.Element(f"{_W_NS}commentRangeEnd")
    end.set(f"{_W_NS}id", str(comment_id))
    para.insert(0, start)
    para.append(end)
    run = etree.SubElement(para, f"{_W_NS}r")
    ref = etree.SubElement(run, f"{_W_NS}commentReference")
    ref.set(f"{_W_NS}id", str(comment_id))


def _ensure_content_type(content_types_path: str) -> None:
    if not os.path.exists(content_types_path):
        return
    tree = etree.parse(content_types_path)
    root = tree.getroot()
    for o in root.findall(f"{_CT_NS}Override"):
        if o.get("PartName") == "/word/comments.xml":
            return
    o = etree.SubElement(root, f"{_CT_NS}Override")
    o.set("PartName", "/word/comments.xml")
    o.set("ContentType",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml")
    with open(content_types_path, "wb") as f:
        f.write(etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True))


def _ensure_rel(rels_path: str) -> None:
    if not os.path.exists(rels_path):
        return
    tree = etree.parse(rels_path)
    root = tree.getroot()
    for r in root.findall(f"{_RELS_NS}Relationship"):
        if r.get("Type") == \
           "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments":
            return
    max_id = 0
    for r in root.findall(f"{_RELS_NS}Relationship"):
        rid = r.get("Id", "")
        if rid.startswith("rId"):
            try:
                max_id = max(max_id, int(rid[3:]))
            except ValueError:
                pass
    new = etree.SubElement(root, f"{_RELS_NS}Relationship")
    new.set("Id", f"rId{max_id + 1}")
    new.set("Type",
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments")
    new.set("Target", "comments.xml")
    with open(rels_path, "wb") as f:
        f.write(etree.tostring(tree, xml_declaration=True, encoding="UTF-8"))


def _safe_rmtree(path: str) -> None:
    for _ in range(3):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            time.sleep(0.4)
    shutil.rmtree(path, ignore_errors=True)


def add_summary_comments_to_word(
    doc_path: str,
    output_path: str,
    summaries: Iterable[Dict[str, str]],
    author: str = "DHF QA Agent",
) -> Dict[str, object]:
    """Insert one consolidated comment per heading into a DOCX.

    Returns a small report describing what was attached vs. what could not be
    matched (for surfacing in the UI / markdown report).
    """
    summaries = [s for s in summaries if (s.get("summary") or "").strip()]
    shutil.copy2(doc_path, output_path)

    if not summaries:
        return {"attached": 0, "unmatched": [], "total": 0}

    temp_dir = output_path + ".extract"
    if os.path.exists(temp_dir):
        _safe_rmtree(temp_dir)
    with zipfile.ZipFile(output_path, "r") as z:
        z.extractall(temp_dir)

    doc_xml_path = os.path.join(temp_dir, "word", "document.xml")
    with open(doc_xml_path, "rb") as f:
        tree = etree.parse(f)
    root = tree.getroot()

    comments_root = etree.Element(
        f"{_W_NS}comments",
        nsmap={"w": _W_NS[1:-1]},
    )

    all_paragraphs = root.findall(f".//{_W_NS}p")

    attached = 0
    unmatched: List[Dict[str, str]] = []
    fallback_para = None
    for p in all_paragraphs:
        if _para_text(p):
            fallback_para = p
            break

    next_id = 0
    for entry in summaries:
        heading = (entry.get("heading") or "").strip()
        body = (entry.get("summary") or "").strip()
        target_para = _find_heading_paragraph(all_paragraphs, heading) if heading else None

        if target_para is None:
            target_para = fallback_para
            if heading:
                body = f"[Section: {heading}]\n{body}"
            unmatched.append({"heading": heading or "(document-wide)", "summary": body})
        else:
            attached += 1

        if target_para is None:
            # Nothing in the document — abandon this entry.
            continue

        _make_comment_xml_element(comments_root, next_id, author, body)
        _attach_comment_to_paragraph(target_para, next_id)
        next_id += 1

    # Persist edits.
    with open(doc_xml_path, "wb") as f:
        f.write(etree.tostring(tree, xml_declaration=True, encoding="UTF-8"))
    with open(os.path.join(temp_dir, "word", "comments.xml"), "wb") as f:
        f.write(etree.tostring(etree.ElementTree(comments_root),
                               xml_declaration=True, encoding="UTF-8"))
    _ensure_content_type(os.path.join(temp_dir, "[Content_Types].xml"))
    _ensure_rel(os.path.join(temp_dir, "word", "_rels", "document.xml.rels"))

    # Re-zip.
    if os.path.exists(output_path):
        os.remove(output_path)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for folder, _, files in os.walk(temp_dir):
            for file in files:
                full = os.path.join(folder, file)
                zout.write(full, os.path.relpath(full, temp_dir))
    _safe_rmtree(temp_dir)

    return {
        "attached": attached,
        "unmatched": unmatched,
        "total": len(summaries),
    }
