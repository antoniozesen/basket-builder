"""Validation helpers for universe and basket inputs."""
from __future__ import annotations

from typing import Tuple
import pandas as pd

from src.config import REQUIRED_UNIVERSE_COLUMNS, WEIGHT_TOLERANCE


def validate_universe_schema(df: pd.DataFrame) -> Tuple[bool, list[str]]:
    errors: list[str] = []
    missing = [c for c in REQUIRED_UNIVERSE_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {missing}")
    if "instrument_id" in df.columns and df["instrument_id"].duplicated().any():
        errors.append("instrument_id must be unique")
    if "ticker" in df.columns and df["ticker"].isna().any():
        errors.append("ticker cannot be missing")
    return (len(errors) == 0, errors)


def validate_weights(
    holdings: pd.DataFrame,
    allow_short: bool = False,
    minmax: pd.DataFrame | None = None,
) -> Tuple[bool, list[str]]:
    errors: list[str] = []
    if holdings.empty:
        return False, ["Holdings cannot be empty"]
    total = holdings["weight"].sum()
    if abs(total - 100.0) > WEIGHT_TOLERANCE:
        errors.append(f"Weight sum must be 100, got {total:.4f}")
    if not allow_short and (holdings["weight"] < 0).any():
        errors.append("Negative weights are not allowed")

    if minmax is not None and not minmax.empty:
        merged = holdings.merge(minmax[["ticker", "min_weight", "max_weight"]], on="ticker", how="left")
        bad_min = merged[(merged["min_weight"].notna()) & (merged["weight"] < merged["min_weight"])]
        bad_max = merged[(merged["max_weight"].notna()) & (merged["weight"] > merged["max_weight"])]
        if not bad_min.empty:
            errors.append("Some holdings are below min_weight bounds")
        if not bad_max.empty:
            errors.append("Some holdings are above max_weight bounds")

    return (len(errors) == 0, errors)


def version_diff(old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    old = old_df[["ticker", "weight"]].rename(columns={"weight": "old_weight"})
    new = new_df[["ticker", "weight"]].rename(columns={"weight": "new_weight"})
    diff = old.merge(new, on="ticker", how="outer")
    diff["change"] = diff["new_weight"].fillna(0) - diff["old_weight"].fillna(0)
    return diff.sort_values("change", ascending=False)
