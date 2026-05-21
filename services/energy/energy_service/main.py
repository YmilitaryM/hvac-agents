# services/energy/energy_service/main.py
from fastapi import FastAPI

app = FastAPI(title="Energy Service", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "energy"}
