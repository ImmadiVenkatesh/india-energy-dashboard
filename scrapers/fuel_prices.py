"""
Daily petrol & diesel prices from public OMC sources.
Primary: goodreturns.in (aggregates IOC/BPCL/HPCL official prices).
Fallback: iocl.com direct scrape.
Cities covered: Delhi, Mumbai, Chennai, Kolkata, Bengaluru, Hyderabad,
                Pune, Ahmedabad, Jaipur, Lucknow.
Writes:
  data/fuel_prices_latest.json
  data/fuel_prices_history.csv
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from scrapers.utils import DATA_DIR, get_logger, safe_get, update_metadata, utc_now_iso, write_json

log = get_logger("fuel_prices")

CITIES = [
    "Delhi", "Mumbai", "Chennai", "Kolkata",
    "Bengaluru", "Hyderabad", "Pune", "Ahmedabad",
    "Jaipur", "Lucknow",
]

# goodreturns city slugs
CITY_SLUGS = {
    "Delhi":     "petrol-price-in-delhi",
    "Mumbai":    "petrol-price-in-mumbai",
    "Chennai":   "petrol-price-in-chennai",
    "Kolkata":   "petrol-price-in-kolkata",
    "Bengaluru": "petrol-price-in-bangalore",
    "Hyderabad": "petrol-price-in-hyderabad",
    "Pune":      "petrol-price-in-pune",
    "Ahmedabad": "petrol-price-in-ahmedabad",
    "Jaipur":    "petrol-price-in-jaipur",
    "Lucknow":   "petrol-price-in-lucknow",
}

BASE_URL = "https://www.goodreturns.in/{slug}.html"


def parse_price(text: str) -> float | None:
    """Extract numeric price from strings like '₹94.72' or '94.72/litre'."""
    m = re.search(r"[\d,]+\.\d+", text.replace(",", ""))
    return float(m.group()) if m else None


def scrape_goodreturns(city: str) -> dict | None:
    slug = CITY_SLUGS.get(city)
    if not slug:
        return None
    url = BASE_URL.format(slug=slug)
    try:
        r = safe_get(url)
        soup = BeautifulSoup(r.text, "lxml")

        # Goodreturns shows a price-table; look for petrol & diesel rows
        result = {"city": city, "omc": "PSU blend", "date": str(datetime.now(timezone.utc).date())}

        for row in soup.select("table tr"):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) >= 2:
                label, val = cells[0].lower(), cells[1]
                if "petrol" in label:
                    result["petrol_per_litre"] = parse_price(val)
                elif "diesel" in label:
                    result["diesel_per_litre"] = parse_price(val)

        if result.get("petrol_per_litre"):
            return result
        return None
    except Exception as exc:
        log.warning(f"goodreturns scrape failed for {city}: {exc}")
        return None


def scrape_fallback_ioc() -> list[dict]:
    """Direct fallback from iocl.com — their page loads city prices dynamically.
    We use the known XHR pattern they use for the price table widget."""
    url = "https://iocl.com/petrol-diesel-price"
    try:
        r = safe_get(url, timeout=40)
        soup = BeautifulSoup(r.text, "lxml")
        rows = []
        today = str(datetime.now(timezone.utc).date())
        for tr in soup.select("table.price-table tr, tr.price-row"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) >= 3:
                city = cells[0]
                petrol = parse_price(cells[1])
                diesel = parse_price(cells[2]) if len(cells) > 2 else None
                if city and petrol:
                    rows.append({
                        "city": city, "omc": "IOC", "date": today,
                        "petrol_per_litre": petrol, "diesel_per_litre": diesel,
                    })
        return rows
    except Exception as exc:
        log.error(f"IOC fallback failed: {exc}")
        return []


def main() -> None:
    log.info("Scraping fuel prices…")
    rows = []
    for city in CITIES:
        result = scrape_goodreturns(city)
        if result:
            rows.append(result)
            log.info(f"  {city}: ₹{result.get('petrol_per_litre')} petrol / ₹{result.get('diesel_per_litre')} diesel")
        else:
            log.warning(f"  {city}: primary scrape failed")

    if len(rows) < 3:
        log.warning("Too few cities scraped — trying IOC fallback")
        rows = scrape_fallback_ioc() or rows

    today = str(datetime.now(timezone.utc).date())
    write_json(DATA_DIR / "fuel_prices_latest.json", {"as_of": today, "rows": rows})

    if rows:
        hist_path = DATA_DIR / "fuel_prices_history.csv"
        df_new = pd.DataFrame(rows)
        if hist_path.exists():
            old = pd.read_csv(hist_path)
            df_new = pd.concat([old, df_new], ignore_index=True).drop_duplicates(
                subset=["date", "city"], keep="last"
            )
        df_new.to_csv(hist_path, index=False)
        log.info(f"Fuel history updated: {len(df_new)} rows")

    update_metadata("fuel_prices")


if __name__ == "__main__":
    main()
