"""
Event collector for GDP Checker monitoring.

Captures usage events from the GDP Checker agentic pipeline
and stores them as raw per-session records.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from .schema import GDPCheckerUsageRecord, get_period_info
from .storage import get_storage, MonitoringStorage


# Productivity factor: Hours saved per session (like other tools in IGTS AI Savings)
# Can be overridden via environment variable
DEFAULT_PRODUCTIVITY_FACTOR = float(os.getenv("GDP_CHECKER_PRODUCTIVITY_FACTOR", "2.0"))


def calculate_hours_saved(productivity_factor: float = DEFAULT_PRODUCTIVITY_FACTOR) -> float:
    """
    Calculate hours saved per session.
    
    Matches Excel formula: Hours Saved = 1 session × Productivity Factor
    
    For GDP Checker, factor = 2.0 (as defined in IGTS AI Savings spreadsheet)
    This means each completed session saves 2 hours.
    """
    return productivity_factor


class UsageCollector:
    """
    Collects and records GDP Checker usage events.
    
    Usage:
        collector = UsageCollector()
        collector.start_session(session_id, user_email, doc_name)
        collector.record_findings(session_id, findings_list)
        collector.record_comments_generated(session_id, count)
        collector.record_review(session_id, approved, rejected, edited)
        collector.complete_session(session_id)
    """
    
    def __init__(self, storage: Optional[MonitoringStorage] = None):
        self.storage = storage or get_storage()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def start_session(
        self,
        session_id: str,
        user_email: str,
        document_name: str,
        template_name: Optional[str] = None,
    ) -> GDPCheckerUsageRecord:
        now = datetime.now()
        period = get_period_info(now)
        
        record = GDPCheckerUsageRecord(
            timestamp=now.isoformat(),
            period_start=period["period_start"],
            period_end=period["period_end"],
            period_month=period["period_month"],
            user_email=user_email,
            session_id=session_id,
            document_name=document_name,
            template_name=template_name,
            status="running",
        )
        
        self._active_sessions[session_id] = {
            "record": record,
            "start_time": now,
            "review_start_time": None,
        }
        
        self.storage.save_record(record)
        return record
    
    def record_findings(self, session_id: str, findings: List[Dict[str, Any]], checks_run: int = 21) -> None:
        if session_id not in self._active_sessions:
            return
        
        record = self._active_sessions[session_id]["record"]
        
        severity_counts = {"Critical": 0, "Major": 0, "Moderate": 0, "Minor": 0}
        for finding in findings:
            severity = finding.get("severity", "Moderate")
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        record.checks_run = checks_run
        record.findings_total = len(findings)
        record.findings_critical = severity_counts["Critical"]
        record.findings_major = severity_counts["Major"]
        record.findings_moderate = severity_counts["Moderate"]
        record.findings_minor = severity_counts["Minor"]
        
        self.storage.save_record(record)
    
    def record_comments_generated(self, session_id: str, comments_count: int) -> None:
        if session_id not in self._active_sessions:
            return
        
        record = self._active_sessions[session_id]["record"]
        record.comments_generated = comments_count
        self._active_sessions[session_id]["review_start_time"] = datetime.now()
        self.storage.save_record(record)
    
    def record_review(self, session_id: str, approved: int, rejected: int, edited: int) -> None:
        if session_id not in self._active_sessions:
            return
        
        session = self._active_sessions[session_id]
        record = session["record"]
        
        record.comments_approved = approved
        record.comments_rejected = rejected
        record.comments_edited = edited
        
        if session["review_start_time"]:
            review_duration = datetime.now() - session["review_start_time"]
            record.review_time_seconds = review_duration.total_seconds()
        
        self.storage.save_record(record)
    
    def complete_session(
        self,
        session_id: str,
        status: str = "completed",
        error_message: Optional[str] = None,
    ) -> Optional[GDPCheckerUsageRecord]:
        if session_id not in self._active_sessions:
            return self.storage.get_record(session_id)
        
        session = self._active_sessions[session_id]
        record = session["record"]
        
        if session["start_time"]:
            total_duration = datetime.now() - session["start_time"]
            record.processing_time_seconds = total_duration.total_seconds()
        
        record.status = status
        record.error_message = error_message
        
        if status == "completed":
            # Simple formula matching Excel: Hours = 1 session × Factor
            record.productivity_factor = DEFAULT_PRODUCTIVITY_FACTOR
            record.productivity_hours_saved = calculate_hours_saved(record.productivity_factor)
        
        self.storage.save_record(record)
        del self._active_sessions[session_id]
        
        return record
    
    def get_active_record(self, session_id: str) -> Optional[GDPCheckerUsageRecord]:
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]["record"]
        return self.storage.get_record(session_id)


_collector_instance: Optional[UsageCollector] = None


def get_collector() -> UsageCollector:
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = UsageCollector()
    return _collector_instance


def reset_collector() -> None:
    global _collector_instance
    _collector_instance = None
