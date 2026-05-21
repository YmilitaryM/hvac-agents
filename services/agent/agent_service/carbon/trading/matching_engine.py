"""Price-time priority matching engine."""
from typing import List, Tuple
from dataclasses import dataclass

from .order_book import OrderBook
from ...carbon_models import CarbonOrderModel


@dataclass
class Match:
    buy_order: CarbonOrderModel
    sell_order: CarbonOrderModel
    qty: float
    price: float


class MatchingEngine:
    def __init__(self, order_repo, trade_repo, ledger_repo):
        self.order_repo = order_repo
        self.trade_repo = trade_repo
        self.ledger_repo = ledger_repo
        self.books: dict[str, OrderBook] = {}

    def get_book(self, allowance_type: str) -> OrderBook:
        if allowance_type not in self.books:
            self.books[allowance_type] = OrderBook(allowance_type)
        return self.books[allowance_type]

    def _can_match(self, buy: CarbonOrderModel, sell: CarbonOrderModel) -> bool:
        if buy.order_type == "market":
            return True
        if sell.order_type == "market":
            return True
        return buy.price >= sell.price

    def match_order(self, incoming: CarbonOrderModel) -> List[Match]:
        book = self.get_book(incoming.allowance_type)
        matches: List[Match] = []

        if incoming.side == "buy":
            counterparties = list(book._sell_orders)
            for sell in counterparties:
                if incoming.remaining <= 0:
                    break
                if not self._can_match(incoming, sell):
                    continue
                trade_qty = min(incoming.remaining, sell.remaining)
                trade_price = sell.price
                incoming.remaining -= trade_qty
                sell.remaining -= trade_qty

                if sell.remaining <= 0:
                    sell.status = "filled"
                    book.remove(sell)
                else:
                    sell.status = "partial_fill"

                matches.append(Match(incoming, sell, trade_qty, trade_price))
        else:  # sell
            counterparties = list(book._buy_orders)
            for buy in counterparties:
                if incoming.remaining <= 0:
                    break
                if not self._can_match(buy, incoming):
                    continue
                trade_qty = min(incoming.remaining, buy.remaining)
                trade_price = buy.price
                incoming.remaining -= trade_qty
                buy.remaining -= trade_qty

                if buy.remaining <= 0:
                    buy.status = "filled"
                    book.remove(buy)
                else:
                    buy.status = "partial_fill"

                matches.append(Match(buy, incoming, trade_qty, trade_price))

        # If incoming has remaining, add to book (limit only)
        if incoming.remaining > 0 and incoming.order_type != "market":
            incoming.status = "pending" if incoming.remaining == incoming.qty else "partial_fill"
            book.add(incoming)

        return matches
