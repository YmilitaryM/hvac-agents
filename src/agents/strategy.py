"""Strategy Agent — generates optimization strategies for chiller plant control.

Uses the ChillerPlantOptimizer to find the best chiller load distribution,
then converts the solution into a Strategy with actions and a transition plan.

Core logic is in build_strategy() — pure Python, no LLM required.
LLM integration can be layered on top later for strategy explanation and reasoning.
"""

import time as time_module
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent, AgentContext
from src.optimization.solver import ChillerPlantOptimizer, OptimizationSolution
from src.reports.kpi_calculator import KW_PER_RT
from src.schemas.strategy import (
    Strategy,
    StrategyAction,
    StrategyStatus,
    TransitionPhase,
    TransitionPlan,
    TriggerType,
)


def build_strategy(
    solution: OptimizationSolution,
    current_load_rt: float,
    predicted_load_rt: float,
    current_time: Optional[float] = None,
    strategy_id: Optional[str] = None,
    trigger_type: str = "SCHEDULED",
    previous_loads: Optional[Dict[str, float]] = None,
    electricity_price: float = 0.8,
    grid_carbon_intensity: float = 0.5,
    carbon_price: float = 0.08,
    outdoor_wb_temp: float = 26.0,
) -> Strategy:
    """Convert an optimization solution into a Strategy with transition plan.

    Creates StrategyActions for each chiller:
      - "start" + "set_load" for chillers with positive target load
      - "stop" for chillers with zero target load

    and a TransitionPlan with a single ramp phase plus abort conditions.

    Args:
        solution: OptimizationSolution from the solver.
        current_load_rt: Current total plant load in RT.
        predicted_load_rt: Forecasted load in RT.
        current_time: Unix timestamp for strategy creation (defaults to now).
        strategy_id: Optional explicit strategy ID (auto-generated if omitted).
        trigger_type: One of "SCHEDULED", "LOAD_CHANGE", "FAULT", etc.
        previous_loads: Optional dict mapping chiller name -> previous load in RT.
        electricity_price: Electricity price in currency/kWh.
        grid_carbon_intensity: Grid carbon intensity in kgCO2/kWh.
        carbon_price: Carbon price in currency/kgCO2.
        outdoor_wb_temp: Outdoor wet-bulb temperature in degC.

    Returns:
        A Strategy ready for review and execution.
    """
    if current_time is None:
        current_time = time_module.time()

    if strategy_id is None:
        strategy_id = f"strat_{int(current_time)}"

    previous_loads = previous_loads or {}

    # --- Build actions for each chiller ---
    actions: List[StrategyAction] = []
    seq = 1
    has_start_stop = False

    for device, load in sorted(solution.chiller_loads.items()):
        prev_load = previous_loads.get(device, None)

        if load > 0:
            # If previous load was 0 or unknown, add a start action
            if prev_load is None or prev_load <= 0:
                actions.append(StrategyAction(
                    seq=seq, device=device, action="start",
                ))
                seq += 1
                has_start_stop = True

            # Always add a set_load action with the target load
            actions.append(StrategyAction(
                seq=seq, device=device, action="set_load", value=round(load, 1),
            ))
            seq += 1
        else:
            # Chiller should be stopped
            if prev_load is None or prev_load > 0:
                actions.append(StrategyAction(
                    seq=seq, device=device, action="stop",
                ))
                seq += 1
                has_start_stop = True

    # --- Build transition plan ---
    # Use 600s when start/stop operations are involved (equipment has thermal inertia)
    # Use 300s for load-only adjustments
    ramp_duration = 600.0 if has_start_stop else 300.0
    stability_duration = 60.0  # post-ramp stabilization window

    phase = TransitionPhase(
        seq=1,
        duration_sec=ramp_duration,
        description=f"Ramp chillers to optimized loads ({ramp_duration:.0f}s ramp)",
        actions=actions,
        stability_check={
            "check_type": "power_stable",
            "window_sec": 60,
            "max_deviation_pct": 5.0,
        },
    )

    transition_plan = TransitionPlan(
        total_duration_sec=ramp_duration + stability_duration,
        phases=[phase],
        abort_conditions=[
            "Any chiller enters FAULT or SURGE state during transition",
            "System COP drops below 2.0 during transition",
            "CHW supply temp deviates >2 degC from setpoint",
            "CW return temp exceeds 40 degC",
        ],
    )

    # --- Calculate expected improvements ---
    cooling_kw = current_load_rt * KW_PER_RT
    baseline_cop = 5.0  # conservative baseline for typical sub-optimal operation
    baseline_power = cooling_kw / baseline_cop if baseline_cop > 0 else float("inf")
    optimized_power = solution.total_power_kw
    optimized_cop = cooling_kw / optimized_power if optimized_power > 0 else 0.0

    if baseline_power > 0 and optimized_power > 0:
        cop_improvement = (optimized_cop - baseline_cop) / baseline_cop
        energy_saving = baseline_power - optimized_power
    else:
        cop_improvement = 0.0
        energy_saving = 0.0

    # --- Preconditions ---
    preconditions = [
        f"total_load >= {current_load_rt * 0.8:.0f} RT",
        "No chiller in FAULT state",
        "CW supply temp within design range",
        "All required pumps available",
    ]

    # Determine status based on feasibility
    status = StrategyStatus.DRAFT if solution.is_feasible else StrategyStatus.REJECTED

    # TriggerType values are lowercase ("scheduled"), but callers may pass
    # uppercase names ("SCHEDULED") or lowercase values. Try both.
    try:
        trigger_enum = TriggerType(trigger_type)
    except ValueError:
        trigger_enum = TriggerType[trigger_type.upper()] if trigger_type.upper() in TriggerType.__members__ else TriggerType.SCHEDULED

    return Strategy(
        strategy_id=strategy_id,
        trigger_type=trigger_enum,
        trigger_time=current_time,
        current_load_rt=current_load_rt,
        predicted_load_rt=predicted_load_rt,
        outdoor_wb_temp=outdoor_wb_temp,
        electricity_price=electricity_price,
        carbon_intensity=grid_carbon_intensity,
        actions=actions,
        transition_plan=transition_plan,
        preconditions=preconditions,
        expected_cop_improvement=round(cop_improvement, 4),
        expected_energy_saving_kwh_per_h=round(energy_saving, 2),
        status=status,
    )


