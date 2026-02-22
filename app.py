from __future__ import annotations

from datetime import date
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics.metrics import (
    compute_returns,
    cumulative_returns,
    hhi,
    max_drawdown,
    rolling_sharpe,
    rolling_vol,
    top5_weight,
)
from src.analytics.signals import composite_signal, suggest_reweight
from src.analytics.validation import validate_universe_schema, validate_weights, version_diff
from src.config import APP_TITLE, DEFAULT_END_DATE, DEFAULT_FRED_SERIES, DEFAULT_START_DATE, MAX_HOLDINGS_DEFAULT
from src.data.fred_provider import fetch_fred_series
from src.data.yfinance_provider import data_health, fetch_prices, quick_ticker_check
from src.logging_utils import ui_error
from src.reporting.html_report import build_report_html, table_to_html
from src.storage.db import (
    create_basket,
    create_basket_version,
    create_universe_snapshot,
    get_constraints,
    get_holdings,
    get_universe,
    init_db,
    list_baskets,
    list_universe_snapshots,
    list_versions,
    reset_db,
    save_constraints,
)

st.set_page_config(page_title=APP_TITLE, layout="wide")
init_db()

if "global_start" not in st.session_state:
    st.session_state.global_start = DEFAULT_START_DATE
if "global_end" not in st.session_state:
    st.session_state.global_end = DEFAULT_END_DATE

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Home", "Universe", "Baskets", "Dashboards", "Signals & Suggestions", "Report Builder", "Settings / Help"],
)

st.sidebar.subheader("Global Date Range")
st.session_state.global_start = st.sidebar.date_input("Start", st.session_state.global_start)
st.session_state.global_end = st.sidebar.date_input("End", st.session_state.global_end)


def home_page() -> None:
    st.title(APP_TITLE)
    st.caption("Institutional-style monitor using free data (FRED + yfinance), no Bloomberg.")
    st.markdown("### System status")
    fred_ok = bool(st.secrets.get("FRED_API_KEY", ""))
    st.write(f"- FRED key configured: {'✅' if fred_ok else '❌ (macro page will degrade gracefully)'}")
    st.write("- Database: SQLite in app folder")
    st.info("Use the sidebar to upload a universe, build baskets, and generate reports.")


def universe_page() -> None:
    st.header("Universe Manager")
    st.write("Upload desk-approved universe CSV or use the built-in demo universe.")

    with st.expander("CSV schema help"):
        st.write("Required: instrument_id, ticker, name, asset_class, region, currency, eligible")

    up = st.file_uploader("Upload Universe CSV", type=["csv"])
    col1, col2 = st.columns(2)
    if col1.button("Load built-in demo universe"):
        demo = pd.read_csv("data/demo_universe.csv")
        ok, errors = validate_universe_schema(demo)
        if ok:
            sid = create_universe_snapshot(demo, source="demo_csv", note="demo load")
            st.success(f"Demo snapshot created: {sid}")
        else:
            for err in errors:
                st.error(err)

    if up is not None:
        df = pd.read_csv(up)
        ok, errors = validate_universe_schema(df)
        if not ok:
            for err in errors:
                st.error(err)
        else:
            checks = {t: quick_ticker_check(t) for t in df["ticker"].astype(str).tolist()[:30]}
            st.write("Ticker quick-check sample:", checks)
            sid = create_universe_snapshot(df, source="upload")
            st.success(f"Universe snapshot created: {sid}")

    snaps = list_universe_snapshots()
    if snaps.empty:
        st.warning("No snapshots yet.")
        return

    chosen = st.selectbox("Select Snapshot", snaps["snapshot_id"].tolist())
    uni = get_universe(int(chosen))
    c1, c2, c3 = st.columns(3)
    af = c1.multiselect("asset_class", sorted(uni["asset_class"].dropna().unique().tolist()))
    rg = c2.multiselect("region", sorted(uni["region"].dropna().unique().tolist()))
    el = c3.selectbox("eligible", ["all", "true", "false"])
    filt = uni.copy()
    if af:
        filt = filt[filt["asset_class"].isin(af)]
    if rg:
        filt = filt[filt["region"].isin(rg)]
    if el != "all":
        filt = filt[filt["eligible"] == (1 if el == "true" else 0)]
    st.dataframe(filt, use_container_width=True)
    st.download_button("Download Universe Snapshot CSV", filt.to_csv(index=False), file_name=f"universe_{chosen}.csv")


