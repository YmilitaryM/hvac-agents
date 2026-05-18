"""Strategy management API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# In-memory strategy store (would be DB in production)
_strategies: Dict[str, Dict[str, Any]] = {}
_strategy_history: List[Dict[str, Any]] = []


@router.get("/")
async def list_strategies(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, le=500),
):
    """List strategies, optionally filtered by status."""
    if status:
        filtered = [s for s in _strategies.values() if s.get("status") == status]
    else:
        filtered = list(_strategies.values())

    filtered = filtered[-limit:]
    return {"strategies": filtered, "count": len(filtered)}


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    """Get a specific strategy by ID."""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return {"strategy": _strategies[strategy_id]}


@router.post("/")
async def create_strategy(strategy: Dict[str, Any]):
    """Create a new strategy."""
    strategy_id = strategy.get("strategy_id", "")
    if not strategy_id:
        raise HTTPException(status_code=400, detail="strategy_id is required")

    if "status" not in strategy:
        strategy["status"] = "draft"

    _strategies[strategy_id] = strategy
    _strategy_history.append({
        "strategy_id": strategy_id,
        "action": "created",
        "timestamp": strategy.get("trigger_time", 0),
    })

    return {"status": "ok", "strategy_id": strategy_id}


@router.put("/{strategy_id}/status")
async def update_strategy_status(strategy_id: str, status_update: Dict[str, Any]):
    """Update a strategy's status (approve, reject, etc.)."""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

    new_status = status_update.get("status", "")
    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")

    _strategies[strategy_id]["status"] = new_status
    _strategy_history.append({
        "strategy_id": strategy_id,
        "action": f"status_changed_to_{new_status}",
        "timestamp": status_update.get("timestamp", 0),
    })

    return {"status": "ok", "strategy_id": strategy_id, "new_status": new_status}


@router.get("/history/recent")
async def get_strategy_history(limit: int = Query(default=20, le=200)):
    """Get recent strategy history."""
    return {"history": _strategy_history[-limit:], "count": len(_strategy_history[-limit:])}


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """Delete a strategy."""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    del _strategies[strategy_id]
    return {"status": "ok", "deleted": strategy_id}