def _build_strategy_reasoning_prompt(
    strategy: Strategy,
    solution: OptimizationSolution,
    total_load_rt: float,
    t_cw: float,
    t_chw: float,
) -> str:
    """Build a prompt for LLM to generate strategy reasoning narrative."""
    loads_desc = ", ".join(
        f"{dev}={load:.0f}RT" for dev, load in solution.chiller_loads.items()
    )
    return (
        "你是一个暖通空调冷水机组优化专家。请用2-3句中文简要解释以下优化策略的推理过程：\n\n"
        f"总冷负荷: {total_load_rt:.0f} RT\n"
        f"冷却水进水温度: {t_cw:.1f}°C\n"
        f"冷冻水出水温度: {t_chw:.1f}°C\n"
        f"机组负荷分配: {loads_desc}\n"
        f"预计总功率: {solution.total_power_kw:.1f} kW\n"
        f"预计COP改善: {strategy.expected_cop_improvement:.2%}\n"
        f"是否可行: {'是' if solution.is_feasible else '否'}\n"
        f"约束违反: {', '.join(solution.constraint_violations) if solution.constraint_violations else '无'}\n"
        f"运行动作数: {len(strategy.actions)}\n"
        "\n请简要解释优化决策的理由、关键权衡和预期效果。"
    )


