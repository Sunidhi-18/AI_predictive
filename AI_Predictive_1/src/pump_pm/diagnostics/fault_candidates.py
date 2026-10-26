"""
fault_candidates.py
-------------------
Data models and structure for diagnostic candidates with supporting and missing evidence.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class FaultCandidate:
    fault_name: str
    fault_family: str  # mechanical, bearing, hydraulic, electrical, tribology, instrumentation, indeterminate
    confidence_score: float  # Heuristic score [0.0, 1.0]
    evidence_level: str  # HIGH, MODERATE, LOW, INSUFFICIENT
    selection_reason: str
    supporting_evidence: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    relevant_locations: List[str] = field(default_factory=list)
    recommended_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fault_name": self.fault_name,
            "fault_family": self.fault_family,
            "confidence_score": round(float(self.confidence_score), 2),
            "evidence_level": self.evidence_level,
            "selection_reason": self.selection_reason,
            "supporting_evidence": self.supporting_evidence,
            "missing_evidence": self.missing_evidence,
            "relevant_locations": self.relevant_locations,
            "recommended_action": self.recommended_action
        }


@dataclass
class DiagnosticEvaluation:
    machine_id: str
    timestamp: str
    governing_zone: str
    candidates: List[FaultCandidate] = field(default_factory=list)
    dominant_hypothesis: Optional[FaultCandidate] = None
    uncertainty_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "timestamp": self.timestamp,
            "governing_zone": self.governing_zone,
            "dominant_hypothesis": self.dominant_hypothesis.to_dict() if self.dominant_hypothesis else None,
            "candidates": [c.to_dict() for c in self.candidates],
            "uncertainty_note": self.uncertainty_note
        }
