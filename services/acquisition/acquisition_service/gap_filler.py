from datetime import datetime, timezone
from typing import Sequence
from .models import EquipmentReading


class GapFiller:
    @staticmethod
    def fill(point_id: str, readings: Sequence[EquipmentReading],
             gap_start: datetime, gap_end: datetime) -> list[EquipmentReading]:
        gap_seconds = (gap_end - gap_start).total_seconds()
        filled = []

        if gap_seconds < 300:
            before = next((r for r in readings if r.time < gap_start and r.quality == "good"), None)
            after = next((r for r in readings if r.time > gap_end and r.quality == "good"), None)
            if before and after:
                dt = (after.time - before.time).total_seconds()
                dv = after.value - before.value
                mid_time = gap_start + (gap_end - gap_start) / 2
                mid_value = before.value + dv * ((mid_time - before.time).total_seconds() / dt) if dt > 0 else before.value
                filled.append(EquipmentReading(
                    time=mid_time, equipment_id=readings[0].equipment_id,
                    plant_id=readings[0].plant_id, point_id=point_id,
                    point_code=readings[0].point_code, value=mid_value,
                    quality="estimated", source=readings[0].source
                ))

        elif gap_seconds < 3600:
            filled.append(EquipmentReading(
                time=gap_start + (gap_end - gap_start) / 2,
                equipment_id=readings[0].equipment_id,
                plant_id=readings[0].plant_id, point_id=point_id,
                point_code=readings[0].point_code,
                value=readings[-1].value if readings else 0.0,
                quality="estimated", source=readings[0].source
            ))

        else:
            filled.append(EquipmentReading(
                time=gap_start + (gap_end - gap_start) / 2,
                equipment_id=readings[0].equipment_id,
                plant_id=readings[0].plant_id, point_id=point_id,
                point_code=readings[0].point_code,
                value=readings[-1].value if readings else 0.0,
                quality="questionable", source="simulated"
            ))

        return filled
