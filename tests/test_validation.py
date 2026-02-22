import pandas as pd

from src.analytics.validation import validate_universe_schema, validate_weights


def test_universe_schema_ok():
    df = pd.DataFrame(
        {
            "instrument_id": ["a"],
            "ticker": ["SPY"],
            "name": ["S&P"],
            "asset_class": ["Equity"],
            "region": ["US"],
            "currency": ["USD"],
            "eligible": [True],
        }
    )
    ok, errors = validate_universe_schema(df)
    assert ok
    assert errors == []


def test_weight_sum_fails():
    h = pd.DataFrame({"ticker": ["SPY", "AGG"], "weight": [50.0, 40.0]})
    ok, errors = validate_weights(h)
    assert not ok
    assert "Weight sum must be 100" in errors[0]
