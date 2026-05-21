"""Continuous auction order book using sortedcontainers."""
from sortedcontainers import SortedList

from ...carbon_models import CarbonOrderModel


class OrderBook:
    """Price-time priority order book for one allowance type."""

    def __init__(self, allowance_type: str):
        self.allowance_type = allowance_type
        self._buy_orders: SortedList[CarbonOrderModel] = SortedList(
            key=lambda o: (-o.price, o.created_at)
        )
        self._sell_orders: SortedList[CarbonOrderModel] = SortedList(
            key=lambda o: (o.price, o.created_at)
        )

    def add(self, order: CarbonOrderModel) -> None:
        target = self._buy_orders if order.side == "buy" else self._sell_orders
        target.add(order)

    def remove(self, order: CarbonOrderModel) -> None:
        target = self._buy_orders if order.side == "buy" else self._sell_orders
        if order in target:
            target.remove(order)

    @property
    def best_bid(self) -> float:
        return self._buy_orders[0].price if self._buy_orders else 0.0

    @property
    def best_ask(self) -> float:
        return self._sell_orders[0].price if self._sell_orders else float("inf")

    @property
    def spread(self) -> float:
        if not self._buy_orders or not self._sell_orders:
            return 0.0
        return self.best_ask - self.best_bid

    @property
    def mid_price(self) -> float:
        if not self._buy_orders or not self._sell_orders:
            return 0.0
        return (self.best_bid + self.best_ask) / 2.0

    def get_depth(self, depth: int = 10) -> dict:
        buys, sells = [], []
        total_buy_vol = 0.0
        for o in self._buy_orders[:depth]:
            total_buy_vol += o.remaining
            buys.append({"price": o.price, "qty": o.remaining, "total": round(total_buy_vol, 2)})
        total_sell_vol = 0.0
        for o in self._sell_orders[:depth]:
            total_sell_vol += o.remaining
            sells.append({"price": o.price, "qty": o.remaining, "total": round(total_sell_vol, 2)})
        return {"bids": buys, "asks": sells, "spread": self.spread}
