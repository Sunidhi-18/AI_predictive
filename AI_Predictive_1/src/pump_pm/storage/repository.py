"""
repository.py
-------------
Local SQLite database persistence for condition monitoring events, operator acknowledgements,
work orders, and immutable audit trails.
"""

import os
import sqlite3
import json
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime


DEFAULT_DB_PATH = "data/database/maintenance.db"


class MaintenanceRepository:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Maintenance Events table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                severity_zone TEXT NOT NULL,
                alarm_status TEXT NOT NULL,
                max_vibration REAL,
                dominant_location TEXT,
                candidate_faults TEXT,      -- JSON string
                supporting_evidence TEXT,   -- JSON string
                missing_evidence TEXT,      -- JSON string
                anomaly_score REAL,
                model_version TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN', -- OPEN, ACKNOWLEDGED, UNDER_INSPECTION, RESOLVED, FALSE_ALARM
                acknowledgement_notes TEXT,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                work_order_id TEXT,
                action_taken TEXT,
                completion_timestamp TEXT,
                post_maintenance_notes TEXT,
                created_at TEXT NOT NULL
            );
            """)

            # 2. Immutable Audit Trail table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                action_type TEXT NOT NULL, -- CREATED, ACKNOWLEDGED, WORK_ORDER_ISSUED, COMPLETED, NOTE_ADDED
                performed_by TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (event_id) REFERENCES events (event_id)
            );
            """)

            conn.commit()

    def record_event(self, event_data: Dict[str, Any]) -> int:
        """
        Inserts a newly detected event into the database and logs to the audit trail.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
            INSERT INTO events (
                machine_id, timestamp, source, severity_zone, alarm_status,
                max_vibration, dominant_location, candidate_faults,
                supporting_evidence, missing_evidence, anomaly_score,
                model_version, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_data.get("machine_id"),
                event_data.get("timestamp"),
                event_data.get("source", "PIPELINE"),
                event_data.get("severity_zone", "Zone A"),
                event_data.get("alarm_status", "NORMAL"),
                event_data.get("max_vibration"),
                event_data.get("dominant_location"),
                json.dumps(event_data.get("candidate_faults", [])),
                json.dumps(event_data.get("supporting_evidence", [])),
                json.dumps(event_data.get("missing_evidence", [])),
                event_data.get("anomaly_score"),
                event_data.get("model_version", "1.0.0"),
                event_data.get("status", "OPEN"),
                now
            ))
            event_id = cursor.lastrowid

            cursor.execute("""
            INSERT INTO audit_trail (event_id, action_type, performed_by, timestamp, details)
            VALUES (?, 'CREATED', 'SYSTEM', ?, ?)
            """, (event_id, now, f"Event triggered by {event_data.get('source', 'PIPELINE')}"))

            conn.commit()
            return event_id

    def record_events_batch(self, events_list: List[Dict[str, Any]]) -> int:
        """
        Inserts multiple newly detected events into the database in a single atomic transaction.
        """
        if not events_list:
            return 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            inserted = 0
            for event_data in events_list:
                cursor.execute("""
                INSERT INTO events (
                    machine_id, timestamp, source, severity_zone, alarm_status,
                    max_vibration, dominant_location, candidate_faults,
                    supporting_evidence, missing_evidence, anomaly_score,
                    model_version, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_data.get("machine_id"),
                    event_data.get("timestamp"),
                    event_data.get("source", "PIPELINE"),
                    event_data.get("severity_zone", "Zone A"),
                    event_data.get("alarm_status", "NORMAL"),
                    event_data.get("max_vibration"),
                    event_data.get("dominant_location"),
                    json.dumps(event_data.get("candidate_faults", [])),
                    json.dumps(event_data.get("supporting_evidence", [])),
                    json.dumps(event_data.get("missing_evidence", [])),
                    event_data.get("anomaly_score"),
                    event_data.get("model_version", "1.0.0"),
                    event_data.get("status", "OPEN"),
                    now
                ))
                event_id = cursor.lastrowid
                cursor.execute("""
                INSERT INTO audit_trail (event_id, action_type, performed_by, timestamp, details)
                VALUES (?, 'CREATED', 'SYSTEM', ?, ?)
                """, (event_id, now, f"Event triggered by {event_data.get('source', 'PIPELINE')}"))
                inserted += 1
            conn.commit()
            return inserted

    def get_events(

        self,
        machine_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Queries maintenance events with optional machine and status filters.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM events WHERE 1=1"
            params = []

            if machine_id:
                query += " AND machine_id = ?"
                params.append(machine_id)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY event_id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for r in rows:
                d = dict(r)
                # Parse JSON fields
                d["candidate_faults"] = json.loads(d["candidate_faults"]) if d.get("candidate_faults") else []
                d["supporting_evidence"] = json.loads(d["supporting_evidence"]) if d.get("supporting_evidence") else []
                d["missing_evidence"] = json.loads(d["missing_evidence"]) if d.get("missing_evidence") else []
                results.append(d)
            return results

    def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single maintenance event by its primary key ID.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["candidate_faults"] = json.loads(d["candidate_faults"]) if d.get("candidate_faults") else []
            d["supporting_evidence"] = json.loads(d["supporting_evidence"]) if d.get("supporting_evidence") else []
            d["missing_evidence"] = json.loads(d["missing_evidence"]) if d.get("missing_evidence") else []
            return d

    def acknowledge_event(

        self,
        event_id: int,
        acknowledged_by: str,
        notes: str
    ) -> bool:
        """
        Acknowledges an open event, transitions status to ACKNOWLEDGED, and appends to audit trail.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
            UPDATE events SET
                status = 'ACKNOWLEDGED',
                acknowledged_by = ?,
                acknowledgement_notes = ?,
                acknowledged_at = ?
            WHERE event_id = ?
            """, (acknowledged_by, notes, now, event_id))

            cursor.execute("""
            INSERT INTO audit_trail (event_id, action_type, performed_by, timestamp, details)
            VALUES (?, 'ACKNOWLEDGED', ?, ?, ?)
            """, (event_id, acknowledged_by, now, notes))

            conn.commit()
            return cursor.rowcount > 0

    def complete_maintenance(
        self,
        event_id: int,
        action_taken: str,
        post_notes: str,
        performed_by: str = "MAINTENANCE_SUPERVISOR"
    ) -> bool:
        """
        Resolves an event, records physical maintenance actions taken, and records completion time.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
            UPDATE events SET
                status = 'RESOLVED',
                action_taken = ?,
                post_maintenance_notes = ?,
                completion_timestamp = ?
            WHERE event_id = ?
            """, (action_taken, post_notes, now, event_id))

            cursor.execute("""
            INSERT INTO audit_trail (event_id, action_type, performed_by, timestamp, details)
            VALUES (?, 'COMPLETED', ?, ?, ?)
            """, (event_id, performed_by, now, f"Action: {action_taken} | Post-check: {post_notes}"))

            conn.commit()
            return cursor.rowcount > 0

    def get_audit_trail(self, event_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_trail WHERE event_id = ? ORDER BY audit_id ASC", (event_id,))
            return [dict(r) for r in cursor.fetchall()]
