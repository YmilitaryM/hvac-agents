import asyncio
import logging

from .config import load_config
from .db import init_db

logger = logging.getLogger(__name__)


async def main():
    cfg = load_config()
    logger.info(f"Starting hvac-edge {cfg.edge_id} in {cfg.mode} mode")

    db = init_db(cfg.db_path)
    logger.info(f"DuckDB initialized at {cfg.db_path}")

    try:
        while True:
            await asyncio.sleep(60)
            logger.debug("Edge heartbeat tick")
    except asyncio.CancelledError:
        logger.info("Shutting down hvac-edge")
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
