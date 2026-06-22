"""
Data models for the Document Quality Checker application.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

@dataclass
class Finding:
    check_id: str
    severity: str
    message: str
    evidence: str = ""
    span: Optional[Tuple[int,int]] = None
    section: Optional[str] = None

@dataclass
class Para:
    text: str
    style: str = ""

@dataclass
class ExtractedDoc:
    paragraphs: List[Para] = field(default_factory=list)
    tables: List[List[List[str]]] = field(default_factory=list)  # list of tables; table is list of rows; row is list of cells (str)
    raw_text: str = ""  # joined paragraphs for regex scans
    headings: List[str] = field(default_factory=list)  # guessed headings by style or numeric pattern
    header_text: str = ""   # concatenated text of all section headers
    footer_text: str = ""   # concatenated text of all section footers
    # Per-cell empty findings produced at load time so the LLM doesn't have
    # to guess. Each entry: {table_index, row, column_index, column_name, nearest_heading}
    empty_cells: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class Report:
    ai_findings: Dict[str, List[Finding]] = field(default_factory=lambda: defaultdict(list))
    brand_findings: List[Finding] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
