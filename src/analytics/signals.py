"""Signal generation and suggestion engine."""
from __future__ import annotations

import pandas as pd


def momentum_signal(price_df: pd.DataFrame) -> pd.DataFrame:
    m12 = price_df.pct_change(252)
    m1 = price_df.pct_change(21)
    mom_12_1 = m12 - m1
    m6 = price_df.pct_change(126)
    return pd.DataFrame({"mom_12_1": mom_12_1.iloc[-1], "mom_6m": m6.iloc[-1]})


def trend_signal(price_df: pd.DataFrame) -> pd.Series:
    ma50 = price_df.rolling(50).mean().iloc[-1]
    ma200 = price_df.rolling(200).mean().iloc[-1]
    return (ma50 > ma200).astype(int)


def composite_signal(price_df: pd.DataFrame) -> pd.DataFrame:
    mom = momentum_signal(price_df)
    tr = trend_signal(price_df)
    out = mom.copy()
    out["trend"] = tr
    out = out.fillna(0)
    out["score"] = out[["mom_12_1", "mom_6m"]].mean(axis=1) + 0.05 * out["trend"]
    return out.sort_values("score", ascending=False)


def suggest_reweight(holdings: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    merged = holdings.merge(scores[["score"]], left_on="ticker", right_index=True, how="left").fillna(0)
    merged["adj"] = merged["weight"] + merged["score"] * 10
    merged["new_weight"] = merged["adj"] / merged["adj"].sum() * 100
    merged["delta"] = merged["new_weight"] - merged["weight"]
    return merged[["ticker", "weight", "new_weight", "delta", "score"]].sort_values("delta", ascending=False)
