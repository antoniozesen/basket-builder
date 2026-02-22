"""Global configuration constants for the app."""
from __future__ import annotations

from datetime import date, timedelta

APP_TITLE = "Cross-Asset Market Monitor + Basket Builder"
DB_PATH = "basket_builder.db"
CACHE_TTL_SECONDS = 60 * 30
DEFAULT_LOOKBACK_YEARS = 3
DEFAULT_START_DATE = date.today() - timedelta(days=365 * DEFAULT_LOOKBACK_YEARS)
DEFAULT_END_DATE = date.today()

REQUIRED_UNIVERSE_COLUMNS = [
    "instrument_id",
    "ticker",
    "name",
    "asset_class",
    "region",
    "currency",
    "eligible",
]
OPTIONAL_UNIVERSE_COLUMNS = ["isin", "min_weight", "max_weight", "notes"]

ALLOWED_ASSET_CLASSES = ["Equity", "Rates", "Credit", "Commodities", "FX", "Alternatives"]

MAX_HOLDINGS_DEFAULT = 50
WEIGHT_TOLERANCE = 1e-3

DEFAULT_BENCHMARKS = ["SPY", "AGG", "GLD"]

PERCENT_FMT = "{:.2%}"
LEVEL_FMT = "{:.2f}"

DEFAULT_FRED_SERIES = {
    "US 10Y": "DGS10",
    "US CPI": "CPIAUCSL",
    "Unemployment": "UNRATE",
    "Fed Funds": "FEDFUNDS",
    "Recession": "USREC",
}
