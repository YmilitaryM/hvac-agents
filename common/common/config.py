from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://hvac:hvac_dev@localhost:5432/db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    debug: bool = False
    # Service URLs for inter-service communication
    asset_service_url: str = "http://localhost:8001"
    env_service_url: str = "http://localhost:8002"
    sim_service_url: str = "http://localhost:8003"
    agent_service_url: str = "http://localhost:8004"
    acquisition_service_url: str = "http://localhost:8005"
    acq_database_url: str = "postgresql+asyncpg://hvac:hvac_dev@localhost:5438/acq_db"

    model_config = {"env_file": ".env"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
