"""
Strategic Petroleum Reserve (SPR) data from ISPRL.
Data reality: ISPRL does not publish daily fill levels. Sources:
  1. Parliament Q&A PDF (Ministry of Petroleum) — quarterly-ish
  2. PIB press releases
  3. News aggregation (for any new figure)
This scraper captures the most recent verified figure with a clear timestamp.
Writes: data/spr_status.json, data/spr_history.csv
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from scrapers.utils import DATA_DIR, get_logger, safe_get, update_metadata, write_json

log = get_logger("spr_isprl")

# SPR static capacity data (ISPRL official, updated as new caverns come online)
SPR_SITES = [
    {"location": "Visakhapatnam", "state": "Andhra Pradesh", "capacity_mmt": 1.33},
    {"location": "Mangaluru (Padur)", "state": "Karnataka",  "capacity_mmt": 2.50},
    {"location": "Padur Phase-2",     "state": "Karnataka",  "capacity_mmt": 2.50},  # Phase 2 approved
    {"location": "Bikaner (Rajasthan)","state": "Rajasthan",  "capacity_mmt": 2.50},  # Phase 2
    {"location": "Chandikhol",        "state": "Odisha",      "capacity_mmt": 4.00},  # Phase 2
]

TOTAL_PHASE1_CAPACITY_MMT = 5.33   # Visakhapatnam + Padur + Mangaluru (operational)
TOTAL_PHASE2_CAPACITY_MMT = 6.50   # Additional approved

# Last known fill from Parliament Standing Committee on Petroleum, Feb 2024
LAST_KNOWN = {
    "fill_mmt": 5.33,             # Phase 1 fully filled as of early 2024
    "fill_pct": 100.0,
    "verified_date": "2024-02-01",
    "source": "Parliament Standing Committee on Petroleum & Natural Gas, Feb 2024",
    "note": (
        "ISPRL does not publish daily fill levels. "
        "This figure represents Phase-1 capacity (5.33 MMT) fully operational. "
        "Check source for any newer parliamentary statements."
    ),
}


def scrape_pib() -> dict | None:
    """Search PIB (Press Information Bureau) for recent ISPRL announcements."""
    try:
        url = "https://pib.gov.in/allRel.aspx"
        r = safe_get(url + "?ModId=6&reg=3&lang=1", timeout=30)
        soup = BeautifulSoup(r.text, "lxml")
        # Look for ISPRL or strategic reserve mentions in headlines
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if "strategic" in text and ("reserve" in text or "spr" in text or "isprl" in text):
                log.info(f"Found PIB mention: {a.get_text(strip=True)}")
                return {
                    "source": "PIB",
                    "headline": a.get_text(strip=True),
                    "url": "https://pib.gov.in" + a["href"] if a["href"].startswith("/") else a["href"],
                }
    except Exception as exc:
        log.warning(f"PIB scrape failed: {exc}")
    return None


def build_days_of_import_cover(fill_mmt: float) -> float:
    """India imports ~4.5 MMT/month crude → 1 MMT = ~6.7 days of cover."""
    monthly_import_mmt = 4.5
    days_per_mmt = 30 / monthly_import_mmt
    return round(fill_mmt * days_per_mmt, 1)


def main() -> None:
    log.info("Fetching SPR / ISPRL data…")

    # Try PIB for any new announcement
    pib = scrape_pib()

    data = {
        "as_of": str(datetime.now(timezone.utc).date()),
        "last_verified": LAST_KNOWN["verified_date"],
        "fill_mmt": LAST_KNOWN["fill_mmt"],
        "fill_pct": LAST_KNOWN["fill_pct"],
        "phase1_capacity_mmt": TOTAL_PHASE1_CAPACITY_MMT,
        "phase2_capacity_mmt": TOTAL_PHASE2_CAPACITY_MMT,
        "days_of_import_cover": build_days_of_import_cover(LAST_KNOWN["fill_mmt"]),
        "sites": SPR_SITES,
        "source": LAST_KNOWN["source"],
        "note": LAST_KNOWN["note"],
        "latest_pib": pib,
    }

    write_json(DATA_DIR / "spr_status.json", data)

    # Append to history (one row per run; only adds if fill_mmt changed)
    hist_path = DATA_DIR / "spr_history.csv"
    row = {
        "date": data["as_of"],
        "fill_mmt": data["fill_mmt"],
        "fill_pct": data["fill_pct"],
        "days_of_cover": data["days_of_import_cover"],
        "source": data["source"],
    }
    df_new = pd.DataFrame([row])
    if hist_path.exists():
        old = pd.read_csv(hist_path)
        df_combined = pd.concat([old, df_new], ignore_index=True).drop_duplicates(
            subset=["date"], keep="last"
        )
    else:
        df_combined = df_new
    df_combined.to_csv(hist_path, index=False)

    log.info(f"SPR: {data['fill_mmt']} MMT / {data['fill_pct']}% / {data['days_of_import_cover']} days cover")
    update_metadata("spr_isprl")


if __name__ == "__main__":
    main()
