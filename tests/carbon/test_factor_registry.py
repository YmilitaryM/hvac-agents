from services.agent.agent_service.carbon.emission.factor_registry import FactorRegistry


def test_get_regional_factor():
    reg = FactorRegistry()
    assert reg.get_factor("north", month=5) == 0.525
    assert reg.get_factor("south", month=5) == 0.389
    assert reg.get_factor("unknown", month=5) == 0.50


def test_seasonal_adjustment():
    reg = FactorRegistry()
    summer = reg.get_factor("east", month=7)
    winter = reg.get_factor("east", month=1)
    assert summer > winter


def test_override():
    reg = FactorRegistry()
    reg.set_override("north", 0.600)
    assert reg.get_factor("north") == 0.600
    reg.clear_override("north")
    assert reg.get_factor("north", month=5) == 0.525
