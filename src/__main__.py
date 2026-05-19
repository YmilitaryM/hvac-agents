"""Entry point for the HVAC Chiller Plant Multi-Agent System.

Usage:
  python -m src                    Start API server
  python -m src --run-once        Run a single pipeline cycle and exit
  python -m src --host 0.0.0.0 --port 8080 --debug
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("hvac")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HVAC Chiller Plant Multi-Agent System",
    )
    parser.add_argument("--host", default="127.0.0.1", help="API server host")
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev)")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run a single pipeline cycle and exit (headless mode)",
    )
    parser.add_argument(
        "--snapshot-file",
        default=None,
        help="JSON file with plant snapshot for --run-once mode",
    )
    return parser.parse_args(argv)


def bootstrap(*, debug: bool = False):
    """Create all system components: config, agents, graph, event bus, and API."""
    from src.config import Config, set_config
    from src.logging_config import setup_logging

    setup_logging(debug=debug)

    cfg = Config.from_env()
    cfg.debug = debug
    set_config(cfg)

    logger.info("Bootstrapping HVAC multi-agent system (debug=%s)", debug)

    # Create LLM clients
    from src.agents.base import create_llm_client

    deep_llm = create_llm_client(deep=True)
    quick_llm = create_llm_client(deep=False)

    # Create agents
    from src.agents.monitor import MonitorAgent
    from src.agents.predict import PredictAgent
    from src.agents.strategy import StrategyAgent
    from src.agents.advocates.reliability import ReliabilityAdvocate
    from src.agents.advocates.efficiency import EfficiencyAdvocate
    from src.agents.advocates.compliance import ComplianceAdvocate
    from src.agents.coordinator import CoordinatorAgent
    from src.agents.safety import SafetyAgent
    from src.agents.parameter import ParameterAgent

    from src.optimization.solver import ChillerPlantOptimizer

    # Default optimizer with 2x500RT chillers (can be overridden via config)
    from src.simulation.chiller import CentrifugalChiller

    default_plant = {
        "ch1": CentrifugalChiller(name="ch1", capacity_rt=500, design_cop=6.0, min_plr=0.2),
        "ch2": CentrifugalChiller(name="ch2", capacity_rt=500, design_cop=6.0, min_plr=0.2),
    }
    optimizer = ChillerPlantOptimizer(default_plant)

    agents = {
        "monitor": MonitorAgent(llm=quick_llm),
        "predict": PredictAgent(llm=quick_llm),
        "strategy": StrategyAgent(llm=deep_llm, optimizer=optimizer),
        "reliability": ReliabilityAdvocate(llm=quick_llm),
        "efficiency": EfficiencyAdvocate(llm=quick_llm),
        "compliance": ComplianceAdvocate(llm=quick_llm),
        "coordinator": CoordinatorAgent(llm=deep_llm),
        "safety": SafetyAgent(llm=quick_llm),
        "parameter": ParameterAgent(llm=quick_llm),
    }

    # Build the graph
    from src.graph.setup import HVACGraph

    graph = HVACGraph(
        monitor_agent=agents["monitor"],
        predict_agent=agents["predict"],
        strategy_agent=agents["strategy"],
        reliability_advocate=agents["reliability"],
        efficiency_advocate=agents["efficiency"],
        compliance_advocate=agents["compliance"],
        coordinator_agent=agents["coordinator"],
        safety_agent=agents["safety"],
        parameter_agent=agents["parameter"],
        debug=debug,
    )
    graph.build()

    # Create API
    from src.api.main import create_app

    app = create_app(debug=debug)

    return app, graph, agents, cfg


async def run_headless(config_file: str | None = None, *, debug: bool = False) -> None:
    """Run a single pipeline cycle and print results."""
    logger.info("Running headless pipeline cycle")

    plant_snapshot: dict = {}
    if config_file:
        with open(config_file) as f:
            plant_snapshot = json.load(f)
    else:
        plant_snapshot = {
            "timestamp": time.time(),
            "total_cooling_load_rt": 600.0,
            "total_power_kw": 420.0,
            "system_cop": 5.0,
            "outdoor_wb_temp": 26.0,
            "outdoor_db_temp": 32.0,
            "chillers": {
                "ch1": {"status": "RUNNING", "is_running": True, "plr": 0.6, "load_rt": 300.0},
                "ch2": {"status": "RUNNING", "is_running": True, "plr": 0.6, "load_rt": 300.0},
            },
            "cooling_towers": {"ct1": {"status": "RUNNING"}},
            "chw_pumps": {"pump_chw1": {"status": "RUNNING", "speed_hz": 50.0}},
            "cw_pumps": {"pump_cw1": {"status": "RUNNING", "speed_hz": 50.0}},
        }

    initial_state = {
        "messages": [],
        "current_time": time.time(),
        "trigger_type": "scheduled",
        "plant_snapshot": plant_snapshot,
        "weather_data": {
            "outdoor_temp": plant_snapshot.get("outdoor_db_temp", 32.0),
            "outdoor_humidity": 60.0,
        },
    }

    app, graph, _agents, _cfg = bootstrap(debug=debug)

    result = await graph.run(initial_state)

    strategy = result.get("current_strategy", {})
    safety = result.get("safety_result", {})

    print("\n=== Pipeline Result ===")
    print(f"Execution status: {result.get('execution_status', 'unknown')}")
    print(f"Strategy ID: {strategy.get('strategy_id', 'N/A')}")
    print(f"Strategy status: {strategy.get('status', 'N/A')}")
    print(f"Safety passed: {safety.get('passed', 'N/A')}")
    print(f"Alerts: {len(result.get('alerts', []))}")
    print(f"Advocate opinions: {len(result.get('advocate_opinions', []))}")

    if safety.get("warnings"):
        print(f"Warnings: {safety['warnings']}")

    return result


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.run_once:
        asyncio.run(run_headless(config_file=args.snapshot_file, debug=args.debug))
        return

    app, _graph, _agents, _cfg = bootstrap(debug=args.debug)

    import uvicorn

    logger.info(
        "Starting API server on %s:%d (debug=%s)",
        args.host,
        args.port,
        args.debug,
    )
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()
