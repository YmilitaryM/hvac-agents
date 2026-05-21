from fastapi import FastAPI

from .api import dashboard, equipment_detail, rul, diagnosis, fmea, vibration, oil, validation


app = FastAPI(title="Health Service", version="0.1.0")

app.include_router(dashboard.router, prefix="/api/health", tags=["Health Dashboard"])
app.include_router(equipment_detail.router, prefix="/api/health", tags=["Equipment Health"])
app.include_router(rul.router, prefix="/api/health", tags=["RUL"])
app.include_router(diagnosis.router, prefix="/api/health", tags=["Diagnosis"])
app.include_router(fmea.router, prefix="/api/health", tags=["FMEA"])
app.include_router(vibration.router, prefix="/api/health", tags=["Vibration"])
app.include_router(oil.router, prefix="/api/health", tags=["Oil Analysis"])
app.include_router(validation.router, prefix="/api/health", tags=["Validation"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "health"}
