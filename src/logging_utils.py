"""Logging setup and error display utilities."""
from __future__ import annotations

import logging
import streamlit as st


def get_logger(name: str) -> logging.Logger:
    """Return logger with a consistent format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def ui_error(message: str, exc: Exception | None = None) -> None:
    """Show a user-friendly error banner without exposing secrets."""
    if exc:
        st.error(f"⚠️ {message}: {type(exc).__name__}")
    else:
        st.error(f"⚠️ {message}")
