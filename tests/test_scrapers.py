"""
Validates data file shape and freshness after each scraper run.
Run: pytest tests/test_scrapers.py -v
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

DATA = Path(__file__).parent.parent / "data"


def load_json(filename: str) -> dict:
    p = DATA / filename
    assert p.exists(), f"Missing data file: {filename}"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data


def load_csv(filename: str) -> pd.DataFrame:
    p = DATA / filename
    assert p.exists(), f"Missing CSV: {filename}"
    return pd.read_csv(p)


# ─────────────────────────────── SPR ────────────────────────────────────────

def test_spr_status_schema():
    d = load_json("spr_status.json")
    assert "fill_mmt" in d, "Missing fill_mmt"
    assert "fill_pct" in d, "Missing fill_pct"
    assert "days_of_import_cover" in d, "Missing days_of_import_cover"
    assert "sites" in d and isinstance(d["sites"], list), "Missing or invalid sites"
    assert d["fill_pct"] >= 0 and d["fill_pct"] <= 100, "fill_pct out of range"
    assert d["fill_mmt"] > 0, "fill_mmt must be positive"


# ─────────────────────────────── Fuel prices ─────────────────────────────────

def test_fuel_prices_latest_schema():
    d = load_json("fuel_prices_latest.json")
    assert "as_of" in d, "Missing as_of"
    assert "rows" in d, "Missing rows"


def test_fuel_prices_has_content():
    d = load_json("fuel_prices_latest.json")
    rows = d.get("rows", [])
    assert len(rows) >= 1, "fuel_prices_latest has zero rows"
    for row in rows:
        assert "city" in row, f"Row missing 'city': {row}"
        # petrol price should be a plausible India range (₹70–₹130/L)
        p = row.get("petrol_per_litre")
        if p is not None:
            assert 70 <= p <= 135, f"Suspicious petrol price {p} for {row.get('city')}"


def test_fuel_prices_history_exists():
    p = DATA / "fuel_prices_history.csv"
    if p.exists():
        df = pd.read_csv(p)
        assert "city" in df.columns
        assert "petrol_per_litre" in df.columns


# ─────────────────────────────── Crude ───────────────────────────────────────

def test_crude_latest_schema():
    d = load_json("crude_latest.json")
    assert "as_of" in d, "Missing as_of"
    assert "prices_usd_bbl" in d, "Missing prices_usd_bbl"
    prices = d["prices_usd_bbl"]
    assert "brent" in prices, "Missing brent price"
    brent = prices["brent"]
    if brent is not None:
        assert 20 <= brent <= 250, f"Brent price implausible: {brent}"


def test_crude_history_exists():
    df = load_csv("crude_benchmarks.csv")
    assert "symbol" in df.columns
    assert "close" in df.columns
    assert "date" in df.columns
    assert len(df) >= 1


# ─────────────────────────────── Markets ─────────────────────────────────────

def test_markets_latest_schema():
    d = load_json("markets_latest.json")
    assert "latest" in d, "Missing 'latest'"
    latest = d["latest"]
    assert "nifty50" in latest or "nifty_it" in latest, "Expected nifty50 or nifty_it"


def test_markets_nifty_plausible():
    d = load_json("markets_latest.json")
    nifty = d.get("latest", {}).get("nifty50")
    if nifty is not None:
        assert 5000 <= nifty <= 50000, f"Nifty level implausible: {nifty}"


# ─────────────────────────────── LNG ─────────────────────────────────────────

def test_lng_dashboard_schema():
    d = load_json("lng_dashboard.json")
    assert "terminals" in d, "Missing terminals"
    assert "utilization" in d, "Missing utilization"
    assert isinstance(d["terminals"], list)
    assert len(d["terminals"]) >= 3


# ─────────────────────────────── Attribution ─────────────────────────────────

def test_attribution_latest_schema():
    d = load_json("attribution_latest.json")
    assert "r_squared" in d, "Missing r_squared"
    assert "today_contributions_pct" in d, "Missing today_contributions_pct"
    r2 = d["r_squared"]
    assert 0.0 <= r2 <= 1.0, f"R² out of range: {r2}"


def test_attribution_contributions_sum():
    d = load_json("attribution_latest.json")
    contrib = d.get("today_contributions_pct", {})
    nifty_ret = d.get("nifty_return_today_pct", 0)
    total = sum(contrib.values())
    # Sum of contributions should approximately equal nifty return
    assert abs(total - nifty_ret) < 0.1, (
        f"Contributions {total:.4f} don't sum to Nifty return {nifty_ret:.4f}"
    )


# ─────────────────────────────── Metadata ────────────────────────────────────

def test_metadata_exists():
    d = load_json("metadata.json")
    assert len(d) >= 1, "metadata.json is empty"


def test_metadata_freshness():
    """At least one source should have been updated within the last 2 days."""
    d = load_json("metadata.json")
    now = datetime.now(timezone.utc)
    fresh = [
        k for k, v in d.items()
        if v.get("updated_at") and
        (now - datetime.fromisoformat(v["updated_at"].replace("Z", "+00:00"))) < timedelta(days=2)
    ]
    assert len(fresh) >= 1, "No data source updated in the last 2 days"