def baskets_page() -> None:
    st.header("Basket Builder")
    snaps = list_universe_snapshots()
    if snaps.empty:
        st.warning("Create a universe snapshot first.")
        return
    sid = st.selectbox("Universe Snapshot", snaps["snapshot_id"].tolist(), key="basket_sid")
    uni = get_universe(int(sid))
    allowed = uni[uni["eligible"] == 1]["ticker"].tolist()

    with st.expander("Create new basket"):
        name = st.text_input("Basket Name")
        desc = st.text_area("Description")
        allow_short = st.checkbox("Allow short", value=False)
        max_hold = st.number_input("Max holdings", 1, 200, MAX_HOLDINGS_DEFAULT)
        if st.button("Create Basket") and name:
            bid = create_basket(name, desc, int(sid), allow_short, int(max_hold))
            st.success(f"Created basket {bid}")

    baskets = list_baskets()
    if baskets.empty:
        st.info("No baskets yet.")
        return
    bid = st.selectbox("Select Basket", baskets["basket_id"].tolist())
    row = baskets[baskets["basket_id"] == bid].iloc[0]
    st.write(f"Universe snapshot bound to basket: **{row['universe_snapshot_id']}**")

    tickers = st.multiselect("Tickers", allowed)
    weights = {}
    notes = {}
    for t in tickers:
        c1, c2 = st.columns([1, 2])
        weights[t] = c1.number_input(f"Weight {t}", value=0.0, step=0.5, key=f"w_{t}")
        notes[t] = c2.text_input(f"Notes {t}", key=f"n_{t}")

    if st.button("Save as new version") and tickers:
        hold = pd.DataFrame({"ticker": tickers, "weight": [weights[t] for t in tickers], "notes": [notes[t] for t in tickers]})
        minmax = uni[["ticker", "min_weight", "max_weight"]].copy() if "min_weight" in uni.columns else None
        ok, errs = validate_weights(hold, allow_short=bool(row["allow_short"]), minmax=minmax)
        if len(hold) > int(row["max_holdings"]):
            errs.append("Too many holdings")
            ok = False
        if not ok:
            for e in errs:
                st.error(e)
        else:
            vid = create_basket_version(int(bid), hold)
            st.success(f"Saved version {vid}")

    versions = list_versions(int(bid))
    if versions.empty:
        return
    st.subheader("Versions")
    st.dataframe(versions, use_container_width=True)
    vsel = st.selectbox("Version", versions["version_id"].tolist())
    h = get_holdings(int(vsel))
    st.dataframe(h, use_container_width=True)
    st.download_button("Download Basket CSV", h.to_csv(index=False), file_name=f"basket_{bid}_v{vsel}.csv")

    up = st.file_uploader("Import Basket CSV", type=["csv"], key="import_basket")
    if up is not None and st.button("Import as new version"):
        imp = pd.read_csv(up)
        ok, errs = validate_weights(imp, allow_short=bool(row["allow_short"]))
        if ok:
            vid = create_basket_version(int(bid), imp)
            st.success(f"Imported as version {vid}")
        else:
            for e in errs:
                st.error(e)

    if len(versions) >= 2:
        v1 = versions["version_id"].iloc[1]
        old_df = get_holdings(int(v1))
        new_df = get_holdings(int(vsel))
        st.subheader("Version Diff")
        st.dataframe(version_diff(old_df, new_df), use_container_width=True)

    st.subheader("Basket Health")
    prices = fetch_prices(h["ticker"].tolist(), str(st.session_state.global_start), str(st.session_state.global_end))
    health = data_health(prices)
    st.dataframe(health, use_container_width=True)
    st.write(f"HHI: {hhi(h['weight']):.3f} | Top-5 Weight: {top5_weight(h['weight']):.2f}%")


