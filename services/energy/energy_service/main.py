# services/energy/energy_service/main.py
from fastapi import FastAPI

from .api import baseline, comparison, dashboard, demand, excel_download, mv, power_quality, reports


app = FastAPI(title="Energy Service", version="0.1.0")

app.include_router(dashboard.router, prefix="/api/energy", tags=["Energy Dashboard"])
app.include_router(baseline.router, prefix="/api/energy", tags=["Energy Baseline"])
app.include_router(demand.router, prefix="/api/energy", tags=["Energy Demand"])
app.include_router(reports.router, prefix="/api/energy", tags=["Energy Reports"])
app.include_router(mv.router, prefix="/api/energy", tags=["Energy M&V"])
app.include_router(power_quality.router, prefix="/api/energy", tags=["Power Quality"])
app.include_router(comparison.router, prefix="/api/energy", tags=["Energy Comparison"])
app.include_router(excel_download.router, prefix="/api/energy", tags=["Energy Excel Downloads"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "energy"}
