import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    provider: str = "anthropic"
    deep_model: str = "claude-sonnet-4-6"
    quick_model: str = "claude-haiku-4-5-20251001"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    max_debate_rounds: int = 2
    max_risk_discuss_rounds: int = 1


@dataclass
class SimulationConfig:
    plant_config_path: str = "config/plant.toml"
    weather_data_path: str = "data/weather"
    data_generation_samples: int = 5000


@dataclass
class OptimizationConfig:
    solver_timeout_sec: float = 30.0
    pareto_max_solutions: int = 5
    wear_cost_per_start: dict[str, float] = field(default_factory=lambda: {
        "chiller": 150.0,
        "pump": 30.0,
        "cooling_tower": 20.0,
    })
    electricity_price_file: str = "config/price.toml"
    carbon_price_per_kg: float = 0.08


@dataclass
class StorageConfig:
    db_url: str = "postgresql://localhost:5432/hvac"
    redis_url: str = "redis://localhost:6379/0"
    timeseries_table: str = "sensor_data"
    use_db: bool = False  # True when DATABASE_URL env var is set


@dataclass
class RLConfig:
    algorithm: str = "contextual_bandit"
    model_path: str = "models/rl_reviewer.pkl"
    confidence_threshold: float = 0.85
    training_interval_days: int = 7
    auto_train: bool = False  # Enable online learning in production


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    rl: RLConfig = field(default_factory=RLConfig)
    debug: bool = False
    api_key: str = ""  # If set, all mutation endpoints require this key

    @classmethod
    def from_env(cls) -> "Config":
        provider = os.getenv("LLM_PROVIDER", "anthropic")
        api_key = (
            os.getenv("ANTHROPIC_API_KEY")
            if provider == "anthropic"
            else os.getenv("OPENAI_API_KEY")
        )
        db_url = os.getenv("DATABASE_URL", "")
        redis_url = os.getenv("REDIS_URL", "")
        return cls(
            llm=LLMConfig(
                provider=provider,
                api_key=api_key,
                base_url=os.getenv("LLM_BASE_URL"),
            ),
            storage=StorageConfig(
                db_url=db_url or "postgresql://localhost:5432/hvac",
                redis_url=redis_url or "redis://localhost:6379/0",
                use_db=bool(db_url),
            ),
            rl=RLConfig(
                auto_train=os.getenv("RL_AUTO_TRAIN", "").lower() == "true",
            ),
            debug=os.getenv("DEBUG", "").lower() == "true",
            api_key=os.getenv("API_KEY", ""),
        )


_default_config = Config()


def get_config() -> Config:
    return _default_config


def set_config(cfg: Config) -> None:
    global _default_config
    _default_config = cfg
