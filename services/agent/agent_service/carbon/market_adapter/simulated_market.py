"""Simulated carbon market implementation."""
import time
import uuid
from datetime import datetime, timezone

from .interface import CarbonMarketAdapter
from ..assets.allowance_mgr import AllowanceManager
from ..trading.matching_engine import MatchingEngine
from ..trading.settlement import SettlementEngine
from ..trading.market_maker import MarketMaker
from ..trading.virtual_participants import VirtualParticipantManager
from ...carbon_repositories import (
    CarbonOrderRepository, CarbonTradeRepository,
    CarbonLedgerRepository, CarbonPriceRepository,
    CarbonHoldingsRepository, CarbonComplianceRepository,
    CarbonAuctionRepository,
)


class SimulatedMarket:
    def __init__(
        self,
        order_repo: CarbonOrderRepository,
        trade_repo: CarbonTradeRepository,
        ledger_repo: CarbonLedgerRepository,
        price_repo: CarbonPriceRepository,
        holdings_repo: CarbonHoldingsRepository,
        compliance_repo: CarbonComplianceRepository,
        auction_repo: CarbonAuctionRepository,
        spread_pct: float = 0.02,
    ):
        self.order_repo = order_repo
        self.trade_repo = trade_repo
        self.ledger_repo = ledger_repo
        self.price_repo = price_repo
        self.holdings_repo = holdings_repo
        self.compliance_repo = compliance_repo
        self.auction_repo = auction_repo

        self.allowance_mgr = AllowanceManager(ledger_repo)
        self.matching = MatchingEngine(order_repo, trade_repo, ledger_repo)
        self.settlement = SettlementEngine(trade_repo, ledger_repo, order_repo)
        self.market_maker = MarketMaker(spread_pct=spread_pct)
        self.virtual_mgr = VirtualParticipantManager()

        self._tick_callbacks: list = []

    # ── Market Data ──
    async def get_order_book(self, allowance_type: str, depth: int = 10) -> dict:
        book = self.matching.get_book(allowance_type)
        result = book.get_depth(depth)
        result["allowance_type"] = allowance_type
        result["mid_price"] = book.mid_price
        result["latest_price"] = await self.get_latest_price(allowance_type)
        return result

    async def get_latest_price(self, allowance_type: str) -> float:
        price = await self.price_repo.get_latest_price(allowance_type)
        return price if price else 80.0

    async def get_ohlcv(
        self, allowance_type: str, interval: str = "1h",
        start: float = None, end: float = None, limit: int = 200,
    ) -> list:
        if start is None:
            start = time.time() - 86400 * 7
        if end is None:
            end = time.time()
        records = await self.price_repo.get_ohlcv(
            allowance_type, interval, start, end, limit
        )
        return [
            {"o": r.open, "h": r.high, "l": r.low, "c": r.close, "v": r.volume, "t": r.timestamp}
            for r in records
        ]

    async def subscribe_tick(self, allowance_type: str, callback) -> None:
        self._tick_callbacks.append((allowance_type, callback))

    # ── Trading ──
    async def place_order(self, order_data: dict) -> dict:
        expire_at = order_data.get("expire_at")
        if expire_at is not None and isinstance(expire_at, str):
            expire_at = datetime.fromisoformat(expire_at)
        order = await self.order_repo.create({
            "id": order_data.get("id", uuid.uuid4().hex[:16]),
            "plant_id": order_data["plant_id"],
            "side": order_data["side"],
            "allowance_type": order_data["allowance_type"],
            "order_type": order_data.get("order_type", "limit"),
            "qty": order_data["qty"],
            "remaining": order_data["qty"],
            "price": order_data.get("price", 0.0),
            "peak_qty": order_data.get("peak_qty"),
            "expire_at": expire_at,
        })
        matches = self.matching.match_order(order)
        trades = await self.settlement.settle(matches) if matches else []
        await self.order_repo.commit()
        return {"order": {"id": order.id, "status": order.status, "remaining": order.remaining}, "trades": trades}

    async def cancel_order(self, order_id: str) -> bool:
        order = await self.order_repo.get_by_id(order_id)
        if not order or order.status in ("filled", "cancelled"):
            return False
        order.status = "cancelled"
        book = self.matching.get_book(order.allowance_type)
        book.remove(order)
        await self.order_repo.commit()
        return True

    async def get_order(self, order_id: str) -> dict:
        order = await self.order_repo.get_by_id(order_id)
        return {"id": order.id, "plant_id": order.plant_id, "side": order.side,
                "allowance_type": order.allowance_type, "order_type": order.order_type,
                "qty": order.qty, "remaining": order.remaining, "price": order.price,
                "status": order.status} if order else {}

    async def get_my_orders(self, plant_id: str, status: str = None) -> list:
        orders = await self.order_repo.get_open_orders(plant_id=plant_id, status=status)
        return [{"id": o.id, "side": o.side, "allowance_type": o.allowance_type,
                 "order_type": o.order_type, "qty": o.qty, "remaining": o.remaining,
                 "price": o.price, "status": o.status} for o in orders]

    async def get_my_trades(self, plant_id: str, start: float = None, end: float = None) -> list:
        trades = await self.trade_repo.get_by_plant(plant_id, start, end)
        return [{"id": t.id, "buy_plant": t.buy_plant_id, "sell_plant": t.sell_plant_id,
                 "qty": t.qty_tco2, "price": t.price, "total": t.total_value,
                 "allowance_type": t.allowance_type, "settled_at": str(t.settled_at)}
                for t in trades]

    async def get_trade_fee(self, trade_value: float) -> float:
        return round(trade_value * 0.001, 2)

    # ── Allowance Lifecycle ──
    async def receive_allocation(self, plant_id: str, period: str, qty: float, source: str = "free") -> dict:
        return await self.allowance_mgr.allocate(plant_id, period, qty, "CEA", source)

    async def participate_auction(self, plant_id: str, bid_qty: float, bid_price: float, auction_id: str = "") -> dict:
        return {"plant_id": plant_id, "bid_qty": bid_qty, "bid_price": bid_price, "auction_id": auction_id, "status": "submitted"}

    async def transfer(self, from_plant: str, to_plant: str, qty: float, atype: str = "CEA") -> dict:
        period = time.strftime("%Y", time.localtime(time.time()))
        return await self.allowance_mgr.transfer(from_plant, to_plant, qty, atype, period)

    async def surrender(self, plant_id: str, period: str, qty: float, atype: str = "CEA") -> dict:
        balance = await self.ledger_repo.get_balance(plant_id, atype, period)
        if balance < qty:
            raise ValueError(f"Insufficient {atype}: {balance} < {qty}")
        new_balance = balance - qty
        await self.ledger_repo.create_entry({
            "plant_id": plant_id, "period": period,
            "entry_type": "surrender", "direction": "debit",
            "allowance_type": atype, "qty_tco2": qty, "unit_price": 0.0,
            "balance_after": round(new_balance, 4),
        })
        await self.ledger_repo.commit()
        return {"plant_id": plant_id, "surrendered": qty, "type": atype, "status": "completed"}

    # ── Holdings ──
    async def get_holdings(self, plant_id: str, period: str) -> dict:
        return await self.allowance_mgr.get_holdings(plant_id, period)

    async def get_holdings_snapshot(self, plant_id: str, date: str = None) -> dict:
        period = time.strftime("%Y", time.localtime(time.time()))
        snapshots = await self.holdings_repo.get_holdings(plant_id, period)
        return {"plant_id": plant_id, "period": period, "holdings": [
            {"type": s.allowance_type, "total": s.total_held, "used": s.used,
             "available": s.available, "locked": s.locked}
            for s in snapshots
        ]}

    # ── Market Info ──
    async def get_market_calendar(self) -> dict:
        return {
            "trading_hours": "09:30-15:00",
            "trading_days": "Mon-Fri",
            "compliance_deadline": f"{time.strftime('%Y')}-12-31",
            "market_status": "open",
            "next_auction": f"{time.strftime('%Y')}-03-15",
        }

    async def get_compliance_deadline(self, period: str) -> dict:
        return {"period": period, "deadline": f"{period}-12-31T23:59:59", "remaining_days": 224}
