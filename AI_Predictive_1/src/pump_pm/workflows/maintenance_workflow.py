"""
maintenance_workflow.py
-----------------------
Locally orchestrated deterministic agentic AI maintenance workflow.
Drafts maintenance inspection recommendations, identifies evidence gaps,
and enforces human-in-the-loop approval before recording maintenance actions.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from ..storage.repository import MaintenanceRepository


class AgenticMaintenanceWorkflow:
    def __init__(self, repository: Optional[MaintenanceRepository] = None):
        self.repo = repository or MaintenanceRepository()

    def review_event_and_draft_task(self, event_id: int) -> Dict[str, Any]:
        """
        Step 1 & 2: Reads an existing event, synthesizes observed evidence vs uncertainties,
        and drafts an actionable inspection recommendation.
        """
        target_event = self.repo.get_event_by_id(event_id)
        if not target_event:
            # Fallback to general lookup
            events = self.repo.get_events(limit=5000)
            target_event = next((e for e in events if e["event_id"] == event_id), None)
            
        if not target_event:
            return {
                "event_id": event_id,
                "machine_id": "Unknown",
                "summary": f"Event #{event_id} details pending or archived.",
                "uncertainty_assessment": "Verification required.",
                "drafted_inspection_task": "Review telemetry recordings and perform standard walkdown vibration survey."
            }


        machine_id = target_event["machine_id"]
        dominant_fault = target_event["candidate_faults"][0]["fault_name"] if target_event["candidate_faults"] else "Unclassified Anomaly"
        sup_evidence = target_event["supporting_evidence"]
        miss_evidence = target_event["missing_evidence"]
        zone = target_event["severity_zone"]
        v_max = target_event.get("max_vibration", 0.0)

        # Build synthesized summary
        summary = (
            f"Machine {machine_id} exhibited {zone} operating severity (Peak: {v_max:.2f} mm/s RMS). "
            f"Primary diagnostic candidate is '{dominant_fault}'. "
        )
        if sup_evidence:
            summary += f"Observed symptoms: {'; '.join(sup_evidence[:2])}. "

        # Identify uncertainties
        uncertainty = ""
        if miss_evidence:
            uncertainty = f"Key missing evidence required to confirm hypothesis: {'; '.join(miss_evidence[:2])}."
        else:
            uncertainty = "Secondary verification required prior to intrusive mechanical teardown."

        # Draft Recommended Task
        if "Imbalance" in dominant_fault:
            drafted_task = "Conduct single-plane dynamic field balance check on pump coupling; inspect impeller vanes for particulate buildup."
        elif "Misalignment" in dominant_fault:
            drafted_task = "Check flexible coupling element for elastomeric wear; perform hot/cold laser shaft alignment across pump and motor hubs."
        elif "Bearing" in dominant_fault:
            drafted_task = "Collect high-frequency acoustic emission / PeakVue reading; replenish bearing lubrication and schedule bearing replacement."
        elif "Looseness" in dominant_fault:
            drafted_task = "Check torque on baseplate anchor bolts; perform dial indicator survey for soft foot."
        else:
            drafted_task = "Perform walkdown vibration spectrum survey using portable analyzer; verify transmitter cable continuity."

        draft = {
            "event_id": event_id,
            "machine_id": machine_id,
            "summary": summary,
            "uncertainty_assessment": uncertainty,
            "drafted_inspection_task": drafted_task,
            "requires_human_approval": True,
            "generated_at": datetime.now().isoformat()
        }
        return draft

    def approve_and_record_action(
        self,
        event_id: int,
        approved_by: str,
        action_taken: str,
        post_maintenance_notes: str
    ) -> bool:
        """
        Step 5 & 6: Human operator reviews and signs off on maintenance action.
        Persists verified action into local database audit trail.
        """
        return self.repo.complete_maintenance(
            event_id=event_id,
            action_taken=action_taken,
            post_notes=post_maintenance_notes,
            performed_by=approved_by
        )
