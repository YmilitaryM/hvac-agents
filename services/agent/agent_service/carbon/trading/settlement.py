"""T+0 settlement engine — creates trades and updates ledger on match."""
import uuid
import time
from typing import List

from .matching_engine import Match
from ...carbon_repositories import (
    CarbonTradeRepository, CarbonLedgerRepository, CarbonOrderRepository,
)


class SettlementEngine:
    """Handles T+0 settlement: create trades, update ledger, update orders."""

    FEE_RATE = 0.001  # 0.1% transaction fee

    def __init__(
        self,
        trade_repo: CarbonTradeRepository,
        ledger_repo: CarbonLedgerRepository,
        order_repo: CarbonOrderRepository,
    ):
        self.trade_repo = trade_repo
        self.ledger_repo = ledger_repo
        self.order_repo = order_repo

    async def settle(self, matches: List[Match]) -> List[dict]:
        trades = []
        period = time.strftime("%Y", time.localtime(time.time()))

        for m in matches:
            total_value = m.qty * m.price
            fee = round(total_value * self.FEE_RATE, 2)
            trade = await self.trade_repo.create({
                "id": uuid.uuid4().hex[:16],
                "buy_order_id": m.buy_order.id,
                "sell_order_id": m.sell_order.id,
                "buy_plant_id": m.buy_order.plant_id,
                "sell_plant_id": m.sell_order.plant_id,
                "allowance_type": m.buy_order.allowance_type,
                "qty_tco2": m.qty,
                "price": m.price,
                "total_value": total_value,
                "fee": fee,
            })

            # Buyer: credit of allowance
            buyer_bal = await self.ledger_repo.get_balance(
                m.buy_order.plant_id, m.buy_order.allowance_type, period
            )
            await self.ledger_repo.create_entry({
                "plant_id": m.buy_order.plant_id, "period": period,
                "entry_type": "market_buy", "direction": "credit",
                "allowance_type": m.buy_order.allowance_type,
                "qty_tco2": m.qty, "unit_price": m.price,
                "balance_after": round(buyer_bal + m.qty, 4),
                "trade_id": trade.id,
            })

            # Seller: debit of allowance
            seller_bal = await self.ledger_repo.get_balance(
                m.sell_order.plant_id, m.sell_order.allowance_type, period
            )
            await self.ledger_repo.create_entry({
                "plant_id": m.sell_order.plant_id, "period": period,
                "entry_type": "market_sell", "direction": "debit",
                "allowance_type": m.sell_order.allowance_type,
                "qty_tco2": m.qty, "unit_price": m.price,
                "balance_after": round(seller_bal - m.qty, 4),
                "trade_id": trade.id,
            })

            # Update orders in DB
            await self.order_repo.update_remaining(
                m.buy_order.id, m.buy_order.remaining, m.buy_order.status
            )
            await self.order_repo.update_remaining(
                m.sell_order.id, m.sell_order.remaining, m.sell_order.status
            )

            trades.append({
                "trade_id": trade.id,
                "buy_plant": m.buy_order.plant_id,
                "sell_plant": m.sell_order.plant_id,
                "qty": m.qty,
                "price": m.price,
                "total": total_value,
                "fee": fee,
                "allowance_type": m.buy_order.allowance_type,
            })

        await self.trade_repo.commit()
        return trades
