"""Virtual external market participants for price discovery."""
import random
import time
from typing import List


class VirtualParticipant:
    def __init__(self, name: str, strategy: str, weight: float):
        self.name = name
        self.strategy = strategy  # compliance_buyer, speculator, surplus_seller, ccer_holder
        self.weight = weight
        self._last_decision_time = 0.0

    def should_act(self, now: float, market_phase: str) -> bool:
        """Decide if this participant should place an order now."""
        if now - self._last_decision_time < random.uniform(30, 120):
            return False
        self._last_decision_time = now

        if self.strategy == "compliance_buyer":
            return market_phase == "near_deadline" or random.random() < 0.15
        elif self.strategy == "speculator":
            return random.random() < 0.4
        elif self.strategy == "surplus_seller":
            return random.random() < 0.3
        elif self.strategy == "ccer_holder":
            return random.random() < 0.2
        return False

    def generate_order(self, ref_price: float, allowance_type: str = "CEA") -> dict:
        """Generate an order based on strategy."""
        side = random.choice(["buy", "sell"])
        price_noise = random.gauss(0, 0.03)  # 3% std price noise
        price_adj = 1.0 + price_noise

        if self.strategy == "compliance_buyer":
            side = "buy"
            price_adj = 1.0 + abs(price_noise)  # willing to pay a bit more
        elif self.strategy == "surplus_seller":
            side = "sell"
            price_adj = 1.0 - abs(price_noise)  # willing to sell a bit cheaper
        elif self.strategy == "ccer_holder":
            allowance_type = "CCER"
            price_adj = 0.6 + random.random() * 0.2  # CCER at 60-80% of CEA

        qty = random.uniform(50, 500) * self.weight
        price = round(ref_price * max(0.5, min(1.5, price_adj)), 2)

        return {
            "plant_id": f"virtual_{self.name}",
            "side": side,
            "allowance_type": allowance_type,
            "order_type": "limit",
            "qty": round(qty, 2),
            "price": price,
        }


class VirtualParticipantManager:
    def __init__(self):
        self.participants: List[VirtualParticipant] = [
            VirtualParticipant("compliance_1", "compliance_buyer", 0.30),
            VirtualParticipant("compliance_2", "compliance_buyer", 0.30),
            VirtualParticipant("speculator_1", "speculator", 0.25),
            VirtualParticipant("surplus_1", "surplus_seller", 0.25),
            VirtualParticipant("surplus_2", "surplus_seller", 0.25),
            VirtualParticipant("ccer_holder_1", "ccer_holder", 0.20),
        ]
        self._market_phase = "normal"

    def set_market_phase(self, phase: str):
        self._market_phase = phase  # normal | near_deadline | post_compliance

    def get_active_orders(self, ref_price: float) -> List[dict]:
        now = time.time()
        orders = []
        for p in self.participants:
            if p.should_act(now, self._market_phase):
                atype = "CEA" if p.strategy != "ccer_holder" else "CCER"
                orders.append(p.generate_order(ref_price, atype))
        return orders
