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
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, END

from src.schemas.state import AgentState
from src.agents.base import BaseAgent
from .conditional_logic import (
    should_continue_after_monitor,
    should_generate_strategy,
    should_enter_debate,
    should_execute,
)
from .debate import run_debate


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

        # Safety -> Execute or END
        workflow.add_conditional_edges(
            "safety",
            should_execute,
            {"execute": "execute", "end": END},
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
        return result

    async def _predict_node(self, state: AgentState) -> Dict[str, Any]:
        agent = self.agents["predict"]
        if agent is None:
            return {}
        result = await agent.run(
            {
                "weather_data": state.get("weather_data", {}),
                "historical_load": (
                    state.get("current_strategy", {}).get("current_load_rt")
                    if state.get("current_strategy")
                    else None
                ),
                "current_time": state.get("current_time", 0),
            }
        )
        forecast = result.get("forecast", {})
        return {
            "predicted_load_rt": forecast.get("load_15min"),
            "load_forecast_15min": forecast.get("load_15min"),
            "load_forecast_1h": forecast.get("load_1h"),
            "load_forecast_6h": forecast.get("load_6h"),
        }

    async def _strategy_node(self, state: AgentState) -> Dict[str, Any]:
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

        result = await agent.run(
            {
                "total_load_rt": predicted,
                "t_cw": 30.0,
                "t_chw": 7.0,
                "current_time": state.get("current_time", 0),
                "predicted_load_rt": predicted,
                "trigger_type": state.get("trigger_type", "SCHEDULED"),
            }
        )
        return {"pending_strategy": result.get("strategy")}

    async def _advocates_node(self, state: AgentState) -> Dict[str, Any]:
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

        return {"advocate_opinions": opinions}

    async def _coordinator_node(self, state: AgentState) -> Dict[str, Any]:
        agent = self.agents["coordinator"]
        if agent is None:
            return {}
        result = await agent.run(
            {
                "advocate_opinions": state.get("advocate_opinions", []),
                "pending_strategy": state.get("pending_strategy"),
            }
        )
        return result

    async def _debate_node(self, state: AgentState) -> Dict[str, Any]:
        result = await run_debate(dict(state))
        return result

    async def _safety_node(self, state: AgentState) -> Dict[str, Any]:
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
        result = await agent.run(
            {
                "pending_strategy": strategy,
                "t_cw": 30.0,
                "current_time": state.get("current_time", 0),
            }
        )
        return {"safety_result": result.get("safety_result", {})}

    async def _execute_node(self, state: AgentState) -> Dict[str, Any]:
        """Finalize: move pending_strategy to current_strategy, record in history."""
        pending = state.get("pending_strategy", {})
        history = list(state.get("strategy_history", []))

        if pending:
            pending["status"] = "approved"
            history.append(
                {
                    "strategy_id": pending.get("strategy_id", ""),
                    "timestamp": state.get("current_time", 0),
                    "actions": pending.get("actions", []),
                }
            )

        return {
            "current_strategy": pending,
            "pending_strategy": None,
            "strategy_history": history,
            "execution_status": "completed",
        }

    async def run(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full workflow with the given initial state."""
        state = AgentState(**initial_state)
        result = await self.graph.ainvoke(state)
        return result
