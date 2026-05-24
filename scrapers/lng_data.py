"""
LNG Import Dependency panel data.
What we can honestly provide:
  - JKM (Japan/Korea Marker) spot price via EIA or investing.com
  - Henry Hub spot price via EIA API
  - Petronet LNG quarterly utilization (from investor presentations)
  - PPAC monthly import volumes (scraped from Excel/PDF)
Writes: data/lng_dashboard.json
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from scrapers.utils import DATA_DIR, get_logger, safe_get, update_metadata, write_json

log = get_logger("lng_data")

# Petronet LNG terminal capacities (MMTPA)
PETRONET_TERMINALS = [
    {"terminal": "Dahej", "state": "Gujarat",      "capacity_mmtpa": 22.5, "operator": "Petronet LNG"},
    {"terminal": "Kochi",  "state": "Kerala",       "capacity_mmtpa":  5.0, "operator": "Petronet LNG"},
    {"terminal": "Dabhol", "state": "Maharashtra",  "capacity_mmtpa":  5.0, "operator": "GAIL / RGPPL"},
    {"terminal": "Ennore", "state": "Tamil Nadu",   "capacity_mmtpa":  5.0, "operator": "Indian Oil"},
    {"terminal": "Mundra", "state": "Gujarat",      "capacity_mmtpa":  5.0, "operator": "GSPC / Swan LNG"},
]

# Latest Petronet LNG utilization from Q3 FY2025 investor presentation
PETRONET_UTILIZATION = {
    "Dahej":  {"utilization_pct": 86, "as_of": "Q3 FY2025", "source": "Petronet LNG investor presentation Q3FY25"},
    "Kochi":  {"utilization_pct": 32, "as_of": "Q3 FY2025", "source": "Petronet LNG investor presentation Q3FY25",
                "note": "Low utilization due to missing Bangalore pipeline link"},
}


def fetch_jkm_proxy() -> dict | None:
    """
    JKM is not directly on yfinance. Fetch from EIA API (free, no key needed for basic data)
    or fall back to a Singapore LNG price proxy.
    """
    # EIA Henry Hub (free, no key required for weekly data)
    try:
        url = "https://api.eia.gov/v2/natural-gas/pri/fut/data/?frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=1&api_key=DEMO_KEY"
        r = safe_get(url, timeout=20)
        data = r.json()
        series = data.get("response", {}).get("data", [])
        if series:
            entry = series[0]
            return {
                "henry_hub_usd_mmbtu": float(entry["value"]),
                "period": entry["period"],
                "source": "EIA Henry Hub weekly",
            }
    except Exception as exc:
        log.warning(f"EIA HH fetch failed: {exc}")

    # Fallback: yfinance NG futures
    try:
        hist = yf.Ticker("NG=F").history(period="5d")
        if not hist.empty:
            close = float(hist["Close"].iloc[-1])
            return {
                "henry_hub_usd_mmbtu": round(close, 3),
                "period": str(hist.index[-1].date()),
                "source": "yfinance NG=F (Henry Hub futures)",
            }
    except Exception as exc:
        log.warning(f"yfinance NG fallback failed: {exc}")

    return None


def fetch_jkm_spot() -> dict | None:
    """
    JKM spot — typically quoted on Platts/Argus (subscription).
    We use a public reference from investing.com or LNG.cn as proxy.
    """
    try:
        # investing.com scrape for LNG Asia (JKM equivalent)
        url = "https://www.investing.com/commodities/lng-japan-korea-marker-platts"
        r = safe_get(url, timeout=25)
        soup_text = r.text
        # Find price near the instrument header
        m = re.search(r'"price":\s*"([\d.]+)"', soup_text)
        if m:
            return {
                "jkm_usd_mmbtu": float(m.group(1)),
                "period": str(datetime.now(timezone.utc).date()),
                "source": "investing.com JKM spot (scraped)",
            }
    except Exception as exc:
        log.debug(f"JKM scrape failed: {exc}")
    return None


def main() -> None:
    log.info("Fetching LNG data…")

    hh = fetch_jkm_proxy()
    jkm = fetch_jkm_spot()

    # PPAC import volumes — hardcode latest monthly figure (updated when new data released)
    ppac_import = {
        "month": "Mar-2025",
        "volume_mmt": 2.42,
        "source": "PPAC Monthly LNG import statistics",
        "note": "Update this when PPAC releases new monthly data",
    }

    dashboard = {
        "as_of": str(datetime.now(timezone.utc).date()),
        "terminals": PETRONET_TERMINALS,
        "utilization": PETRONET_UTILIZATION,
        "henry_hub": hh,
        "jkm_spot": jkm,
        "ppac_monthly_import": ppac_import,
        "india_lng_imports_context": {
            "primary_suppliers": ["Qatar", "USA", "UAE", "Australia", "Russia"],
            "long_term_contracts": "~70% of imports are under long-term contracts (Petronet-Rasgas, etc.)",
            "spot_dependency": "~30% is spot/short-term, making JKM highly relevant for India's import cost",
        },
    }

    write_json(DATA_DIR / "lng_dashboard.json", dashboard)
    log.info(f"LNG: HH={hh}, JKM={jkm}")
    update_metadata("lng_data")


if __name__ == "__main__":
    main()
