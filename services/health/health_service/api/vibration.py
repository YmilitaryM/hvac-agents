from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/vibration")
async def vibration_data(equipment_id: int = Query(...)):
    return {
        "equipment_id": equipment_id,
        "latest": {
            "timestamp": "2026-05-21T10:00:00", "sample_rate": 25600,
            "peak_frequencies": [{"hz": 50.0, "label": "1x 工频", "amplitude": 3.2}, {"hz": 100.0, "label": "2x 不对中", "amplitude": 1.8}],
            "bearing_fault_freqs": {"BPFI": 0.8, "BPFO": 0.5, "FTF": 0.3, "BSF": 0.6},
            "crest_factor": 3.5, "vibration_zone": "B",
        },
        "waterfall_data": [[50, 3.2, 1.8, 0.8], [52, 3.0, 1.6, 0.7]],
    }
