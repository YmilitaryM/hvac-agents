import pytest
from src.config import Config, get_config, set_config


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration tests requiring running services")
    config.addinivalue_line("markers", "asyncio: async test marker")


@pytest.fixture
def test_config():
    cfg = Config(debug=True)
    cfg.llm.provider = "mock"
    set_config(cfg)
    yield cfg
    set_config(Config())


@pytest.fixture
def sample_plant_params():
    return {
        "num_chillers": 3,
        "num_cooling_towers": 3,
        "num_chw_pumps": 3,
        "num_cw_pumps": 3,
        "chiller_capacity_rt": 500,
        "design_chw_supply_temp": 7.0,
        "design_chw_return_temp": 12.0,
        "design_cw_supply_temp": 32.0,
        "design_cw_return_temp": 37.0,
        "design_wet_bulb_temp": 28.0,
    }
