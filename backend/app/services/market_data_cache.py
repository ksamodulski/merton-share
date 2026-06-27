"""Disk-backed cache for the market-data fetch.

Stores the *raw* Claude JSON (not the assembled ``MarketData``) so that
view-blending can be re-applied cheaply on read without paying for another
fetch. Persisted to a file so the last (expensive) run survives a restart.
"""

import json
from datetime import datetime
from pathlib import Path

from app.config import get_settings

settings = get_settings()

# backend root = .../app/services/market_data_cache.py -> parents[2]
_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_raw: dict | None = None
_timestamp: datetime | None = None
_loaded = False


def _cache_file() -> Path:
    p = Path(settings.market_data_cache_file)
    return p if p.is_absolute() else _BACKEND_ROOT / p


def _ensure_loaded() -> None:
    """Lazily load the cache from disk once (e.g. after a restart)."""
    global _raw, _timestamp, _loaded
    if _loaded:
        return
    _loaded = True
    path = _cache_file()
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text())
        _raw = payload["raw"]
        _timestamp = datetime.fromisoformat(payload["cached_at"])
    except Exception:  # noqa: BLE001 — corrupt/stale file: ignore and re-fetch
        _raw = None
        _timestamp = None


def get() -> tuple[dict | None, datetime | None]:
    """Return ``(raw_claude_json, cached_at)``; either may be ``None``."""
    _ensure_loaded()
    return _raw, _timestamp


def set(raw: dict, timestamp: datetime | None = None) -> None:
    """Update the in-memory cache and persist it to disk (best-effort)."""
    global _raw, _timestamp, _loaded
    _loaded = True
    _raw = raw
    _timestamp = timestamp or datetime.utcnow()
    try:
        path = _cache_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"cached_at": _timestamp.isoformat(), "raw": _raw}))
    except Exception:  # noqa: BLE001 — disk cache is an optimization, not critical
        pass


def age_hours() -> float | None:
    """Age of the cached data in hours, or ``None`` if nothing is cached."""
    _ensure_loaded()
    if _timestamp is None:
        return None
    return (datetime.utcnow() - _timestamp).total_seconds() / 3600
