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
    claude_model: str = "claude-opus-4-8"
    # The market-data fetch is web-search-driven gathering, not deep reasoning,
    # so it runs on a faster/cheaper model with bounded thinking and fewer
    # searches to keep latency and cost down (Opus + adaptive thinking + 7
    # searches was taking ~20 min and several dollars per run).
    market_data_model: str = "claude-sonnet-4-6"
    market_data_thinking_budget: int = 6000
    market_data_max_searches: int = 4

    # Cache settings
    market_data_cache_hours: int = 24
    # File the in-memory market-data cache is persisted to, so a restart can
    # reload the last fetch instead of paying for another Claude run. Relative
    # paths are resolved against the backend root.
    market_data_cache_file: str = "data/market_data_cache.json"

    # Methodology settings
    use_views_in_optimization: bool = False  # Enable BL-lite view blending
    expected_return_min: float = -0.05       # -5% lower bound
    expected_return_max: float = 0.15        # +15% upper bound
    default_risk_free_rate: float = 0.025    # 2.5% default ECB rate

    # View blending adjustments (when use_views_in_optimization=True)
    institutional_view_adjustment: float = 0.01  # +/-1% per stance
    valuation_signal_adjustment: float = 0.005   # +/-0.5% per signal

    # Bayes-Stein shrinkage (Jorion 1986) — shrinks μ toward cross-sectional mean
    # phi=0 means no shrinkage (raw estimates), phi=1 means full equal-weight prior
    shrinkage_intensity: float = 0.5

    # Per-region weight caps tied to global market-cap weight, so a small region
    # (e.g. developed Pacific, ~3% of global equity) can't dominate the optimum.
    # cap = clamp(market_weight * multiplier, floor, ceiling).
    region_overweight_multiplier: float = 4.0  # allow up to 4x a region's market weight
    max_region_weight: float = 0.50            # absolute ceiling for any single asset
    min_region_weight_cap: float = 0.10        # floor so tiny regions keep a usable band

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
