from fastapi import FastAPI

app = FastAPI(title="Health Service", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "health"}
