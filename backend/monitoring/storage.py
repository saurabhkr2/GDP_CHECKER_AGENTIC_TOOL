"""
Storage layer for GDP Checker raw monitoring data.

Uses SQLite for portable local storage (works on any VM).
Exports to CSV format similar to ChatGPT_May.csv and Github_May.csv.
"""
from __future__ import annotations

import csv
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional, Dict, Any, Generator

from .schema import (
    GDPCheckerUsageRecord,
    USAGE_TABLE_SQL,
    CSV_COLUMNS,
    get_default_db_path,
)


class MonitoringStorage:
    """
    Thread-safe SQLite storage for GDP Checker monitoring data.
    
    Designed for portability:
    - Uses local SQLite file (no external DB required)
    - Path configurable via GDP_CHECKER_MONITORING_DB env var
    - Works on local dev and VM deployments
    - Exports to CSV format like ChatGPT_May.csv, Github_May.csv
    """
    
    _local = threading.local()
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_default_db_path()
        self._ensure_directory()
        self._init_db()
    
    def _ensure_directory(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_db(self) -> None:
        with self._cursor() as cursor:
            cursor.executescript(USAGE_TABLE_SQL)
    
    def save_record(self, record: GDPCheckerUsageRecord) -> None:
        data = record.to_dict()
        columns = [c for c in CSV_COLUMNS if c in data]
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        sql = f"INSERT OR REPLACE INTO gdp_checker_usage ({columns_str}) VALUES ({placeholders})"
        with self._cursor() as cursor:
            cursor.execute(sql, [data.get(c) for c in columns])
    
    def get_record(self, session_id: str) -> Optional[GDPCheckerUsageRecord]:
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM gdp_checker_usage WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return GDPCheckerUsageRecord.from_dict(dict(row))
        return None
    
    def get_records_by_period(self, period_month: str) -> List[GDPCheckerUsageRecord]:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM gdp_checker_usage WHERE period_month = ? ORDER BY timestamp",
                (period_month,)
            )
            rows = cursor.fetchall()
            return [GDPCheckerUsageRecord.from_dict(dict(row)) for row in rows]
    
    def get_records_by_user(self, user_email: str) -> List[GDPCheckerUsageRecord]:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM gdp_checker_usage WHERE user_email = ? ORDER BY timestamp",
                (user_email,)
            )
            rows = cursor.fetchall()
            return [GDPCheckerUsageRecord.from_dict(dict(row)) for row in rows]
    
    def get_all_records(self, limit: int = 10000) -> List[GDPCheckerUsageRecord]:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM gdp_checker_usage ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [GDPCheckerUsageRecord.from_dict(dict(row)) for row in rows]
    
    def delete_record(self, session_id: str) -> bool:
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM gdp_checker_usage WHERE session_id = ?", (session_id,))
            return cursor.rowcount > 0
    
    def export_to_csv(self, output_path: str, period_month: Optional[str] = None) -> str:
        if period_month:
            records = self.get_records_by_period(period_month)
        else:
            records = self.get_all_records()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for record in records:
                writer.writerow({k: record.to_dict().get(k) for k in CSV_COLUMNS})
        
        return output_path
    
    def get_summary_stats(self) -> Dict[str, Any]:
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(DISTINCT user_email) as unique_users,
                    SUM(checks_run) as total_checks,
                    SUM(findings_total) as total_findings,
                    SUM(comments_generated) as total_comments_generated,
                    SUM(comments_approved) as total_comments_approved,
                    SUM(comments_rejected) as total_comments_rejected,
                    SUM(productivity_hours_saved) as total_hours_saved,
                    AVG(processing_time_seconds) as avg_processing_time
                FROM gdp_checker_usage
                WHERE status = 'completed'
            """)
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def close(self) -> None:
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


_storage_instance: Optional[MonitoringStorage] = None
_storage_lock = threading.Lock()


def get_storage(db_path: Optional[str] = None) -> MonitoringStorage:
    global _storage_instance
    if _storage_instance is None:
        with _storage_lock:
            if _storage_instance is None:
                _storage_instance = MonitoringStorage(db_path)
    return _storage_instance


def reset_storage() -> None:
    global _storage_instance
    with _storage_lock:
        if _storage_instance:
            _storage_instance.close()
        _storage_instance = None
