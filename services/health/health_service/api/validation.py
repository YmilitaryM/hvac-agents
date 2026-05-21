from fastapi import APIRouter

router = APIRouter()


@router.get("/validation")
async def model_validation():
    return {
        "metrics": {"accuracy": 0.82, "precision": 0.78, "recall": 0.85},
        "recent_validations": [
            {"prediction_id": 1, "actual_outcome": "bearing_replace_2026-05-15", "accuracy": 0.9, "retrained": False},
        ],
    }
