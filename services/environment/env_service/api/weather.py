import csv
import io
import time

from fastapi import APIRouter, Depends, UploadFile, File, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WeatherRecordModel

router = APIRouter()


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.session_factory() as session:
        yield session


@router.post("/import/tmy")
async def import_tmy_csv(file: UploadFile = File(...), db=Depends(get_db)):
    """Import TMY CSV: columns: timestamp,db_temp,wb_temp,rh,solar,wind_speed,wind_dir,cloud"""
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode()))
    count = 0
    batch = []
    for row in reader:
        batch.append(WeatherRecordModel(
            timestamp=float(row["timestamp"]),
            outdoor_db_temp=float(row.get("db_temp", 25)),
            outdoor_wb_temp=float(row.get("wb_temp", 20)),
            relative_humidity=float(row.get("rh", 60)),
            solar_radiation_wm2=float(row.get("solar", 0)),
            wind_speed_ms=float(row.get("wind_speed", 0)),
            wind_direction=float(row.get("wind_dir", 0)),
            cloud_cover=float(row.get("cloud", 0)),
        ))
        if len(batch) >= 1000:
            db.add_all(batch)
            await db.flush()
            count += len(batch)
            batch = []
    if batch:
        db.add_all(batch)
        await db.flush()
        count += len(batch)
    await db.commit()
    return {"status": "ok", "records_imported": count}


@router.get("/weather")
async def get_weather(from_ts: float, to_ts: float, db=Depends(get_db)):
    """Query weather records in time range."""
    result = await db.execute(
        select(WeatherRecordModel)
        .where(WeatherRecordModel.timestamp >= from_ts)
        .where(WeatherRecordModel.timestamp <= to_ts)
        .order_by(WeatherRecordModel.timestamp.asc())
        .limit(10000)
    )
    records = result.scalars().all()
    return {
        "records": [
            {
                "timestamp": r.timestamp,
                "db_temp": r.outdoor_db_temp,
                "wb_temp": r.outdoor_wb_temp,
                "rh": r.relative_humidity,
            }
            for r in records
        ]
    }


@router.get("/weather/now")
async def get_current_weather(ts: float | None = None, db=Depends(get_db)):
    """Get weather closest to given timestamp (or now)."""
    ts = ts or time.time()
    result = await db.execute(
        select(WeatherRecordModel)
        .order_by(text(f"abs(timestamp - {ts})"))
        .limit(1)
    )
    r = result.scalar_one_or_none()
    if not r:
        return {"weather": None}
    return {
        "weather": {
            "timestamp": r.timestamp,
            "db_temp": r.outdoor_db_temp,
            "wb_temp": r.outdoor_wb_temp,
            "rh": r.relative_humidity,
        }
    }
