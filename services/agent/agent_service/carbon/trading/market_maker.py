"""Market maker providing baseline liquidity."""
import uuid
from datetime import datetime, timezone
from typing import Optional


class MarketMaker:
    def __init__(
        self,
        spread_pct: float = 0.02,
        depth_per_side: float = 1000.0,
        refresh_secs: float = 30.0,
    ):
        self.spread_pct = spread_pct
        self.depth_per_side = depth_per_side
        self.refresh_secs = refresh_secs
        self._last_price: float = 80.0  # initial carbon price

    def update_reference_price(self, price: float) -> None:
        if price > 0:
            self._last_price = price

    def generate_quotes(self) -> list[dict]:
        """Generate bid/ask quotes for all allowance types."""
        bid = round(self._last_price * (1 - self.spread_pct / 2), 2)
        ask = round(self._last_price * (1 + self.spread_pct / 2), 2)
        return [
            {
                "side": "buy", "allowance_type": "CEA",
                "price": bid, "qty": self.depth_per_side,
                "plant_id": "market_maker",
            },
            {
                "side": "sell", "allowance_type": "CEA",
                "price": ask, "qty": self.depth_per_side,
                "plant_id": "market_maker",
            },
        ]
