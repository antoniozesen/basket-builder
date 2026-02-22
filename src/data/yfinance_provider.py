"""Market data access using yfinance with caching and graceful failures."""
from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

from src.config import CACHE_TTL_SECONDS


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def quick_ticker_check(ticker: str) -> bool:
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        return not hist.empty
    except Exception:
        return False


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    frames = []
    for t in tickers:
        try:
            data = yf.download(t, start=start, end=end, progress=False, auto_adjust=True)
            if not data.empty:
                frames.append(data[["Close"]].rename(columns={"Close": t}))
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, axis=1)
    out.index = pd.to_datetime(out.index)
    return out.sort_index()


def data_health(price_df: pd.DataFrame) -> pd.DataFrame:
    if price_df.empty:
        return pd.DataFrame(columns=["ticker", "missing_pct", "last_date", "history_days"])
    rows = []
    for col in price_df.columns:
        s = price_df[col]
        rows.append(
            {
                "ticker": col,
                "missing_pct": s.isna().mean() * 100,
                "last_date": s.dropna().index.max(),
                "history_days": s.dropna().shape[0],
            }
        )
    return pd.DataFrame(rows)
