"""Minute-level emission monitor — reads plant data, writes emission records + ledger."""
import time
from typing import Optional

from ...carbon_models import CarbonEmissionModel
from ...carbon_repositories import CarbonEmissionRepository, CarbonLedgerRepository
from .factor_registry import FactorRegistry


class EmissionMonitor:
    """Monitors plant power data and records minute-level emissions."""

    def __init__(
        self,
        emission_repo: CarbonEmissionRepository,
        ledger_repo: CarbonLedgerRepository,
        factor_registry: FactorRegistry,
    ):
        self.emission_repo = emission_repo
        self.ledger_repo = ledger_repo
        self.registry = factor_registry
        self._accumulators: dict[str, float] = {}
        self._last_hour_write: dict[str, int] = {}

    async def record_minute(
        self,
        plant_id: str,
        power_kw: float,
        region: str = "east",
        cooling_gj: float = 0.0,
        chiller_id: Optional[str] = None,
    ) -> CarbonEmissionModel:
        now = time.time()
        hour_bucket = int(now // 3600)
        month = int(time.strftime("%m", time.localtime(now)))
        hour = int(time.strftime("%H", time.localtime(now)))
        factor = self.registry.get_factor(region, hour=hour, month=month)
        tco2 = power_kw * factor / 1000.0 * (1.0 / 60.0)

        record = await self.emission_repo.insert({
            "plant_id": plant_id,
            "timestamp": now,
            "power_kw": power_kw,
            "emission_factor": factor,
            "tco2": round(tco2, 6),
            "cooling_gj": cooling_gj,
            "period_tag": time.strftime("%Y", time.localtime(now)),
            "chiller_id": chiller_id,
        })

        key = plant_id
        self._accumulators[key] = self._accumulators.get(key, 0.0) + tco2

        last_write = self._last_hour_write.get(key, -1)
        if hour_bucket > last_write and self._accumulators[key] > 0:
            await self._write_hourly_ledger(plant_id, region, hour_bucket)
            self._last_hour_write[key] = hour_bucket

        return record

    async def _write_hourly_ledger(self, plant_id: str, region: str, hour_bucket: int):
        accumulated = self._accumulators.get(plant_id, 0.0)
        if accumulated <= 0:
            return
        period = time.strftime("%Y", time.localtime(time.time()))
        current_balance = await self.ledger_repo.get_balance(plant_id, "CEA", period)
        new_balance = current_balance - accumulated
        await self.ledger_repo.create_entry({
            "plant_id": plant_id, "period": period,
            "entry_type": "emission", "direction": "debit",
            "allowance_type": "CEA",
            "qty_tco2": round(accumulated, 4),
            "unit_price": self.registry.get_factor(region),
            "balance_after": round(new_balance, 4),
        })
        self._accumulators[plant_id] = 0.0
        await self.ledger_repo.commit()
