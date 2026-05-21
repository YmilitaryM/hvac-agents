import time
from services.agent.agent_service.carbon.trading.order_book import OrderBook
from services.agent.agent_service.carbon_models import CarbonOrderModel


def _make_order(side, price, qty, order_type="limit"):
    return CarbonOrderModel(
        id=f"ord-{side}-{price}-{time.time()}",
        plant_id="plant-1", side=side, allowance_type="CEA",
        order_type=order_type, qty=qty, remaining=qty, price=price,
    )


def test_order_book_depth():
    book = OrderBook("CEA")
    book.add(_make_order("sell", 85.0, 200.0))
    book.add(_make_order("sell", 83.0, 150.0))
    book.add(_make_order("buy", 82.0, 180.0))
    book.add(_make_order("buy", 80.0, 300.0))

    depth = book.get_depth()
    assert book.best_bid == 82.0
    assert book.best_ask == 83.0
    assert book.spread == 1.0
    assert len(depth["bids"]) == 2
    assert len(depth["asks"]) == 2
    assert depth["bids"][0]["price"] == 82.0  # highest bid first
    assert depth["asks"][0]["price"] == 83.0  # lowest ask first


def test_remove_order():
    book = OrderBook("CEA")
    o = _make_order("buy", 82.0, 100.0)
    book.add(o)
    assert book.best_bid == 82.0
    book.remove(o)
    assert book.best_bid == 0.0
