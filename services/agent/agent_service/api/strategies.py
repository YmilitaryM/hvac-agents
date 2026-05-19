"""Strategy management API endpoints.

Supports dual-mode: PostgreSQL via repositories (when configured),
or in-memory storage (default/dev).
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from common.auth import require_role, Role

from ..repositories import StrategyRepository, StrategyHistoryRepository

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for dev/testing fallback
_strategies: Dict[str, Dict[str, Any]] = {}
_strategy_history: List[Dict[str, Any]] = []


def _has_db(request: Request) -> bool:
    """Check if a database session factory is available."""
    return getattr(request.app.state, "session_factory", None) is not None


@router.get("/")
async def list_strategies(
    request: Request,
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, le=500),
):
    """List strategies, optionally filtered by status."""
    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = StrategyRepository(session)
            results = await repo.list_all(status=status, limit=limit)
            return {
                "strategies": [
                    {
                        "strategy_id": s.strategy_id,
                        "trigger_type": s.trigger_type,
                        "status": s.status,
                        "current_load_rt": s.current_load_rt,
                        "expected_cop_improvement": s.expected_cop_improvement,
                        "actions": s.actions or [],
                    }
                    for s in results
                ],
                "count": len(results),
            }

    if status:
        filtered = [s for s in _strategies.values() if s.get("status") == status]
    else:
        filtered = list(_strategies.values())
    filtered = filtered[-limit:]
    return {"strategies": filtered, "count": len(filtered)}


@router.get("/history/recent")
async def get_strategy_history(
    request: Request,
    limit: int = Query(default=20, le=200),
):
    """Get recent strategy history."""
    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = StrategyHistoryRepository(session)
            results = await repo.get_recent(limit=limit)
            return {
                "history": [
                    {
                        "strategy_id": h.strategy_id,
                        "action": h.action,
                        "timestamp": h.timestamp,
                    }
                    for h in results
                ],
                "count": len(results),
            }

    return {"history": _strategy_history[-limit:], "count": len(_strategy_history[-limit:])}


@router.get("/{strategy_id}")
async def get_strategy(request: Request, strategy_id: str):
    """Get a specific strategy by ID."""
    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = StrategyRepository(session)
            s = await repo.get_by_id(strategy_id)
            if s is None:
                raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
            return {
                "strategy": {
                    "strategy_id": s.strategy_id,
                    "trigger_type": s.trigger_type,
                    "trigger_time": s.trigger_time,
                    "current_load_rt": s.current_load_rt,
                    "predicted_load_rt": s.predicted_load_rt,
                    "actions": s.actions or [],
                    "transition_plan": s.transition_plan,
                    "expected_cop_improvement": s.expected_cop_improvement,
                    "expected_energy_saving_kwh_per_h": s.expected_energy_saving_kwh_per_h,
                    "status": s.status,
                }
            }

    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return {"strategy": _strategies[strategy_id]}


@router.post("/")
async def create_strategy(
    request: Request,
    strategy: Dict[str, Any],
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Create a new strategy."""
    strategy_id = strategy.get("strategy_id", "")
    if not strategy_id:
        raise HTTPException(status_code=400, detail="strategy_id is required")
    if "status" not in strategy:
        strategy["status"] = "draft"

    if _has_db(request):
        async with request.app.state.session_factory() as session:
            strat_repo = StrategyRepository(session)
            hist_repo = StrategyHistoryRepository(session)
            await strat_repo.create({
                "strategy_id": strategy_id,
                "trigger_type": strategy.get("trigger_type", "scheduled"),
                "trigger_time": strategy.get("trigger_time", 0),
                "current_load_rt": strategy.get("current_load_rt", 0),
                "predicted_load_rt": strategy.get("predicted_load_rt", 0),
                "actions": strategy.get("actions", []),
                "transition_plan": strategy.get("transition_plan"),
                "expected_cop_improvement": strategy.get("expected_cop_improvement", 0),
                "expected_energy_saving_kwh_per_h": strategy.get("expected_energy_saving_kwh_per_h", 0),
                "status": strategy["status"],
                "raw_strategy": strategy,
            })
            await hist_repo.create({
                "strategy_id": strategy_id,
                "action": "created",
                "timestamp": strategy.get("trigger_time", 0),
            })
            return {"status": "ok", "strategy_id": strategy_id}

    _strategies[strategy_id] = strategy
    _strategy_history.append({
        "strategy_id": strategy_id,
        "action": "created",
        "timestamp": strategy.get("trigger_time", 0),
    })
    return {"status": "ok", "strategy_id": strategy_id}


@router.put("/{strategy_id}/status")
async def update_strategy_status(
    request: Request,
    strategy_id: str,
    status_update: Dict[str, Any],
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Update a strategy's status."""
    new_status = status_update.get("status", "")
    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")

    if _has_db(request):
        async with request.app.state.session_factory() as session:
            strat_repo = StrategyRepository(session)
            hist_repo = StrategyHistoryRepository(session)
            ok = await strat_repo.update_status(strategy_id, new_status)
            if not ok:
                raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
            await hist_repo.create({
                "strategy_id": strategy_id,
                "action": f"status_changed_to_{new_status}",
                "timestamp": status_update.get("timestamp", 0),
            })
            return {"status": "ok", "strategy_id": strategy_id, "new_status": new_status}

    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    _strategies[strategy_id]["status"] = new_status
    _strategy_history.append({
        "strategy_id": strategy_id,
        "action": f"status_changed_to_{new_status}",
        "timestamp": status_update.get("timestamp", 0),
    })
    return {"status": "ok", "strategy_id": strategy_id, "new_status": new_status}


@router.delete("/{strategy_id}")
async def delete_strategy(
    request: Request,
    strategy_id: str,
    user: dict = Depends(require_role(Role.ENGINEER, Role.ADMIN)),
):
    """Delete a strategy."""
    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = StrategyRepository(session)
            ok = await repo.delete(strategy_id)
            if not ok:
                raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
            return {"status": "ok", "deleted": strategy_id}

    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    del _strategies[strategy_id]
    return {"status": "ok", "deleted": strategy_id}
