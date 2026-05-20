import asyncio
import logging

from .config import load_config
from .db import init_db
from .engine.collector import Collector
from .engine.controller import SafetyGate, PIDController, Interlock
from .sync.agent import SyncAgent

logger = logging.getLogger(__name__)


async def main():
    cfg = load_config()
    logger.info(f"Starting hvac-edge {cfg.edge_id} in {cfg.mode} mode")

    db = init_db(cfg.db_path)
    logger.info(f"DuckDB initialized at {cfg.db_path}")

    # Build point configs from acquisition config
    point_configs = {}
    adapters = {}
    for proto_cfg in cfg.acquisition.protocols:
        proto_type = proto_cfg["type"]
        for pt in proto_cfg.get("points", []):
            point_configs[pt["point_id"]] = {
                "protocol": proto_type,
                "binding": pt.get("binding", {}),
                "poll_interval_ms": cfg.acquisition.poll_interval_ms,
            }

    # Init engines
    collector = Collector(db, point_configs, adapters)
    safety_gate = SafetyGate(limits={
        "CH-1.cop": (2.0, 10.0),
        "CH-1.evap_delta_t": (2.0, 12.0),
        "CH-1.cond_delta_t": (2.0, 15.0),
    })
    pid = PIDController(kp=2.0, ki=0.05, kd=0.0, setpoint=7.0, output_min=0, output_max=100)
    interlock = Interlock(rules=[
        {"if": "CH-1.status == 'off'", "then": "P-1.cmd = 0"},
        {"if": "CH-1.status == 'off'", "then": "CT-1.fan_cmd = 0"},
    ])
    sync_agent = SyncAgent(db, cfg)

    logger.info("Engines initialized, starting loops")

    # Start engines
    await collector.start(interval_ms=cfg.acquisition.poll_interval_ms)
    await sync_agent.start()

    try:
        while True:
            await asyncio.sleep(60)

            # Run inspection logic on latest readings
            result = db.execute(
                "SELECT point_id, AVG(value) FROM readings "
                "WHERE time > NOW() - INTERVAL '60 seconds' GROUP BY point_id"
            ).fetchall()
            latest = {r[0]: r[1] for r in result}

            # Check interlock conditions
            actions = interlock.evaluate(latest)
            for action in actions:
                logger.info(f"Interlock action: {action}")

            # Safety gate check on key params
            for param, value in latest.items():
                if not safety_gate.check(param, value):
                    await sync_agent.send_alert("critical", f"Safety gate violation: {param}={value}")

    except asyncio.CancelledError:
        logger.info("Shutting down hvac-edge")
    finally:
        await collector.stop()
        await sync_agent.stop()
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(main())
