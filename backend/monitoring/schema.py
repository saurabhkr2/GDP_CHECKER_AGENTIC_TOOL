"""
Data schema for GDP Checker raw monitoring.

This produces raw per-session records similar to:
- ChatGPT_May.csv (per-user messages)
- Github_May.csv (per-user code metrics)

The raw data can later be processed/aggregated into the 
IGTS AI Savings format with cluster/org hierarchy info.
"""
from __future__ import annotations

import os
import calendar
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


# =============================================================================
# RAW MONITORING SCHEMA - Per Session Record
# =============================================================================

@dataclass
class GDPCheckerUsageRecord:
    """
    Raw per-session usage record for GDP Checker.
    
    This is the RAW format exported to CSV/SQLite (like ChatGPT_May.csv, Github_May.csv).
    Later, a separate script processes this into IGTS AI Savings aggregated format.
    
    Columns follow the pattern of other tool raw files:
    - Time period info
    - User identifier (email)
    - Tool-specific usage metrics
    """
    # === Time Period (like ChatGPT: cadence, period_start, period_end) ===
    timestamp: str                    # ISO format datetime of session
    period_start: str                 # First day of month (YYYY-MM-DD)
    period_end: str                   # Last day of month (YYYY-MM-DD)
    period_month: str                 # Month name: "January", "June", etc.
    
    # === User Identifier (like ChatGPT: email, Github: Microsoft_ManagerEmail) ===
    user_email: str                   # Employee email using the tool
    
    # === Session Info ===
    session_id: str                   # Unique session ID
    document_name: str                # Document being reviewed
    template_name: Optional[str] = None  # Template used (if any)
    
    # === GDP Checker Specific Metrics ===
    # Check execution
    checks_run: int = 21              # Number of checks executed (default 21)
    
    # Findings by severity
    findings_total: int = 0           # Total findings detected
    findings_critical: int = 0        # Critical severity
    findings_major: int = 0           # Major severity  
    findings_moderate: int = 0        # Moderate severity
    findings_minor: int = 0           # Minor severity
    
    # AI Comments (HITL metrics)
    comments_generated: int = 0       # AI-drafted comments
    comments_approved: int = 0        # Human approved
    comments_rejected: int = 0        # Human rejected
    comments_edited: int = 0          # Human edited before approval
    
    # Timing
    processing_time_seconds: float = 0.0   # Total processing time
    review_time_seconds: float = 0.0       # Human review time
    
    # Status
    status: str = "completed"         # completed | error
    error_message: Optional[str] = None
    
    # === Productivity Metric (matches Excel formula: Hours = 1 × Factor) ===
    productivity_factor: float = 2.0      # Human-defined factor (like other tools)
    productivity_hours_saved: float = 0.0  # Calculated: 1 session × factor
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/DB export."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GDPCheckerUsageRecord":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =============================================================================
# DATABASE SCHEMA - SQLite for local storage
# =============================================================================

USAGE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS gdp_checker_usage (
    -- Time Period
    timestamp TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    period_month TEXT NOT NULL,
    
    -- User
    user_email TEXT NOT NULL,
    
    -- Session
    session_id TEXT PRIMARY KEY,
    document_name TEXT,
    template_name TEXT,
    
    -- Checks & Findings
    checks_run INTEGER DEFAULT 21,
    findings_total INTEGER DEFAULT 0,
    findings_critical INTEGER DEFAULT 0,
    findings_major INTEGER DEFAULT 0,
    findings_moderate INTEGER DEFAULT 0,
    findings_minor INTEGER DEFAULT 0,
    
    -- Comments (HITL)
    comments_generated INTEGER DEFAULT 0,
    comments_approved INTEGER DEFAULT 0,
    comments_rejected INTEGER DEFAULT 0,
    comments_edited INTEGER DEFAULT 0,
    
    -- Timing
    processing_time_seconds REAL DEFAULT 0,
    review_time_seconds REAL DEFAULT 0,
    
    -- Status
    status TEXT DEFAULT 'completed',
    error_message TEXT,
    
    -- Productivity (matches Excel: Hours = 1 session × Factor)
    productivity_factor REAL DEFAULT 2.0,
    productivity_hours_saved REAL DEFAULT 0,
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usage_email ON gdp_checker_usage(user_email);
CREATE INDEX IF NOT EXISTS idx_usage_period ON gdp_checker_usage(period_month);
CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON gdp_checker_usage(timestamp);
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_period_info(dt: datetime) -> Dict[str, str]:
    """
    Get period info from datetime.
    Returns period_start, period_end, period_month.
    """
    year = dt.year
    month = dt.month
    
    # First and last day of month
    _, last_day = calendar.monthrange(year, month)
    period_start = f"{year}-{month:02d}-01"
    period_end = f"{year}-{month:02d}-{last_day:02d}"
    period_month = dt.strftime("%B")  # "January", "June", etc.
    
    return {
        "period_start": period_start,
        "period_end": period_end,
        "period_month": period_month,
    }


def get_default_db_path() -> str:
    """
    Get default database path.
    Uses environment variable or falls back to monitoring/data directory.
    Portable for VM deployment.
    """
    env_path = os.getenv("GDP_CHECKER_MONITORING_DB")
    if env_path:
        return env_path
    
    # Default: monitoring/data/usage.db relative to this file
    monitoring_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(monitoring_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "usage.db")


# =============================================================================
# CSV COLUMN ORDER (for export consistency with other tools)
# =============================================================================

CSV_COLUMNS = [
    # Time Period
    "timestamp",
    "period_start", 
    "period_end",
    "period_month",
    # User
    "user_email",
    # Session
    "session_id",
    "document_name",
    "template_name",
    # Checks & Findings
    "checks_run",
    "findings_total",
    "findings_critical",
    "findings_major",
    "findings_moderate",
    "findings_minor",
    # Comments (HITL)
    "comments_generated",
    "comments_approved",
    "comments_rejected",
    "comments_edited",
    # Timing
    "processing_time_seconds",
    "review_time_seconds",
    # Status
    "status",
    "error_message",
    # Productivity (matches Excel formula)
    "productivity_factor",
    "productivity_hours_saved",
]
