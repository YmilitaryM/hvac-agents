from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RootCauseCategory(str, Enum):
    SENSOR_FAULT = "SENSOR_FAULT"
    COMM_FAILURE = "COMM_FAILURE"
    DRIFT = "DRIFT"
    REAL_ANOMALY = "REAL_ANOMALY"
    PLC_FAULT = "PLC_FAULT"
    ENV_INTERFERENCE = "ENV_INTERFERENCE"


@dataclass
class Evidence:
    category: RootCauseCategory
    weight: float  # 0.0-1.0
    reason: str


@dataclass
class RootCauseResult:
    point_id: str
    equipment_id: str
    primary_cause: RootCauseCategory
    confidence: float  # 0.0-1.0
    evidence_list: list[Evidence] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RootCauseAnalyzer:
    def analyze(
        self,
        point_id: str,
        equipment_id: str,
        events: list,
        peer_data: dict | None = None,
    ) -> RootCauseResult:
        evidence_list: list[Evidence] = []

        # Rule 1: Communication failure -> COMM_FAILURE
        has_comm_loss = any(e.event_type == "communication_lost" for e in events)
        if has_comm_loss:
            evidence_list.append(
                Evidence(RootCauseCategory.COMM_FAILURE, 0.9, "Communication lost event detected")
            )

        # Rule 2: Frozen sensor + no comm loss -> SENSOR_FAULT
        has_frozen = any(e.event_type == "sensor_frozen" for e in events)
        if has_frozen and not has_comm_loss:
            evidence_list.append(
                Evidence(RootCauseCategory.SENSOR_FAULT, 0.8, "Frozen sensor detected without communication loss")
            )

        # Rule 3: Drift -> DRIFT
        has_drift = any(e.event_type == "drift_detected" for e in events)
        if has_drift:
            evidence_list.append(
                Evidence(RootCauseCategory.DRIFT, 0.7, "Drift detected via CUSUM+EWMA")
            )

        # Rule 4: Out of bounds + comm OK -> SENSOR_FAULT or PLC_FAULT
        has_oob = any(e.event_type == "out_of_bounds" for e in events)
        if has_oob:
            if has_comm_loss:
                evidence_list.append(
                    Evidence(RootCauseCategory.PLC_FAULT, 0.5, "Out of bounds with communication loss")
                )
            else:
                evidence_list.append(
                    Evidence(RootCauseCategory.SENSOR_FAULT, 0.6, "Out of bounds without communication loss")
                )

        # Rule 5: Peer deviation -> ENV_INTERFERENCE or REAL_ANOMALY
        has_peer = any(e.event_type == "peer_deviation" for e in events)
        if has_peer:
            evidence_list.append(
                Evidence(RootCauseCategory.ENV_INTERFERENCE, 0.4, "Peer deviation - possible local interference")
            )

        # Rule 6: Baseline deviation -> REAL_ANOMALY (could be real equipment issue)
        has_baseline = any(e.event_type == "baseline_deviation" for e in events)
        if has_baseline:
            evidence_list.append(
                Evidence(RootCauseCategory.REAL_ANOMALY, 0.5, "Baseline deviation detected")
            )

        if not evidence_list:
            evidence_list.append(
                Evidence(RootCauseCategory.REAL_ANOMALY, 0.1, "No specific evidence - default anomaly")
            )

        # Pick primary cause by highest weight
        best = max(evidence_list, key=lambda e: e.weight)
        confidence = best.weight

        return RootCauseResult(
            point_id=point_id,
            equipment_id=equipment_id,
            primary_cause=best.category,
            confidence=confidence,
            evidence_list=evidence_list,
        )
