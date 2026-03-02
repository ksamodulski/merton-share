"""Real market data fetched from Yahoo Finance via yfinance."""

import logging
from typing import Optional

import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)


def _price_history_vol(ticker_sym: str, period: str = "1y") -> Optional[float]:
    """Compute annualized realized volatility from price history."""
    try:
        hist = yf.Ticker(ticker_sym).history(period=period)
        if hist.empty or len(hist) < 20:
            return None
        returns = hist["Close"].pct_change().dropna()
        return float(returns.std() * np.sqrt(252))
    except Exception as e:
        logger.warning("Realized vol fetch failed for %s: %s", ticker_sym, e)
        return None


def _spot(ticker_sym: str) -> Optional[float]:
    """Fetch current spot price / index level."""
    try:
        return float(yf.Ticker(ticker_sym).fast_info.last_price)
    except Exception as e:
        logger.warning("Spot fetch failed for %s: %s", ticker_sym, e)
        return None


def _etf_info(ticker_sym: str) -> dict:
    """Fetch P/E and dividend yield from an ETF. Returns {} on failure."""
    try:
        info = yf.Ticker(ticker_sym).info
        return {
            "trailing_pe": info.get("trailingPE"),
            # trailingAnnualDividendYield is a proper decimal (e.g. 0.013)
            "dividend_yield": info.get("trailingAnnualDividendYield"),
        }
    except Exception as e:
        logger.warning("ETF info fetch failed for %s: %s", ticker_sym, e)
        return {}


def fetch_market_snapshot() -> dict:
    """
    Fetch current market data from Yahoo Finance.

    Returns a dict with real values where available, None for unavailable fields.
    Volatilities are annualized decimals (e.g. 0.18 = 18%).
    Dividend yields are decimals (e.g. 0.013 = 1.3%).
    """
    data: dict = {}

    # --- Implied volatility ---
    # VIX and VSTOXX are quoted as % levels (e.g. 18.5), divide to get decimal
    vix = _spot("^VIX")
    data["us_implied_vol"] = round(vix / 100, 4) if vix else None

    vstoxx = _spot("V2TX.DE")
    data["europe_implied_vol"] = round(vstoxx / 100, 4) if vstoxx else None

    gvz = _spot("^GVZ")
    data["gold_implied_vol"] = round(gvz / 100, 4) if gvz else None

    # --- Realized volatility (from 1Y price history) ---
    data["us_realized_vol"] = _price_history_vol("SPY")
    data["europe_realized_vol"] = _price_history_vol("VGK")
    data["japan_realized_vol"] = _price_history_vol("EWJ")
    data["em_realized_vol"] = _price_history_vol("EEM")
    data["gold_realized_vol"] = _price_history_vol("GLD")

    # --- FX ---
    data["eur_pln"] = _spot("EURPLN=X")

    # --- Valuations ---
    us = _etf_info("SPY")
    data["us_trailing_pe"] = us.get("trailing_pe")
    data["us_dividend_yield"] = us.get("dividend_yield")

    eu = _etf_info("VGK")
    data["europe_trailing_pe"] = eu.get("trailing_pe")
    data["europe_dividend_yield"] = eu.get("dividend_yield")

    jp = _etf_info("EWJ")
    data["japan_trailing_pe"] = jp.get("trailing_pe")
    data["japan_dividend_yield"] = jp.get("dividend_yield")

    em = _etf_info("EEM")
    data["em_trailing_pe"] = em.get("trailing_pe")
    data["em_dividend_yield"] = em.get("dividend_yield")

    return data


def format_snapshot_for_prompt(snapshot: dict) -> str:
    """Format the snapshot into a readable block for injection into the Claude prompt."""

    def pct(val):
        return f"{val * 100:.2f}%" if val is not None else "N/A"

    def num(val, decimals=2):
        return f"{val:.{decimals}f}" if val is not None else "N/A"

    return "\n".join([
        "LIVE MARKET DATA (fetched from Yahoo Finance right now):",
        "",
        "Implied volatility (as decimals — use these directly):",
        f"  US (VIX):      {pct(snapshot.get('us_implied_vol'))}   → decimal: {num(snapshot.get('us_implied_vol'), 4)}",
        f"  Europe (VSTOXX): {pct(snapshot.get('europe_implied_vol'))}   → decimal: {num(snapshot.get('europe_implied_vol'), 4)}",
        f"  Gold (GVZ):    {pct(snapshot.get('gold_implied_vol'))}   → decimal: {num(snapshot.get('gold_implied_vol'), 4)}",
        "",
        "Realized volatility 1Y (as decimals — use these directly):",
        f"  US (SPY):    {pct(snapshot.get('us_realized_vol'))}   → decimal: {num(snapshot.get('us_realized_vol'), 4)}",
        f"  Europe (VGK): {pct(snapshot.get('europe_realized_vol'))}   → decimal: {num(snapshot.get('europe_realized_vol'), 4)}",
        f"  Japan (EWJ):  {pct(snapshot.get('japan_realized_vol'))}   → decimal: {num(snapshot.get('japan_realized_vol'), 4)}",
        f"  EM (EEM):     {pct(snapshot.get('em_realized_vol'))}   → decimal: {num(snapshot.get('em_realized_vol'), 4)}",
        f"  Gold (GLD):   {pct(snapshot.get('gold_realized_vol'))}   → decimal: {num(snapshot.get('gold_realized_vol'), 4)}",
        "",
        "Valuations (ETF proxies — use these directly, do NOT substitute your own guesses):",
        f"  US (SPY):     Trailing P/E = {num(snapshot.get('us_trailing_pe'), 1)},  Div Yield = {pct(snapshot.get('us_dividend_yield'))}",
        f"  Europe (VGK): Trailing P/E = {num(snapshot.get('europe_trailing_pe'), 1)},  Div Yield = {pct(snapshot.get('europe_dividend_yield'))}",
        f"  Japan (EWJ):  Trailing P/E = {num(snapshot.get('japan_trailing_pe'), 1)},  Div Yield = {pct(snapshot.get('japan_dividend_yield'))}",
        f"  EM (EEM):     Trailing P/E = {num(snapshot.get('em_trailing_pe'), 1)},  Div Yield = {pct(snapshot.get('em_dividend_yield'))}",
        "",
        "FX:",
        f"  EUR/PLN: {num(snapshot.get('eur_pln'), 4)}",
    ])
