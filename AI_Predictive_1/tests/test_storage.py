"""
test_storage.py
---------------
Automated unit tests for SQLite local storage, event persistence,
status transitions, operator acknowledgements, and agentic maintenance workflows.
"""

import unittest
import tempfile
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pump_pm.storage.repository import MaintenanceRepository
from pump_pm.workflows.maintenance_workflow import AgenticMaintenanceWorkflow


class TestStorage(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_maintenance.db")
        self.repo = MaintenanceRepository(db_path=self.db_path)
        self.workflow = AgenticMaintenanceWorkflow(repository=self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_get_events(self):
        event_data = {
            "machine_id": "M1201",
            "timestamp": "2024-04-15",
            "source": "RULE_ENGINE",
            "severity_zone": "Zone D (Hazardous / Damage risk)",
            "alarm_status": "TRIP",
            "max_vibration": 8.8,
            "dominant_location": "P1",
            "candidate_faults": [{"fault_name": "Rotor Imbalance", "confidence_score": 0.85}],
            "supporting_evidence": ["Dominant 1x radial velocity at 8.8 mm/s"],
            "missing_evidence": ["Dynamic phase vector survey"],
            "anomaly_score": -0.15,
            "status": "OPEN"
        }

        event_id = self.repo.record_event(event_data)
        self.assertGreater(event_id, 0)

        # Retrieve events
        events = self.repo.get_events(machine_id="M1201")
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["machine_id"], "M1201")
        self.assertEqual(ev["severity_zone"], "Zone D (Hazardous / Damage risk)")
        self.assertEqual(ev["status"], "OPEN")
        self.assertEqual(ev["candidate_faults"][0]["fault_name"], "Rotor Imbalance")

        # Verify audit trail
        audit = self.repo.get_audit_trail(event_id)
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["action_type"], "CREATED")

    def test_acknowledge_and_workflow(self):
        event_id = self.repo.record_event({
            "machine_id": "M1202",
            "timestamp": "2024-08-20",
            "source": "TEST",
            "severity_zone": "Zone C",
            "alarm_status": "ALARM",
            "max_vibration": 7.2,
            "dominant_location": "P2",
            "candidate_faults": [{"fault_name": "Shaft or Coupling Misalignment", "confidence_score": 0.80}],
            "supporting_evidence": ["High axial vibration on coupling bearings"],
            "missing_evidence": ["Laser alignment check"],
            "status": "OPEN"
        })

        # Acknowledge event
        success = self.repo.acknowledge_event(event_id, acknowledged_by="Reliability_Lead", notes="Scheduled alignment check on next shift.")
        self.assertTrue(success)

        events = self.repo.get_events(status="ACKNOWLEDGED")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["acknowledged_by"], "Reliability_Lead")

        # Test agentic workflow task drafting
        draft = self.workflow.review_event_and_draft_task(event_id)
        self.assertEqual(draft["machine_id"], "M1202")
        self.assertIn("laser shaft alignment", draft["drafted_inspection_task"].lower())
        self.assertTrue(draft["requires_human_approval"])

        # Approve and resolve maintenance action
        resolved = self.workflow.approve_and_record_action(
            event_id=event_id,
            approved_by="Shift_Manager",
            action_taken="Realigned coupling using laser tool; adjusted horizontal offset by 0.15mm.",
            post_maintenance_notes="Post-run vibration dropped to 2.1 mm/s (Zone A)."
        )
        self.assertTrue(resolved)

        resolved_events = self.repo.get_events(status="RESOLVED")
        self.assertEqual(len(resolved_events), 1)
        self.assertEqual(resolved_events[0]["action_taken"], "Realigned coupling using laser tool; adjusted horizontal offset by 0.15mm.")


if __name__ == "__main__":
    unittest.main()
