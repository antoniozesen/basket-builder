"""Macro data provider using fredapi and Streamlit secrets."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from fredapi import Fred

from src.config import CACHE_TTL_SECONDS


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_fred_series(series_map: dict[str, str], start: str, end: str) -> pd.DataFrame:
    key = st.secrets.get("FRED_API_KEY", "")
    if not key:
        return pd.DataFrame()
    fred = Fred(api_key=key)
    frames = []
    for label, sid in series_map.items():
        try:
            s = fred.get_series(sid, observation_start=start, observation_end=end)
            if s is not None and not s.empty:
                frames.append(pd.Series(s, name=label))
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, axis=1)
    out.index = pd.to_datetime(out.index)
    return out.sort_index()
