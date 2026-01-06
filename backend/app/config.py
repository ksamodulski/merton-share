from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Anthropic API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # Cache settings
    market_data_cache_hours: int = 24

    # Methodology settings
    use_views_in_optimization: bool = False  # Enable BL-lite view blending
    expected_return_min: float = -0.05       # -5% lower bound
    expected_return_max: float = 0.15        # +15% upper bound
    default_risk_free_rate: float = 0.025    # 2.5% default ECB rate

    # View blending adjustments (when use_views_in_optimization=True)
    institutional_view_adjustment: float = 0.01  # +/-1% per stance
    valuation_signal_adjustment: float = 0.005   # +/-0.5% per signal

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
