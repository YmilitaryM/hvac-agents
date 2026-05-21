import time
from services.agent.agent_service.carbon.trading.matching_engine import MatchingEngine
from services.agent.agent_service.carbon_models import CarbonOrderModel


def _make_order(side, price, qty, order_type="limit", plant_id="plant-1"):
    return CarbonOrderModel(
        id=f"ord-{side}-{price}-{time.time()}",
        plant_id=plant_id, side=side, allowance_type="CEA",
        order_type=order_type, qty=qty, remaining=qty, price=price,
    )


def test_buy_matches_lowest_sell():
    engine = MatchingEngine(None, None, None)
    book = engine.get_book("CEA")
    book.add(_make_order("sell", 83.0, 100.0))
    book.add(_make_order("sell", 85.0, 200.0))

    buy = _make_order("buy", 85.0, 150.0)
    matches = engine.match_order(buy)
    assert len(matches) == 2
    assert matches[0].price == 83.0
    assert matches[0].qty == 100.0
    assert matches[1].price == 85.0
    assert matches[1].qty == 50.0


def test_sell_matches_highest_bid():
    engine = MatchingEngine(None, None, None)
    book = engine.get_book("CEA")
    book.add(_make_order("buy", 85.0, 200.0))
    book.add(_make_order("buy", 82.0, 100.0))

    sell = _make_order("sell", 80.0, 250.0)
    matches = engine.match_order(sell)
    assert len(matches) == 2
    assert matches[0].price == 85.0  # trades at counterparty (buyer) price
    assert matches[0].qty == 200.0
    assert matches[1].price == 82.0
    assert matches[1].qty == 50.0
