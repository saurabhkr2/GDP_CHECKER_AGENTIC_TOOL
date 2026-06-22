"""
LangGraph wiring for the document-quality review pipeline.

  load_documents -> run_checks -> draft_comments -> [INTERRUPT] -> apply_comments -> END

The interrupt before `await_human_review` is what enables Human-in-the-Loop:
the API runs the graph until that point, surfaces draft comments to the user,
collects approve/reject/edit decisions, then resumes.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .nodes import (
    node_apply_comments,
    node_await_human_review,
    node_draft_comments,
    node_load_documents,
    node_run_checks,
)
from .state import AgentState


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("load_documents", node_load_documents)
    g.add_node("run_checks", node_run_checks)
    g.add_node("draft_comments", node_draft_comments)
    g.add_node("await_human_review", node_await_human_review)
    g.add_node("apply_comments", node_apply_comments)

    g.add_edge(START, "load_documents")
    g.add_edge("load_documents", "run_checks")
    g.add_edge("run_checks", "draft_comments")
    g.add_edge("draft_comments", "await_human_review")
    g.add_edge("await_human_review", "apply_comments")
    g.add_edge("apply_comments", END)
    return g


@lru_cache(maxsize=1)
def get_app():
    """Compile the graph with an in-memory checkpointer.

    We interrupt BEFORE `await_human_review` so that:
      * the graph stops with `draft_comments` already populated in state,
      * the API can read those drafts, mutate them with reviewer decisions,
      * `app.invoke(None, config)` resumes the run from that exact step.
    """
    return build_graph().compile(
        checkpointer=MemorySaver(),
        interrupt_before=["await_human_review"],
    )
