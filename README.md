# Cross-Asset Market Monitor + Basket Builder (No Bloomberg)

A Streamlit app for:
- Cross-asset monitoring (yfinance)
- Macro monitoring (FRED)
- Restricted universe management (desk snapshot model)
- Basket creation/edit/versioning/CSV import-export
- Signals + explainable suggestions
- HTML report preview + download

## 1) Create a public GitHub repo (Web UI only)
1. Go to GitHub → **New repository**.
2. Name it (for example: `basket-builder`).
3. Choose **Public**.
4. Click **Create repository**.

## 2) Upload files (Web UI only)
1. In your new repo, click **Add file** → **Upload files**.
2. Drag-and-drop all project files/folders from this package.
3. Click **Commit changes**.

## 3) Deploy to Streamlit Community Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io).
2. Click **New app**.
3. Select your GitHub repo and branch.
4. Set **Main file path** = `app.py`.
5. Click **Deploy**.

## 4) Add secrets in Streamlit Cloud
1. In deployed app settings, open **Secrets**.
2. Paste keys from `.streamlit/secrets.toml.example` with your values.
3. Required for macro dashboard:
   - `FRED_API_KEY`
4. Optional SMTP keys are placeholders only (email sending remains OFF by default).

## 5) How to use the app
1. **Home**: verify system status and FRED key availability.
2. **Universe**:
   - Upload your desk CSV OR load demo universe.
   - Creates a new **Universe Snapshot ID**.
   - Filter/browse instruments and download snapshot CSV.
3. **Baskets**:
   - Create basket tied to a snapshot.
   - Add holdings from eligible universe tickers.
   - Save versions (with validation and constraints).
   - Compare versions, import/export CSV, and inspect basket health.
4. **Dashboards**:
   - Performance, correlation, macro, regime, and signals.
   - Each section includes a “What this means” interpretation.
5. **Signals & Suggestions**:
   - Review composite scores.
   - Save constraints.
   - Apply suggestion only by explicit click (creates new version).
6. **Report Builder**:
   - Edit narrative blocks, reorder sections, preview HTML.
   - Download report as `.html`.

## 6) Universe CSV schema
Required columns:
- `instrument_id` (unique string)
- `ticker`
- `name`
- `asset_class` (Equity / Rates / Credit / Commodities / FX / Alternatives)
- `region`
- `currency`
- `eligible` (TRUE/FALSE)

Optional columns:
- `isin`
- `min_weight`
- `max_weight`
- `notes`

## 7) Persistence note (Streamlit Cloud)
Data is stored in local SQLite (`basket_builder.db`). On Streamlit Community Cloud, filesystem persistence may be ephemeral across restarts.

Recommended workflow:
- Export universe snapshots and basket CSV versions regularly.
- Re-import on restart if needed.

## 8) Troubleshooting
- **Ticker not found (yfinance):** use valid Yahoo Finance symbols (e.g., `SPY`, `AGG`, `GLD`).
- **FRED key missing:** app still runs; macro dashboard shows friendly warning.
- **Cache stale:** in Streamlit app menu, use **Clear cache** and rerun.
- **Partial data failures:** app continues rendering available data and skips failed tickers/series.

## Security and privacy
- No secrets are hardcoded.
- FRED key is read only from `st.secrets["FRED_API_KEY"]`.
- Do not commit `.streamlit/secrets.toml`.
