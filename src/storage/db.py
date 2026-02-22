"""SQLite storage layer for universe snapshots, baskets, versions and audit."""
from __future__ import annotations

import sqlite3
from datetime import datetime
import pandas as pd

from src.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS universe_snapshots (
            snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            source TEXT NOT NULL,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS universe_instruments (
            snapshot_id INTEGER NOT NULL,
            instrument_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            name TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            region TEXT NOT NULL,
            currency TEXT NOT NULL,
            eligible INTEGER NOT NULL,
            isin TEXT,
            min_weight REAL,
            max_weight REAL,
            notes TEXT,
            PRIMARY KEY (snapshot_id, instrument_id)
        );

        CREATE TABLE IF NOT EXISTS baskets (
            basket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            basket_name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            universe_snapshot_id INTEGER NOT NULL,
            allow_short INTEGER NOT NULL DEFAULT 0,
            max_holdings INTEGER NOT NULL DEFAULT 50
        );

        CREATE TABLE IF NOT EXISTS basket_versions (
            version_id INTEGER PRIMARY KEY AUTOINCREMENT,
            basket_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            comment TEXT
        );

        CREATE TABLE IF NOT EXISTS basket_holdings (
            version_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            weight REAL NOT NULL,
            notes TEXT,
            PRIMARY KEY (version_id, ticker)
        );

        CREATE TABLE IF NOT EXISTS basket_constraints (
            basket_id INTEGER PRIMARY KEY,
            max_single_name REAL,
            max_asset_class REAL
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            event_time TEXT NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def log_event(event_type: str, details: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO audit_log(event_time,event_type,details) VALUES (?,?,?)",
        (datetime.utcnow().isoformat(), event_type, details),
    )
    conn.commit()
    conn.close()


def create_universe_snapshot(df: pd.DataFrame, source: str, note: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO universe_snapshots(created_at,source,note) VALUES (?,?,?)",
        (datetime.utcnow().isoformat(), source, note),
    )
    snapshot_id = cur.lastrowid
    payload = df.copy()
    payload["eligible"] = payload["eligible"].astype(bool).astype(int)
    payload["snapshot_id"] = snapshot_id
    cols = [
        "snapshot_id",
        "instrument_id",
        "ticker",
        "name",
        "asset_class",
        "region",
        "currency",
        "eligible",
        "isin",
        "min_weight",
        "max_weight",
        "notes",
    ]
    payload = payload.reindex(columns=cols)
    payload.to_sql("universe_instruments", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    log_event("universe_snapshot_created", f"snapshot_id={snapshot_id}")
    return int(snapshot_id)


def list_universe_snapshots() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM universe_snapshots ORDER BY snapshot_id DESC", conn)
    conn.close()
    return df


def get_universe(snapshot_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM universe_instruments WHERE snapshot_id=? ORDER BY ticker", conn, params=(snapshot_id,)
    )
    conn.close()
    return df


def create_basket(name: str, description: str, universe_snapshot_id: int, allow_short: bool, max_holdings: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO baskets(basket_name,description,created_at,universe_snapshot_id,allow_short,max_holdings)
           VALUES (?,?,?,?,?,?)""",
        (name, description, datetime.utcnow().isoformat(), universe_snapshot_id, int(allow_short), max_holdings),
    )
    basket_id = cur.lastrowid
    conn.commit()
    conn.close()
    log_event("basket_created", f"basket_id={basket_id}")
    return int(basket_id)


def list_baskets() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM baskets ORDER BY basket_id DESC", conn)
    conn.close()
    return df


def create_basket_version(basket_id: int, holdings: pd.DataFrame, comment: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(version_number),0)+1 FROM basket_versions WHERE basket_id=?", (basket_id,))
    version_number = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO basket_versions(basket_id,version_number,created_at,comment) VALUES (?,?,?,?)",
        (basket_id, version_number, datetime.utcnow().isoformat(), comment),
    )
    version_id = cur.lastrowid
    payload = holdings[["ticker", "weight", "notes"]].copy()
    payload["version_id"] = version_id
    payload = payload[["version_id", "ticker", "weight", "notes"]]
    payload.to_sql("basket_holdings", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    log_event("basket_version_created", f"basket_id={basket_id},version_id={version_id}")
    return int(version_id)


def list_versions(basket_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM basket_versions WHERE basket_id=? ORDER BY version_number DESC", conn, params=(basket_id,)
    )
    conn.close()
    return df


def get_holdings(version_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM basket_holdings WHERE version_id=? ORDER BY weight DESC", conn, params=(version_id,))
    conn.close()
    return df


def save_constraints(basket_id: int, max_single_name: float, max_asset_class: float) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO basket_constraints(basket_id,max_single_name,max_asset_class)
           VALUES (?,?,?)
           ON CONFLICT(basket_id) DO UPDATE SET
           max_single_name=excluded.max_single_name,
           max_asset_class=excluded.max_asset_class""",
        (basket_id, max_single_name, max_asset_class),
    )
    conn.commit()
    conn.close()


def get_constraints(basket_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM basket_constraints WHERE basket_id=?", conn, params=(basket_id,))
    conn.close()
    return df


def reset_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    for table in [
        "universe_snapshots",
        "universe_instruments",
        "baskets",
        "basket_versions",
        "basket_holdings",
        "basket_constraints",
        "audit_log",
    ]:
        cur.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
