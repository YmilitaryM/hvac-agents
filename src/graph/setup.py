"""LangGraph workflow setup for the HVAC multi-agent system.

7-Stage Flow:
  1. Monitor  -> anomaly detection
  2. Predict  -> load forecasting
  3. Strategy -> optimization
  4. Advocates -> review (3 parallel advocates)
  5. Coordinator -> arbitration (+ debate if needed)
  6. Safety   -> hard constraint checks
  7. Execute  -> finalize and record
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, END

from src.schemas.state import AgentState
from src.agents.base import BaseAgent
from .conditional_logic import (
    should_continue_after_monitor,
    should_generate_strategy,
    should_enter_debate,
    should_execute,
    should_reoptimize,
)
from .debate import run_debate

logger = logging.getLogger(__name__)


class HVACGraph:
    """Builds and manages the LangGraph workflow for HVAC chiller plant control."""

    def __init__(
        self,
        monitor_agent: Optional[BaseAgent] = None,
        predict_agent: Optional[BaseAgent] = None,
        strategy_agent: Optional[BaseAgent] = None,
        reliability_advocate: Optional[BaseAgent] = None,
        efficiency_advocate: Optional[BaseAgent] = None,
        compliance_advocate: Optional[BaseAgent] = None,
        coordinator_agent: Optional[BaseAgent] = None,
        safety_agent: Optional[BaseAgent] = None,
        parameter_agent: Optional[BaseAgent] = None,
        debug: bool = False,
    ):
        self.agents = {
            "monitor": monitor_agent,
            "predict": predict_agent,
            "strategy": strategy_agent,
            "reliability": reliability_advocate,
            "efficiency": efficiency_advocate,
            "compliance": compliance_advocate,
            "coordinator": coordinator_agent,
            "safety": safety_agent,
            "parameter": parameter_agent,
        }
        self.debug = debug
        self._graph = None

    def build(self) -> StateGraph:
        """Build and compile the StateGraph."""
        workflow = StateGraph(AgentState)

        # --- Add nodes ---
        workflow.add_node("monitor", self._monitor_node)
        workflow.add_node("predict", self._predict_node)
        workflow.add_node("strategy", self._strategy_node)
        workflow.add_node("advocates", self._advocates_node)
        workflow.add_node("coordinator", self._coordinator_node)
        workflow.add_node("debate", self._debate_node)
        workflow.add_node("safety", self._safety_node)
        workflow.add_node("parameter", self._parameter_node)
        workflow.add_node("execute", self._execute_node)

        # --- Add edges ---
        workflow.set_entry_point("monitor")

        # Monitor -> Predict (or END if critical anomaly)
        workflow.add_conditional_edges(
            "monitor",
            should_continue_after_monitor,
            {"predict": "predict", "end": END},
        )

        # Predict -> Strategy (or END if load stable)
        workflow.add_conditional_edges(
            "predict",
            should_generate_strategy,
            {"strategy": "strategy", "end": END},
        )

        # Strategy -> Advocates (always)
        workflow.add_edge("strategy", "advocates")

        # Advocates -> Coordinator (always)
        workflow.add_edge("advocates", "coordinator")

        # Coordinator -> Debate or Safety
        workflow.add_conditional_edges(
            "coordinator",
            should_enter_debate,
            {"debate": "debate", "safety": "safety"},
        )

        # Debate -> Safety (after debate resolves)
        workflow.add_edge("debate", "safety")

        # Safety -> Parameter or END
        workflow.add_conditional_edges(
            "safety",
            should_execute,
            {"execute": "parameter", "end": END},
        )

        # Parameter -> Re-optimize (back to Strategy) or Execute
        workflow.add_conditional_edges(
            "parameter",
            should_reoptimize,
            {"strategy": "strategy", "execute": "execute"},
        )

        # Execute -> END
        workflow.add_edge("execute", END)

        self._graph = workflow.compile(debug=self.debug)
        return self._graph

    @property
    def graph(self):
        if self._graph is None:
            self.build()
        return self._graph

    # --- Node implementations ---

    async def _monitor_node(self, state: AgentState) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.debug("Node: monitor — checking for anomalies")
        agent = self.agents["monitor"]
        if agent is None:
            return {
                "alerts": [],
                "health_scores": {},
                "anomaly_detected": False,
            }
        result = await agent.run(
            {"plant_snapshot": state.get("plant_snapshot", {})}
        )
        logger.debug(
            "Node: monitor — done (%.0fms) alerts=%d anomaly=%s",
            (time.monotonic() - t0) * 1000,
            len(result.get("alerts", [])),
            result.get("anomaly_detected"),
        )
        return result

    async def _predict_node(self, state: AgentState) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.debug("Node: predict — forecasting load")
        agent = self.agents["predict"]
        if agent is None:
            return {}
        weather = state.get("weather_data", {}) or {}
        snapshot = state.get("plant_snapshot", {}) or {}
        current_time = state.get("current_time", 0) or 0
        # Extract weather fields from weather_data dict or plant snapshot
        outdoor_temp = float(weather.get("outdoor_temp", snapshot.get("outdoor_db_temp", 32.0)))
        outdoor_humidity = float(weather.get("outdoor_humidity", snapshot.get("outdoor_humidity", 60.0)))
        # Derive time-of-day and day-of-week from current_time
        import datetime
        dt = datetime.datetime.fromtimestamp(current_time)
        hour_of_day = dt.hour
        day_of_week = dt.weekday()
        historical_load = (
            state.get("current_strategy", {}).get("current_load_rt")
            if state.get("current_strategy")
            else None
        )
        result = await agent.run(
            {
                "outdoor_temp": outdoor_temp,
                "outdoor_humidity": outdoor_humidity,
                "hour_of_day": hour_of_day,
                "day_of_week": day_of_week,
                "historical_load": historical_load,
                "current_time": current_time,
            }
        )
        forecast = result.get("load_forecast", {})
        logger.debug(
            "Node: predict — done (%.0fms) forecast_15min=%.0fRT",
            (time.monotonic() - t0) * 1000,
            forecast.get("load_15min", 0),
        )
        return {
            "predicted_load_rt": forecast.get("load_15min"),
            "load_forecast_15min": forecast.get("load_15min"),
            "load_forecast_1h": forecast.get("load_1h"),
            "load_forecast_6h": forecast.get("load_6h"),
        }

    async def _strategy_node(self, state: AgentState) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.debug("Node: strategy — optimizing chiller load distribution")
        agent = self.agents["strategy"]
        if agent is None:
            return {}
        predicted = state.get("predicted_load_rt", 0) or 0
        if predicted <= 0:
            current = state.get("current_strategy", {}) or {}
            predicted = (
                current.get("current_load_rt", 500)
                if isinstance(current, dict)
                else 500
            )

        snapshot = state.get("plant_snapshot", {}) or {}
        t_cw = float(snapshot.get("cw_supply_temp", snapshot.get("outdoor_wb_temp", 30.0)))
        t_chw = float(snapshot.get("chw_supply_temp", 7.0))
        result = await agent.run(
            {
                "total_load_rt": predicted,
                "t_cw": t_cw,
                "t_chw": t_chw,
                "current_time": state.get("current_time", 0),
                "predicted_load_rt": predicted,
                "trigger_type": state.get("trigger_type", "SCHEDULED"),
            }
        )
        strategy = result.get("strategy", {})
        logger.debug(
            "Node: strategy — done (%.0fms) status=%s actions=%d",
            (time.monotonic() - t0) * 1000,
            strategy.get("status", "?"),
            len(strategy.get("actions", [])),
        )
        return {"pending_strategy": strategy}

    async def _advocates_node(self, state: AgentState) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.debug("Node: advocates — running 3 advocate reviews")
        """Run all three advocates and collect their opinions."""
        strategy = state.get("pending_strategy", {})

        async def run_advocate(name: str) -> Dict:
            agent = self.agents.get(name)
            if agent is None:
                return {}
            return await agent.run({"strategy": strategy})

        results = await asyncio.gather(
            run_advocate("reliability"),
            run_advocate("efficiency"),
            run_advocate("compliance"),
        )

        opinions = []
        for r in results:
            if r and "opinion" in r:
                opinions.append(r["opinion"])

        logger.debug(
            "Node: advocates — done (%.0fms) opinions=%d",
            (time.monotonic() - t0) * 1000,
            len(opinions),
        )
        return {"advocate_opinions": opinions}

    async def _coordinator_node(self, state: AgentState) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.debug("Node: coordinator — arbitrating advocate opinions")
        agent = self.agents["coordinator"]
        if agent is None:
            return {}
        result = await agent.run(
            {
                "advocate_opinions": state.get("advocate_opinions", []),
                "pending_strategy": state.get("pending_strategy"),
            }
        )
        arb = result.get("arbitration_result", {})
        logger.debug(
            "Node: coordinator — done (%.0fms) decision=%s",
            (time.monotonic() - t0) * 1000,
            arb.get("decision", "?"),
        )
        return result

    async def _debate_node(self, state: AgentState) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.debug("Node: debate — running debate round")
        result = await run_debate(dict(state))
        logger.debug(
            "Node: debate — done (%.0fms) round=%d",
            (time.monotonic() - t0) * 1000,
            result.get("debate_round", 0),
        )
        return result

    async def _safety_node(self, state: AgentState) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.debug("Node: safety — checking hard constraints")
        agent = self.agents["safety"]
        if agent is None:
            return {
                "safety_result": {
                    "passed": True,
                    "failures": [],
                    "warnings": [],
                    "blocking": False,
                }
            }
        strategy = state.get("pending_strategy", {})
        snapshot = state.get("plant_snapshot", {}) or {}
        t_cw = float(snapshot.get("cw_supply_temp", snapshot.get("outdoor_wb_temp", 30.0)))
        result = await agent.run(
            {
                "pending_strategy": strategy,
                "t_cw": t_cw,
                "current_time": state.get("current_time", 0),
            }
        )
        sr = result.get("safety_result", {})
        logger.debug(
            "Node: safety — done (%.0fms) passed=%s",
            (time.monotonic() - t0) * 1000,
            sr.get("passed"),
        )
        return {"safety_result": sr}

    async def _parameter_node(self, state: AgentState) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.debug("Node: parameter — applying deadband, rate limit, PID")
        agent = self.agents["parameter"]
        if agent is None:
            return {"parameter_adjustments": [], "needs_new_strategy": False}

        strategy = state.get("pending_strategy") or {}
        snapshot = state.get("plant_snapshot") or {}
        chillers = snapshot.get("chillers", {})

        # Extract target loads from strategy actions
        target_loads = {}
        for action in strategy.get("actions", []):
            if action.get("action") == "set_load" and action.get("value", 0) > 0:
                target_loads[action["device"]] = action["value"]

        # Extract current loads from snapshot
        current_loads = {}
        for name, data in chillers.items():
            if isinstance(data, dict) and data.get("load_rt", 0) > 0:
                current_loads[name] = data["load_rt"]

        # Build capacity map
        capacity_rt = {}
        for name in set(list(target_loads.keys()) + list(current_loads.keys())):
            capacity_rt[name] = 500.0

        result = await agent.run({
            "target_loads": target_loads,
            "current_loads": current_loads,
            "capacity_rt": capacity_rt,
        })

        adjustments = result.get("adjustments", [])
        needs_new = result.get("needs_new_strategy", False)
        reopt_count = state.get("reoptimization_count", 0)

        logger.debug(
            "Node: parameter — done (%.0fms) adjustments=%d needs_new=%s",
            (time.monotonic() - t0) * 1000,
            len(adjustments),
            needs_new,
        )
        return {
            "parameter_adjustments": adjustments,
            "needs_new_strategy": needs_new,
            "reoptimization_count": reopt_count + (1 if needs_new else 0),
        }

    async def _execute_node(self, state: AgentState) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.debug("Node: execute — finalizing strategy")
        """Finalize: move pending_strategy to current_strategy, record in history."""
        pending = state.get("pending_strategy", {})
        history = list(state.get("strategy_history", []))

        if pending:
            arb = state.get("arbitration_result", {}) or {}
            decision = arb.get("decision", "approved")
            pending["status"] = decision
            history.append(
                {
                    "strategy_id": pending.get("strategy_id", ""),
                    "timestamp": state.get("current_time", 0),
                    "actions": pending.get("actions", []),
                }
            )

        logger.debug(
            "Node: execute — done (%.0fms) status=%s history=%d",
            (time.monotonic() - t0) * 1000,
            pending.get("status", "?") if pending else "noop",
            len(history),
        )
        return {
            "current_strategy": pending,
            "pending_strategy": None,
            "strategy_history": history,
            "execution_status": "completed",
        }

    async def run(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.monotonic()
        logger.info("Starting HVAC pipeline run (trigger=%s)", initial_state.get("trigger_type", "?"))
        """Run the full workflow with the given initial state."""
        state = AgentState(**initial_state)
        result = await self.graph.ainvoke(state)
        logger.info(
            "Pipeline complete (%.0fms) — execution=%s",
            (time.monotonic() - t0) * 1000,
            result.get("execution_status", "?"),
        )
        return result
