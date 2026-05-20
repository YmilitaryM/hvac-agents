import os
import tempfile

import pytest
from datetime import datetime, timezone

from edge.db import init_db
from edge.engine.inspector import Inspector, InspectionPlan


@pytest.fixture
def db():
    path = os.path.join(tempfile.mkdtemp(), "test_inspector.duckdb")
    return init_db(path)


SAMPLE_PLAN = InspectionPlan(
    plan_id="test-plan",
    description="Test plan",
    interval_hours=1,
    items=[
        {
            "id": "chk-1",
            "equipment_type": "chiller",
            "check": "cop_degradation",
            "params": {"threshold_pct": 10},
            "severity": "warning",
        },
        {
            "id": "chk-2",
            "equipment_type": "pump",
            "check": "vibration_rms",
            "params": {"max_rms": 7.0},
            "severity": "critical",
        },
    ],
)


@pytest.mark.asyncio
async def test_inspector_runs_checks(db):
    # Seed some readings with current timestamp so they fall within the
    # NOW() - INTERVAL '1 hour' window used by the inspector queries.
    now = datetime.now(timezone.utc)
    db.execute(
        "INSERT INTO readings (time, point_id, value) VALUES (?, 'CH-1.cop', 4.5)",
        [now],
    )
    db.execute(
        "INSERT INTO readings (time, point_id, value) VALUES (?, 'P-1.vibration_rms', 8.5)",
        [now],
    )

    inspector = Inspector(db, SAMPLE_PLAN)
    result = await inspector.run_inspection()

    assert result["plan_id"] == "test-plan"
    assert result["status"] in ("passed", "failed")
    # P-1 vibration is 8.5 > 7.0 max -> should fail
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_inspector_creates_work_order_on_critical(db):
    now = datetime.now(timezone.utc)
    db.execute(
        "INSERT INTO readings (time, point_id, value) VALUES (?, 'P-1.vibration_rms', 9.0)",
        [now],
    )

    inspector = Inspector(db, SAMPLE_PLAN)
    await inspector.run_inspection()

    # Should create a work order for critical vibration
    orders = db.execute("SELECT COUNT(*) FROM work_orders").fetchone()
    assert orders[0] >= 1
