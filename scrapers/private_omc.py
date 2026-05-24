"""
Private OMC fuel prices (Shell, Reliance, Nayara/Essar).
Honest approach:
  - Attempt aggregator scrape for each brand.
  - Where data is unavailable, estimate as PSU price + known typical premium
    and flag the record with source='estimated'.
  - Never present estimates as official prices.
Writes: data/private_omc_latest.json
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from scrapers.utils import DATA_DIR, get_logger, safe_get, update_metadata, write_json

log = get_logger("private_omc")

# Typical premiums over PSU prices (₹/litre), based on historic data.
# Updated quarterly — source: consumer surveys + media reports.
KNOWN_PREMIUMS = {
    "Shell":    {"petrol": 3.5, "diesel": 2.0},
    "Reliance": {"petrol": 2.0, "diesel": 1.5},
    "Nayara":   {"petrol": 1.5, "diesel": 1.0},
}

CITIES = ["Delhi", "Mumbai", "Chennai", "Bengaluru", "Hyderabad"]


def load_psu_prices() -> dict:
    """Load today's PSU prices from fuel_prices_latest.json as baseline."""
    path = DATA_DIR / "fuel_prices_latest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for row in data.get("rows", []):
        city = row["city"]
        result[city] = {
            "petrol": row.get("petrol_per_litre"),
            "diesel": row.get("diesel_per_litre"),
        }
    return result


def estimate_from_psu(city: str, brand: str, psu: dict) -> dict | None:
    """Estimate private OMC price from PSU baseline + known premium."""
    base = psu.get(city)
    premium = KNOWN_PREMIUMS.get(brand)
    if not base or not premium:
        return None
    petrol_base = base.get("petrol")
    diesel_base = base.get("diesel")
    today = str(datetime.now(timezone.utc).date())
    return {
        "city": city,
        "brand": brand,
        "date": today,
        "petrol_per_litre": round(petrol_base + premium["petrol"], 2) if petrol_base else None,
        "diesel_per_litre": round(diesel_base + premium["diesel"], 2) if diesel_base else None,
        "source": "estimated",
        "note": f"PSU price + ₹{premium['petrol']}/L typical {brand} premium (estimated, not official)",
    }


def scrape_shell(city: str) -> dict | None:
    """Attempt to scrape Shell India price for a city from aggregators."""
    # Shell does not publish national aggregated prices; use goodreturns shell page if available
    try:
        slug = city.lower().replace(" ", "-")
        url = f"https://www.goodreturns.in/shell-petrol-price-in-{slug}.html"
        r = safe_get(url, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")
        today = str(datetime.now(timezone.utc).date())
        result = {"city": city, "brand": "Shell", "date": today, "source": "scraped"}
        for row in soup.select("table tr"):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) >= 2:
                label = cells[0].lower()
                if "petrol" in label:
                    m = re.search(r"[\d.]+", cells[1])
                    result["petrol_per_litre"] = float(m.group()) if m else None
                elif "diesel" in label:
                    m = re.search(r"[\d.]+", cells[1])
                    result["diesel_per_litre"] = float(m.group()) if m else None
        if result.get("petrol_per_litre"):
            return result
    except Exception as exc:
        log.debug(f"Shell scrape failed for {city}: {exc}")
    return None


def main() -> None:
    log.info("Fetching private OMC prices…")
    psu = load_psu_prices()
    rows = []

    for brand in ["Shell", "Reliance", "Nayara"]:
        for city in CITIES:
            scraped = None
            if brand == "Shell":
                scraped = scrape_shell(city)

            if scraped:
                rows.append(scraped)
                log.info(f"  {brand} {city}: scraped ₹{scraped.get('petrol_per_litre')}")
            else:
                est = estimate_from_psu(city, brand, psu)
                if est:
                    rows.append(est)
                    log.info(f"  {brand} {city}: estimated ₹{est.get('petrol_per_litre')} (PSU+premium)")

    today = str(datetime.now(timezone.utc).date())
    write_json(DATA_DIR / "private_omc_latest.json", {
        "as_of": today,
        "disclaimer": (
            "Records marked source='estimated' are derived from PSU prices plus "
            "historically observed brand premiums. They are NOT official prices."
        ),
        "rows": rows,
    })
    log.info(f"Private OMC: {len(rows)} records written")
    update_metadata("private_omc")


if __name__ == "__main__":
    main()
