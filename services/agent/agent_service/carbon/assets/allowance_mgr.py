"""Allowance lifecycle manager — allocation, transfer, balance queries."""
from typing import List, Optional

from ...carbon_repositories import CarbonLedgerRepository


class AllowanceManager:
    def __init__(self, ledger_repo: CarbonLedgerRepository):
        self.ledger = ledger_repo

    async def allocate(
        self, plant_id: str, period: str, qty: float,
        allowance_type: str = "CEA", source: str = "free_allocation",
    ) -> dict:
        """Receive free allocation (年初政府发放)."""
        balance = await self.ledger.get_balance(plant_id, allowance_type, period)
        new_balance = balance + qty
        await self.ledger.create_entry({
            "plant_id": plant_id, "period": period,
            "entry_type": "allocation", "direction": "credit",
            "allowance_type": allowance_type,
            "qty_tco2": qty, "unit_price": 0.0,
            "balance_after": round(new_balance, 4),
            "note": f"Free allocation from {source}",
        })
        await self.ledger.commit()
        return {"plant_id": plant_id, "type": allowance_type, "allocated": qty, "balance": new_balance}

    async def transfer(
        self, from_plant: str, to_plant: str, qty: float,
        allowance_type: str, period: str,
    ) -> dict:
        """Internal transfer between plants (站间调拨)."""
        from_balance = await self.ledger.get_balance(from_plant, allowance_type, period)
        if from_balance < qty:
            raise ValueError(f"Insufficient balance: {from_balance} < {qty}")

        new_from = from_balance - qty
        await self.ledger.create_entry({
            "plant_id": from_plant, "period": period,
            "entry_type": "transfer_out", "direction": "debit",
            "allowance_type": allowance_type,
            "qty_tco2": qty, "unit_price": 0.0,
            "balance_after": round(new_from, 4),
            "note": f"Transfer to {to_plant}",
        })

        to_balance = await self.ledger.get_balance(to_plant, allowance_type, period)
        new_to = to_balance + qty
        await self.ledger.create_entry({
            "plant_id": to_plant, "period": period,
            "entry_type": "transfer_in", "direction": "credit",
            "allowance_type": allowance_type,
            "qty_tco2": qty, "unit_price": 0.0,
            "balance_after": round(new_to, 4),
            "note": f"Transfer from {from_plant}",
        })
        await self.ledger.commit()
        return {"from": from_plant, "to": to_plant, "qty": qty, "status": "completed"}

    async def get_holdings(self, plant_id: str, period: str) -> dict:
        cea = await self.ledger.get_balance(plant_id, "CEA", period)
        ccer = await self.ledger.get_balance(plant_id, "CCER", period)
        return {
            "plant_id": plant_id, "period": period,
            "CEA": cea, "CCER": ccer,
            "total": cea + ccer,
        }
