"""
Application settings and configuration.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration using environment variables."""
    
    # Database
    DATABASE_URL: str = "postgresql://localhost:5432/retail_demand"
    
    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Forecasting defaults
    DEFAULT_FORECAST_HORIZON: int = 7
    MIN_DATA_DAYS_ARIMA: int = 60
    MIN_DATA_DAYS_MOVING_AVG: int = 30
    SAFETY_STOCK_MULTIPLIER: float = 1.2
    
    # API
    API_PREFIX: str = "/api"
    
    # External APIs
    OGD_INDIA_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
