"""
Agentic workflow package for the DHF GDP Checker.

Implements the document-quality review pipeline as a LangGraph state machine
with a human-in-the-loop checkpoint between AI comment drafting and
final DOCX annotation.
"""

from .config import settings
from .graph import build_graph, get_app

__all__ = ["settings", "build_graph", "get_app"]
