from datetime import datetime, timezone
from acquisition_service.gap_filler import GapFiller
from acquisition_service.models import EquipmentReading


def make_reading(time, value, quality="good", source="live", point_code="CHWST",
                 equipment_id="e1", plant_id="pl1", point_id="p1"):
    return EquipmentReading(
        time=time, equipment_id=equipment_id, plant_id=plant_id,
        point_id=point_id, point_code=point_code, value=value,
        quality=quality, source=source
    )


def test_gap_filler_short_gap_linear_interpolation():
    t0 = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
    readings = [
        make_reading(t0.replace(minute=0), 20.0),
        make_reading(t0.replace(minute=5), 25.0),
    ]
    gap_start = t0.replace(minute=2)
    gap_end = t0.replace(minute=3)
    filled = GapFiller.fill("p1", readings, gap_start, gap_end)
    assert len(filled) == 1
    assert filled[0].quality == "estimated"


def test_gap_filler_long_gap_fallback_simulation():
    t0 = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
    readings = [make_reading(t0.replace(hour=10), 20.0)]
    gap_start = t0.replace(hour=12)
    gap_end = t0.replace(hour=14)
    filled = GapFiller.fill("p1", readings, gap_start, gap_end)
    assert len(filled) == 1
    assert filled[0].quality == "questionable"
    assert filled[0].source == "simulated"
