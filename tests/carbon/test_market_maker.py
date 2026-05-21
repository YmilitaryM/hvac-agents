from services.agent.agent_service.carbon.trading.market_maker import MarketMaker
from services.agent.agent_service.carbon.trading.virtual_participants import (
    VirtualParticipantManager, VirtualParticipant,
)


def test_market_maker_quotes():
    mm = MarketMaker(spread_pct=0.02, depth_per_side=500.0)
    mm.update_reference_price(80.0)
    quotes = mm.generate_quotes()
    assert len(quotes) == 2
    buy = [q for q in quotes if q["side"] == "buy"][0]
    sell = [q for q in quotes if q["side"] == "sell"][0]
    assert buy["price"] == 79.2
    assert sell["price"] == 80.8
    assert buy["plant_id"] == "market_maker"


def test_virtual_participant_generates_valid_order():
    p = VirtualParticipant("test", "speculator", 1.0)
    order = p.generate_order(80.0, "CEA")
    assert order["plant_id"] == "virtual_test"
    assert order["allowance_type"] == "CEA"
    assert order["qty"] > 0
    assert 40 <= order["price"] <= 120  # within 50% of ref


def test_manager_generates_orders():
    mgr = VirtualParticipantManager()
    mgr.set_market_phase("normal")
    # Force all participants active
    for p in mgr.participants:
        p._last_decision_time = 0.0
    all_orders = []
    for _ in range(20):
        all_orders.extend(mgr.get_active_orders(80.0))
    assert len(all_orders) > 0
