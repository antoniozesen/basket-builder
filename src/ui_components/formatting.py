"""Number formatting helpers for UI consistency."""
from __future__ import annotations


def fmt_pct(x: float) -> str:
    return f"{x:.2f}%"


def fmt_level(x: float, decimals: int = 2) -> str:
    return f"{x:.{decimals}f}"
