"""
Shared LangGraph state for the document review pipeline.

Each session corresponds to one DOCX review. The state object travels through
every node and accumulates findings, draft comments, human decisions, and
output paths.
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict
from typing_extensions import NotRequired


# A "draft comment" is the unit of human review.
# It is what the AI proposes to attach to a heading / paragraph in the DOCX.
class DraftComment(TypedDict, total=False):
    id: str                       # stable id, used by frontend to vote
    check_id: str                 # e.g. "AI01_NA_Justification"
    severity: str                 # Critical | Major | Moderate | Minor
    heading: Optional[str]        # nearest heading the comment is anchored to
    evidence: str                 # quoted snippet from the doc
    message: str                  # AI-suggested comment body
    edited_message: NotRequired[str]            # human-edited body (if any)
    decision: Literal["pending", "approved", "rejected"]
    rationale: NotRequired[str]                 # optional reviewer note


class ReviewProgress(TypedDict, total=False):
    percent: int
    label: str
    stage: str   # one of: pending, loading, checking, drafting, awaiting_review, applying, done, error


class AgentState(TypedDict, total=False):
    # ----- inputs -----
    session_id: str
    doc_path: str
    template_path: str
    doc_filename: str
    template_filename: str
    brand: str
    enabled_checks: List[str]            # subset of supported check ids; empty == all
    workspace_dir: str

    # ----- Phase-2 context & customisation -----
    document_type: NotRequired[str]      # one of: DHF | DMR | RFS | Verification | Risk | Generic
    pre_pass: NotRequired[Dict[str, Any]]  # structured facts extracted by context_extractor
    template_match: NotRequired[Dict[str, Any]]  # {found_id, expected, status, ...}

    # ----- Phase-1 noise controls (optional, sensible defaults applied in nodes) -----
    min_severity: NotRequired[str]       # one of Critical|Major|Moderate|Minor; default Moderate
    max_per_section: NotRequired[int]    # cap on draft cards per heading; default 5

    # ----- intermediate -----
    raw_text: str
    template_text: str
    headings: List[str]
    findings: List[Dict[str, Any]]       # serialised Finding dicts
    draft_comments: List[DraftComment]

    # ----- HITL output -----
    decisions_complete: bool             # set by API when all comments reviewed

    # ----- finals -----
    review_doc_path: NotRequired[str]
    report_md_path: NotRequired[str]

    # ----- bookkeeping -----
    progress: ReviewProgress
    errors: List[str]