class StrategyAgent(BaseAgent):
    """Strategy Agent — generates optimization strategies using the optimizer.

    Accepts an optional LLM for strategy explanation/reasoning, but the core
    optimization logic runs locally via the ChillerPlantOptimizer.

    Input keys:
        total_load_rt: Total plant cooling load in RT.
        t_cw: Condenser water entering temperature in degC.
        t_chw: Chilled water supply temperature setpoint in degC (default 7.0).
        current_time: Optional Unix timestamp.
        predicted_load_rt: Optional forecasted load in RT.
        price_per_kwh: Electricity price (default 0.8).
        grid_carbon_intensity: Grid carbon intensity kgCO2/kWh (default 0.5).
        carbon_price: Carbon price in currency/kgCO2 (default 0.08).
        trigger_type: Strategy trigger type (default "SCHEDULED").

    Output keys:
        strategy: Serialized Strategy dict.
        solution: Serialized OptimizationSolution dict.
    """

    def __init__(self, llm=None, optimizer=None, context=None, doc_store=None):
        super().__init__(name="strategy", llm=llm, context=context)
        self.optimizer = optimizer
        self.doc_store = doc_store

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the optimizer and produce a Strategy.

        Args:
            input_data: Dict with total_load_rt, t_cw, and optional parameters.

        Returns:
            Dict with "strategy" (serialized Strategy) and "solution"
            (serialized OptimizationSolution).
        """
        total_load_rt = float(input_data["total_load_rt"])
        t_cw = float(input_data["t_cw"])
        t_chw = float(input_data.get("t_chw", 7.0))
        current_time = input_data.get("current_time", time_module.time())
        predicted_load_rt = float(input_data.get("predicted_load_rt", total_load_rt))
        trigger_type = input_data.get("trigger_type", "SCHEDULED")

        price_per_kwh = float(input_data.get("price_per_kwh", 0.8))
        grid_carbon_intensity = float(input_data.get("grid_carbon_intensity", 0.5))
        carbon_price = float(input_data.get("carbon_price", 0.08))

        # If no optimizer was injected (e.g. in a mock context), return a stub
        if self.optimizer is None:
            return {
                "strategy": {
                    "strategy_id": f"strat_{int(current_time)}",
                    "status": "rejected",
                    "actions": [],
                },
                "solution": {
                    "is_feasible": False,
                    "constraint_violations": ["No optimizer configured"],
                },
            }

        # Run the optimizer
        solution = self.optimizer.optimize(
            total_load_rt=total_load_rt,
            t_cw=t_cw,
            t_chw=t_chw,
            price_per_kwh=price_per_kwh,
            grid_carbon_intensity=grid_carbon_intensity,
            carbon_price=carbon_price,
        )

        # Build the strategy
        strategy = build_strategy(
            solution=solution,
            current_load_rt=total_load_rt,
            predicted_load_rt=predicted_load_rt,
            current_time=current_time,
            trigger_type=trigger_type,
            electricity_price=price_per_kwh,
            grid_carbon_intensity=grid_carbon_intensity,
            carbon_price=carbon_price,
            outdoor_wb_temp=float(input_data.get("outdoor_wb_temp", t_cw)),
        )

        # Generate LLM reasoning if available
        reasoning = ""
        if self.llm is not None:
            try:
                prompt = _build_strategy_reasoning_prompt(
                    strategy, solution, total_load_rt, t_cw, t_chw
                )
                response = await self.llm.ainvoke(prompt)
                reasoning = response.content if hasattr(response, "content") else str(response)
            except Exception:
                self.logger.debug("LLM reasoning generation failed, using defaults", exc_info=True)

        # Serialize both for the caller
        result = {
            "strategy": {**strategy.model_dump(), "llm_reasoning": reasoning},
            "solution": {
                "chiller_loads": solution.chiller_loads,
                "total_power_kw": solution.total_power_kw,
                "total_objective": solution.total_objective,
                "energy_cost": solution.energy_cost,
                "carbon_cost": solution.carbon_cost,
                "wear_cost": solution.wear_cost,
                "is_feasible": solution.is_feasible,
                "constraint_violations": solution.constraint_violations,
            },
        }
        return result
