import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import duckdb

logger = logging.getLogger(__name__)


@dataclass
class InspectionPlan:
    plan_id: str
    description: str
    interval_hours: int
    items: list[dict]


class Inspector:
    """Runs inspection checklists against recent readings and generates work orders."""

    def __init__(self, db: duckdb.DuckDBPyConnection, plan: InspectionPlan):
        self.db = db
        self.plan = plan

    async def run_inspection(self) -> dict:
        now = datetime.now(timezone.utc)
        inspection_id = self.db.execute(
            "SELECT nextval('seq_inspection_id')"
        ).fetchone()[0]

        self.db.execute(
            "INSERT INTO inspections (id, started_at, plan_id, status) "
            "VALUES (?, ?, ?, 'running')",
            [inspection_id, now, self.plan.plan_id],
        )

        failures = []
        for item in self.plan.items:
            check_result = self._run_check(item)
            if not check_result["passed"]:
                failures.append(check_result)
                if item["severity"] == "critical":
                    self._create_work_order(item, check_result)

        status = "failed" if failures else "passed"
        ended_at = datetime.now(timezone.utc)
        self.db.execute(
            "UPDATE inspections SET ended_at = ?, status = ?, result = ? WHERE id = ?",
            [ended_at, status, json.dumps({"failures": len(failures)}), inspection_id],
        )

        return {
            "inspection_id": inspection_id,
            "plan_id": self.plan.plan_id,
            "status": status,
            "failures": failures,
        }

    def _run_check(self, item: dict) -> dict:
        check_type = item["check"]
        params = item.get("params", {})

        if check_type == "cop_degradation":
            return self._check_cop(item, params)
        elif check_type == "vibration_rms":
            return self._check_vibration(item, params)
        elif check_type == "approach_temp":
            return self._check_approach_temp(item, params)
        elif check_type == "stuck_detection":
            return self._check_stuck(item, params)
        else:
            return {
                "item_id": item["id"],
                "passed": True,
                "detail": "unknown check type - skipped",
            }

    def _check_cop(self, item: dict, params: dict) -> dict:
        threshold_pct = params.get("threshold_pct", 10)
        rows = self.db.execute(
            "SELECT AVG(value) FROM readings "
            "WHERE point_id LIKE '%cop%' AND time > NOW() - INTERVAL '1 hour'"
        ).fetchone()
        current_cop = rows[0] if rows[0] else None

        if current_cop is None:
            return {
                "item_id": item["id"],
                "passed": True,
                "detail": "no data",
                "value": None,
            }

        design_cop = 5.5
        degradation = (design_cop - current_cop) / design_cop * 100
        passed = degradation < threshold_pct

        return {
            "item_id": item["id"],
            "passed": passed,
            "detail": f"COP={current_cop:.2f}, degradation={degradation:.1f}%",
            "value": current_cop,
        }

    def _check_vibration(self, item: dict, params: dict) -> dict:
        max_rms = params.get("max_rms", 7.0)
        rows = self.db.execute(
            "SELECT AVG(value) FROM readings "
            "WHERE point_id LIKE '%vibration%' AND time > NOW() - INTERVAL '1 hour'"
        ).fetchone()
        current = rows[0] if rows[0] else None

        if current is None:
            return {
                "item_id": item["id"],
                "passed": True,
                "detail": "no data",
                "value": None,
            }

        passed = current <= max_rms
        return {
            "item_id": item["id"],
            "passed": passed,
            "detail": f"Vibration={current:.2f} mm/s RMS (limit={max_rms})",
            "value": current,
        }

    def _check_approach_temp(self, item: dict, params: dict) -> dict:
        max_delta = params.get("max_delta_k", 5.0)
        rows = self.db.execute(
            "SELECT AVG(value) FROM readings "
            "WHERE point_id LIKE '%approach%' AND time > NOW() - INTERVAL '1 hour'"
        ).fetchone()
        current = rows[0] if rows[0] else None

        if current is None:
            return {
                "item_id": item["id"],
                "passed": True,
                "detail": "no data",
                "value": None,
            }

        passed = current <= max_delta
        return {
            "item_id": item["id"],
            "passed": passed,
            "detail": f"Approach ΔT={current:.1f}K (limit={max_delta}K)",
            "value": current,
        }

    def _check_stuck(self, item: dict, params: dict) -> dict:
        min_change = params.get("min_position_change", 0.02)
        rows = self.db.execute(
            "SELECT MIN(value), MAX(value) FROM readings "
            "WHERE point_id LIKE '%valve%position%' "
            "AND time > NOW() - INTERVAL '30 minutes'"
        ).fetchone()
        if rows[0] is None:
            return {
                "item_id": item["id"],
                "passed": True,
                "detail": "no data",
                "value": None,
            }

        range_val = rows[1] - rows[0]
        passed = range_val > min_change
        return {
            "item_id": item["id"],
            "passed": passed,
            "detail": f"Position range={range_val:.3f} (min={min_change})",
            "value": range_val,
        }

    def _create_work_order(self, item: dict, check_result: dict):
        wo_id = self.db.execute("SELECT nextval('seq_work_order_id')").fetchone()[0]
        now = datetime.now(timezone.utc)
        self.db.execute(
            "INSERT INTO work_orders (id, created_at, equipment_id, severity, "
            "title, description, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'open')",
            [
                wo_id,
                now,
                item.get("equipment_type", "unknown"),
                item["severity"],
                f"Inspection failed: {item['id']}",
                check_result.get("detail", ""),
            ],
        )
        logger.info(f"Auto-created work order {wo_id} for {item['id']}")
