import pytest
from src.schemas.state import AgentState, InvestDebateState, RiskDebateState
from src.schemas.equipment import PlantSnapshot, ChillerState, EquipmentStatus


class TestAgentState:
    def test_default_initialization(self):
        state = AgentState(messages=[])
        assert state["current_time"] == 0.0
        assert state["trigger_type"] == ""
        assert state["plant_snapshot"] is None
        assert state["predicted_load_rt"] is None
        assert state["advocate_opinions"] == []
        assert state["debate_round"] == 0
        assert state["max_debate_rounds"] == 2
        assert state["execution_status"] == "idle"
        assert state["anomaly_detected"] is False
        assert state["health_scores"] == {}
        assert state["alerts"] == []

    def test_messages_inherited(self):
        state = AgentState(messages=[{"role": "user", "content": "check plant"}])
        assert len(state["messages"]) == 1
        assert state["messages"][0]["role"] == "user"

    def test_set_plant_snapshot(self):
        snap = PlantSnapshot(
            chillers={
                "ch1": ChillerState(
                    device_id="ch1", capacity_rt=500,
                    status=EquipmentStatus.RUNNING, current_load_rt=300,
                )
            },
            cooling_towers={},
            chw_pumps={},
            cw_pumps={},
            outdoor_wb_temp=26.0,
            outdoor_db_temp=32.0,
        )
        state = AgentState(
            messages=[],
            plant_snapshot=snap.model_dump(),
            current_time=1716000000.0,
        )
        assert state["plant_snapshot"] is not None
        snap_dict = state["plant_snapshot"]
        assert snap_dict["outdoor_wb_temp"] == 26.0
        assert "ch1" in snap_dict["chillers"]

    def test_strategy_lifecycle_in_state(self):
        state = AgentState(messages=[])
        # No strategy initially
        assert state["current_strategy"] is None
        assert state["pending_strategy"] is None

        # Set pending strategy
        state["pending_strategy"] = {
            "strategy_id": "s_001",
            "trigger_type": "scheduled",
            "actions": [{"seq": 1, "device": "ch2", "action": "stop"}],
        }
        assert state["pending_strategy"]["strategy_id"] == "s_001"

    def test_debate_progression(self):
        state = AgentState(messages=[])
        state["advocate_opinions"] = [
            {"advocate": "reliability", "verdict": "approve", "concerns": [], "confidence": 0.9},
            {"advocate": "efficiency", "verdict": "approve", "concerns": [], "confidence": 0.85},
        ]
        state["debate_round"] = 1
        assert len(state["advocate_opinions"]) == 2
        assert state["debate_round"] == 1

    def test_alerts_accumulation(self):
        state = AgentState(messages=[])
        state["alerts"] = [
            {"level": "warning", "device": "ch1", "message": "high approach temp"},
            {"level": "critical", "device": "pump_2", "message": "vibration high"},
        ]
        assert len(state["alerts"]) == 2


class TestInvestDebateState:
    def test_initialization(self):
        debate = InvestDebateState(
            strategy_id="s_001",
            topic="Should we stop chiller_2 at 500RT load?",
            current_round=0,
            opinions=[],
            consensus_reached=False,
            final_verdict="",
        )
        assert debate["strategy_id"] == "s_001"
        assert debate["current_round"] == 0
        assert debate["consensus_reached"] is False

    def test_with_opinions(self):
        opinions = [
            {"advocate": "reliability", "verdict": "conditional_approval",
             "concerns": ["surge risk at 0.2 PLR"], "confidence": 0.75},
            {"advocate": "efficiency", "verdict": "approve",
             "concerns": [], "confidence": 0.9},
        ]
        debate = InvestDebateState(
            strategy_id="s_002",
            topic="Optimize load distribution",
            current_round=1,
            opinions=opinions,
            consensus_reached=False,
            final_verdict="",
        )
        assert len(debate["opinions"]) == 2

    def test_consensus_reached(self):
        debate = InvestDebateState(
            strategy_id="s_003",
            topic="Reduce chiller count",
            current_round=1,
            opinions=[
                {"advocate": "reliability", "verdict": "approve", "concerns": [], "confidence": 0.9},
                {"advocate": "efficiency", "verdict": "approve", "concerns": [], "confidence": 0.85},
                {"advocate": "compliance", "verdict": "approve", "concerns": [], "confidence": 0.88},
            ],
            consensus_reached=True,
            final_verdict="approve",
        )
        assert debate["consensus_reached"] is True
        assert debate["final_verdict"] == "approve"


class TestRiskDebateState:
    def test_initialization(self):
        risk = RiskDebateState(
            risk_type="surge",
            severity="high",
            source_advocate="reliability",
            affected_devices=["chiller_1"],
            resolution="",
            resolution_notes="",
        )
        assert risk["risk_type"] == "surge"
        assert risk["severity"] == "high"
        assert risk["source_advocate"] == "reliability"
        assert risk["affected_devices"] == ["chiller_1"]

    def test_resolved_risk(self):
        risk = RiskDebateState(
            risk_type="overload",
            severity="medium",
            source_advocate="safety",
            affected_devices=["chiller_2", "chiller_3"],
            resolution="mitigated",
            resolution_notes="Load redistributed to keep all chillers above 0.25 PLR",
        )
        assert risk["resolution"] == "mitigated"
        assert "0.25 PLR" in risk["resolution_notes"]

    def test_escalated_risk(self):
        risk = RiskDebateState(
            risk_type="maintenance",
            severity="critical",
            source_advocate="reliability",
            affected_devices=["chiller_1"],
            resolution="escalated",
            resolution_notes="Bearing temperature exceeds safety limit, immediate shutdown required",
        )
        assert risk["resolution"] == "escalated"
        assert risk["severity"] == "critical"