def dashboards_page() -> None:
    st.header("Dashboards")
    baskets = list_baskets()
    if baskets.empty:
        st.warning("Create basket and version first.")
        return
    bid = st.selectbox("Basket", baskets["basket_id"].tolist(), key="dash_b")
    versions = list_versions(int(bid))
    if versions.empty:
        st.warning("No versions for basket.")
        return
    vid = int(versions.iloc[0]["version_id"])
    h = get_holdings(vid)
    tickers = h["ticker"].tolist()
    prices = fetch_prices(tickers, str(st.session_state.global_start), str(st.session_state.global_end))
    if prices.empty:
        st.warning("No market data available for holdings.")
        return
    rets = compute_returns(prices)

    st.subheader("1) Performance")
    w = h.set_index("ticker")["weight"] / 100.0
    basket_ret = rets.mul(w, axis=1).sum(axis=1)
    perf = cumulative_returns(pd.DataFrame({"Basket": basket_ret}))
    bench = fetch_prices(["SPY", "AGG", "GLD"], str(st.session_state.global_start), str(st.session_state.global_end))
    if not bench.empty:
        perf = perf.join(cumulative_returns(compute_returns(bench)), how="left")
    st.plotly_chart(px.line(perf, title="Cumulative Returns"), use_container_width=True)
    st.plotly_chart(px.line(rolling_vol(pd.DataFrame({"Basket": basket_ret})), title="Rolling Volatility"), use_container_width=True)
    st.write(f"Max drawdown: {max_drawdown(basket_ret):.2%}")
    st.markdown("**What this means**\n- Compare trend vs benchmarks.\n- Rising volatility warns about risk budget usage.")

    st.subheader("2) Correlation")
    corr = rets.corr()
    st.plotly_chart(px.imshow(corr, text_auto=True, aspect="auto", title="Correlation Matrix"), use_container_width=True)
    st.markdown("**What this means**\n- Higher correlation reduces diversification.\n- Check pair concentration risk.")

    st.subheader("3) Macro (FRED)")
    fred = fetch_fred_series(DEFAULT_FRED_SERIES, str(st.session_state.global_start), str(st.session_state.global_end))
    if fred.empty:
        st.info("FRED data unavailable. Add FRED_API_KEY in Streamlit secrets.")
    else:
        fig = go.Figure()
        for col in fred.columns:
            if col != "Recession":
                fig.add_trace(go.Scatter(x=fred.index, y=fred[col], name=col, yaxis="y"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**What this means**\n- Macro backdrop can explain cross-asset performance.\n- Watch inflation/rates mix for regime shifts.")

    st.subheader("4) Regime")
    regime = "Risk-on" if basket_ret.tail(63).mean() > 0 else "Risk-off"
    conf = min(abs(basket_ret.tail(63).mean()) * 1000, 99)
    st.metric("Current regime", regime, f"Confidence {conf:.1f}%")

    st.subheader("5) Signals")
    sig = composite_signal(prices)
    st.dataframe(sig, use_container_width=True)
    st.markdown("**What this means**\n- Positive scores support overweight.\n- Negative scores indicate weakening trend/momentum.")


def signals_page() -> None:
    st.header("Signals & Suggestions")
    baskets = list_baskets()
    if baskets.empty:
        st.warning("Create basket first.")
        return
    bid = st.selectbox("Basket", baskets["basket_id"].tolist(), key="sig_b")
    versions = list_versions(int(bid))
    if versions.empty:
        return
    h = get_holdings(int(versions.iloc[0]["version_id"]))
    prices = fetch_prices(h["ticker"].tolist(), str(st.session_state.global_start), str(st.session_state.global_end))
    if prices.empty:
        return
    scores = composite_signal(prices)
    st.dataframe(scores, use_container_width=True)

    st.subheader("Constraints Editor")
    c = get_constraints(int(bid))
    max_single = float(c["max_single_name"].iloc[0]) if not c.empty else 25.0
    max_class = float(c["max_asset_class"].iloc[0]) if not c.empty else 60.0
    n1, n2 = st.columns(2)
    max_single = n1.number_input("Max single name (%)", 1.0, 100.0, max_single)
    max_class = n2.number_input("Max asset class (%)", 1.0, 100.0, max_class)
    if st.button("Save Constraints"):
        save_constraints(int(bid), max_single, max_class)
        st.success("Constraints saved")

    sug = suggest_reweight(h, scores)
    st.subheader("Suggested Reweight")
    st.dataframe(sug, use_container_width=True)
    st.caption("Suggestion is explainable via score and delta columns. Not auto-applied.")

    if st.button("Apply suggestion as NEW version"):
        newh = h.merge(sug[["ticker", "new_weight"]], on="ticker")
        out = pd.DataFrame({"ticker": newh["ticker"], "weight": newh["new_weight"], "notes": "suggested"})
        create_basket_version(int(bid), out, comment="signal suggestion")
        st.success("New version created from suggestion")


def report_page() -> None:
    st.header("Report Builder (HTML Preview)")
    baskets = list_baskets()
    if baskets.empty:
        return
    bid = st.selectbox("Basket", baskets["basket_id"].tolist(), key="rep_b")
    versions = list_versions(int(bid))
    if versions.empty:
        return
    h = get_holdings(int(versions.iloc[0]["version_id"]))
    narrative_summary = st.text_area("Summary narrative", "Market regime appears mixed with selective risk-on signals.")
    notes = st.text_area("Custom News / Notes", "")
    order = st.multiselect(
        "Section order",
        ["Summary", "Basket Overview", "Holdings", "Custom Notes"],
        default=["Summary", "Basket Overview", "Holdings", "Custom Notes"],
    )

    sections: list[tuple[str, str]] = []
    for s in order:
        if s == "Summary":
            sections.append(("Summary", narrative_summary))
        elif s == "Basket Overview":
            sections.append(("Basket Overview", f"Basket ID: {bid}<br/>Current Version: {versions.iloc[0]['version_number']}"))
        elif s == "Holdings":
            sections.append(("Holdings", table_to_html(h, "Current Holdings")))
        elif s == "Custom Notes":
            sections.append(("Custom Notes", notes))

    html = build_report_html(sections)
    st.subheader("Preview")
    st.components.v1.html(html, height=500, scrolling=True)
    st.download_button("Download HTML Report", html.encode("utf-8"), file_name=f"basket_report_{bid}.html")
    st.info("Email sending is intentionally OFF by default. Add SMTP secrets and custom workflow later if required.")


def settings_page() -> None:
    st.header("Settings / Help")
    st.write("This app stores data in SQLite in the app folder. On Streamlit Cloud, storage can be ephemeral.")
    st.write("Best practice: regularly export Universe + Basket CSV backups and re-import as needed.")
    dev_mode = st.toggle("Dev mode")
    if dev_mode and st.button("Reset demo DB"):
        reset_db()
        st.success("Database reset")
    with st.expander("Troubleshooting"):
        st.markdown(
            """
            - **Ticker not found**: verify symbol in Yahoo Finance format.
            - **Missing FRED key**: add `FRED_API_KEY` in Streamlit secrets.
            - **Cache issues**: use Settings → Clear cache in Streamlit app menu.
            """
        )


try:
    if page == "Home":
        home_page()
    elif page == "Universe":
        universe_page()
    elif page == "Baskets":
        baskets_page()
    elif page == "Dashboards":
        dashboards_page()
    elif page == "Signals & Suggestions":
        signals_page()
    elif page == "Report Builder":
        report_page()
    else:
        settings_page()
except Exception as exc:
    ui_error("Unexpected application error", exc)
