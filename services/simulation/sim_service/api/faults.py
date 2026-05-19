"""Fault injection REST API — inject, list, remove faults and disturbances, run diagnostics."""

import time
from fastapi import APIRouter, HTTPException
from ..faults.fault_models import (
    EquipmentFault, FaultType, ExternalDisturbance, DisturbanceType,
)
from ..faults.injector import FaultInjector

router = APIRouter()

# Per-process singleton injector (module-level instance)
_injector = FaultInjector()


# ------------------------------------------------------------------ #
#  List
# ------------------------------------------------------------------ #

@router.get("/")
async def list_faults():
    """List all active faults and disturbances."""
    return {
        "faults": [
            {
                "fault_id": f.fault_id,
                "device_id": f.device_id,
                "fault_type": f.fault_type.value,
                "severity": f.severity,
                "onset_time": f.onset_time,
                "duration": f.duration,
            }
            for f in _injector.list_active()
        ],
        "disturbances": [
            {
                "dist_id": d.dist_id,
                "disturbance_type": d.disturbance_type.value,
                "magnitude": d.magnitude,
                "onset_time": d.onset_time,
                "duration": d.duration,
            }
            for d in _injector.list_active_disturbances()
        ],
    }


# ------------------------------------------------------------------ #
#  Equipment faults
# ------------------------------------------------------------------ #

@router.post("/inject")
async def inject_fault(fault_data: dict):
    """Inject an equipment fault.

    Body:
        {
            "device_id": "CH-1",
            "fault_type": "fouling",
            "severity": 0.3,
            "onset_time": 0,
            "duration": null
        }

    Valid fault_type values:
        surge, cavitation, valve_sticking, sensor_failure,
        fouling, rust, drift, refrigerant_leak
    """
    try:
        fault_type = FaultType(fault_data["fault_type"])
        severity = float(fault_data.get("severity", 0.5))
        if not 0.0 <= severity <= 1.0:
            raise HTTPException(400, "severity must be between 0.0 and 1.0")
        fault = EquipmentFault(
            device_id=fault_data["device_id"],
            fault_type=fault_type,
            severity=severity,
            onset_time=float(fault_data.get("onset_time", 0)),
            duration=float(fault_data["duration"]) if fault_data.get("duration") is not None else None,
        )
        fault_id = _injector.inject(fault)
        return {"status": "injected", "fault_id": fault_id}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/remove/{fault_id}")
async def remove_fault(fault_id: str):
    """Remove an equipment fault by its fault_id."""
    if _injector.remove(fault_id):
        return {"status": "removed", "fault_id": fault_id}
    raise HTTPException(status_code=404, detail="Fault not found")


# ------------------------------------------------------------------ #
#  External disturbances
# ------------------------------------------------------------------ #

@router.post("/inject/external")
async def inject_external(disturbance_data: dict):
    """Inject an external disturbance.

    Body:
        {
            "disturbance_type": "load_spike",
            "magnitude": 0.5,
            "onset_time": 0,
            "duration": null
        }

    Valid disturbance_type values:
        extreme_weather, grid_fluctuation, load_spike, comm_loss
    """
    try:
        dist_type = DisturbanceType(disturbance_data["disturbance_type"])
        magnitude = float(disturbance_data.get("magnitude", 0.5))
        if not 0.0 <= magnitude <= 1.0:
            raise HTTPException(400, "magnitude must be between 0.0 and 1.0")
        dist = ExternalDisturbance(
            disturbance_type=dist_type,
            magnitude=magnitude,
            onset_time=float(disturbance_data.get("onset_time", 0)),
            duration=float(disturbance_data["duration"])
            if disturbance_data.get("duration") is not None
            else None,
        )
        dist_id = _injector.inject_disturbance(dist)
        return {"status": "injected", "dist_id": dist_id}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/remove/external/{dist_id}")
async def remove_external(dist_id: str):
    """Remove an external disturbance by its dist_id."""
    if _injector.remove_disturbance(dist_id):
        return {"status": "removed", "dist_id": dist_id}
    raise HTTPException(status_code=404, detail="Disturbance not found")


# ------------------------------------------------------------------ #
#  Diagnostics
# ------------------------------------------------------------------ #

@router.get("/diagnostics")
async def get_diagnostics():
    """Run automatic diagnostics on all equipment.

    Returns a summary of active faults and detected issues.  This is a
    lightweight endpoint that reports the current fault state — for
    detailed per-equipment time-series diagnostics, use the trend data
    from the simulation API.
    """
    now = time.time()
    faults_summary = []
    for fault in _injector.list_active():
        active = _injector.is_active(fault.fault_id, now)
        elapsed = now - fault.injected_at if hasattr(fault, "injected_at") else None
        faults_summary.append(
            {
                "fault_id": fault.fault_id,
                "device_id": fault.device_id,
                "fault_type": fault.fault_type.value,
                "severity": fault.severity,
                "active": active,
                "elapsed_seconds": round(elapsed, 1) if elapsed is not None else None,
            }
        )

    disturbances_summary = []
    for dist in _injector.list_active_disturbances():
        active = _injector._is_fault_active(dist.onset_time, dist.duration, now)
        disturbances_summary.append(
            {
                "dist_id": dist.dist_id,
                "disturbance_type": dist.disturbance_type.value,
                "magnitude": dist.magnitude,
                "active": active,
            }
        )

    return {
        "faults": faults_summary,
        "disturbances": disturbances_summary,
        "total_active_faults": sum(1 for f in faults_summary if f["active"]),
        "total_active_disturbances": sum(1 for d in disturbances_summary if d["active"]),
    }
