"""Analytics and risk metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_returns(price_df: pd.DataFrame) -> pd.DataFrame:
    return price_df.pct_change().dropna(how="all")


def cumulative_returns(ret_df: pd.DataFrame) -> pd.DataFrame:
    return (1 + ret_df.fillna(0)).cumprod() - 1


def rolling_vol(ret_df: pd.DataFrame, window: int = 63) -> pd.DataFrame:
    return ret_df.rolling(window).std() * np.sqrt(252)


def max_drawdown(series: pd.Series) -> float:
    wealth = (1 + series.fillna(0)).cumprod()
    peak = wealth.cummax()
    drawdown = wealth / peak - 1
    return float(drawdown.min())


def rolling_sharpe(ret_df: pd.DataFrame, window: int = 63, rf: float = 0.0) -> pd.DataFrame:
    excess = ret_df - rf / 252
    mu = excess.rolling(window).mean() * 252
    sig = excess.rolling(window).std() * np.sqrt(252)
    return mu / sig


def hhi(weights: pd.Series) -> float:
    w = (weights / 100.0).fillna(0)
    return float((w**2).sum())


def top5_weight(weights: pd.Series) -> float:
    return float(weights.sort_values(ascending=False).head(5).sum())


def zscore(series: pd.Series, window: int = 252) -> pd.Series:
    return (series - series.rolling(window).mean()) / series.rolling(window).std()
