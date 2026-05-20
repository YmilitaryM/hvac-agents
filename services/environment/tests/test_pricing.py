"""Unit tests for EnergyPrice model and pricing logic."""

import pytest


# ── Import EnergyPriceModel if env_service is available ─────────────────

try:
    from env_service.models import EnergyPriceModel
    HAS_ENV_SERVICE = True
except ImportError:
    EnergyPriceModel = None
    HAS_ENV_SERVICE = False


# ── EnergyPriceModel columns & defaults ───────────────────────────────

@pytest.mark.skipif(not HAS_ENV_SERVICE, reason="env_service package not installed")
class TestEnergyPriceModelColumns:
    """Test that the EnergyPriceModel SQLAlchemy model has expected columns."""

    def test_table_name(self):
        assert EnergyPriceModel.__tablename__ == "energy_prices"

    def test_column_names(self):
        cols = [c.name for c in EnergyPriceModel.__table__.columns]
        expected = {"id", "timestamp", "electricity_price_per_kwh", "carbon_intensity_kg_per_kwh"}
        assert set(cols) == expected

    def test_id_is_string(self):
        col = EnergyPriceModel.__table__.columns["id"]
        assert str(col.type) == "VARCHAR(32)"
        assert not col.nullable

    def test_timestamp_is_float(self):
        col = EnergyPriceModel.__table__.columns["timestamp"]
        assert str(col.type) == "FLOAT"
        assert not col.nullable

    def test_electricity_price_is_float(self):
        col = EnergyPriceModel.__table__.columns["electricity_price_per_kwh"]
        assert str(col.type) == "FLOAT"
        assert col.nullable is True

    def test_carbon_intensity_is_float_with_default(self):
        col = EnergyPriceModel.__table__.columns["carbon_intensity_kg_per_kwh"]
        assert str(col.type) == "FLOAT"
        assert col.default.arg == 0.0

    def test_instance_defaults(self):
        p = EnergyPriceModel(
            id="test1", timestamp=1716210000.5, electricity_price_per_kwh=0.12,
        )
        assert p.carbon_intensity_kg_per_kwh is None
        assert p.timestamp == 1716210000.5
        assert p.electricity_price_per_kwh == 0.12

    def test_instance_with_all_fields(self):
        p = EnergyPriceModel(
            id="test2", timestamp=1716300000.0,
            electricity_price_per_kwh=0.15, carbon_intensity_kg_per_kwh=0.35,
        )
        assert p.carbon_intensity_kg_per_kwh == 0.35
        assert p.id == "test2"


@pytest.mark.skipif(not HAS_ENV_SERVICE, reason="env_service package not installed")
class TestEnergyPriceValues:
    """Test pricing value boundaries and realistic scenarios."""

    def test_zero_price(self):
        p = EnergyPriceModel(id="z", timestamp=1716210000.0, electricity_price_per_kwh=0.0)
        assert p.electricity_price_per_kwh == 0.0
        assert p.carbon_intensity_kg_per_kwh is None

    def test_negative_price(self):
        p = EnergyPriceModel(id="neg", timestamp=1716210000.0, electricity_price_per_kwh=-0.05)
        assert p.electricity_price_per_kwh == -0.05

    def test_high_carbon_intensity(self):
        p = EnergyPriceModel(
            id="high_carbon", timestamp=1716210000.0,
            electricity_price_per_kwh=0.10, carbon_intensity_kg_per_kwh=0.8,
        )
        assert p.carbon_intensity_kg_per_kwh == 0.8

    def test_timestamp_ordering(self):
        early = EnergyPriceModel(id="e", timestamp=1000.0, electricity_price_per_kwh=0.10)
        late = EnergyPriceModel(id="l", timestamp=2000.0, electricity_price_per_kwh=0.10)
        assert early.timestamp < late.timestamp


# ── Pricing tier logic (standalone — no service dependency) ────────────

PRICE_TIERS = {
    "negative": lambda p: p < 0,
    "low": lambda p: 0 <= p < 0.10,
    "medium": lambda p: 0.10 <= p < 0.20,
    "high": lambda p: 0.20 <= p < 0.40,
    "critical": lambda p: p >= 0.40,
}


def classify_price_tier(price_per_kwh: float) -> str:
    for tier, predicate in PRICE_TIERS.items():
        if predicate(price_per_kwh):
            return tier
    return "unknown"


class TestPricingTiers:
    def test_negative_price_is_negative_tier(self):
        assert classify_price_tier(-0.05) == "negative"

    def test_low_price(self):
        assert classify_price_tier(0.05) == "low"

    def test_low_price_upper_boundary(self):
        assert classify_price_tier(0.099) == "low"

    def test_medium_price(self):
        assert classify_price_tier(0.15) == "medium"

    def test_medium_lower_boundary(self):
        assert classify_price_tier(0.10) == "medium"

    def test_medium_upper_boundary(self):
        assert classify_price_tier(0.19) == "medium"

    def test_high_price(self):
        assert classify_price_tier(0.25) == "high"

    def test_high_lower_boundary(self):
        assert classify_price_tier(0.20) == "high"

    def test_critical_price(self):
        assert classify_price_tier(0.50) == "critical"

    def test_critical_lower_boundary(self):
        assert classify_price_tier(0.40) == "critical"

    def test_zero_price_is_low(self):
        assert classify_price_tier(0.0) == "low"


# ── Price/carbon combined cost calculation ─────────────────────────────

def compute_effective_cost(
    electricity_price_per_kwh: float,
    carbon_intensity_kg_per_kwh: float,
    carbon_price_per_kg: float = 0.05,
) -> float:
    return electricity_price_per_kwh + (carbon_intensity_kg_per_kwh * carbon_price_per_kg)


class TestEffectiveCost:
    def test_no_carbon_cost_when_carbon_zero(self):
        cost = compute_effective_cost(0.10, 0.0)
        assert cost == 0.10

    def test_carbon_adds_to_cost(self):
        cost = compute_effective_cost(0.10, 0.5, 0.05)
        assert cost == pytest.approx(0.125)

    def test_default_carbon_price(self):
        cost = compute_effective_cost(0.15, 0.4)
        assert cost == pytest.approx(0.17)

    def test_zero_electricity_with_carbon(self):
        cost = compute_effective_cost(0.0, 0.6)
        assert cost == pytest.approx(0.03)

    def test_electricity_only_when_negative(self):
        cost = compute_effective_cost(-0.05, 0.1)
        assert cost == pytest.approx(-0.045)
