"""
Daily crude oil benchmarks via yfinance.
Tickers: Brent (BZ=F), WTI (CL=F), INR/USD (INR=X).
PPAC Indian Basket is computed as weighted average: 70% Dubai + 30% Brent.
Writes:
  data/crude_benchmarks.csv   — 90-day OHLCV history
  data/crude_latest.json      — latest close prices
"""
import json
from pathlib import Path

import pandas as pd
import yfinance as yf

from scrapers.utils import DATA_DIR, get_logger, update_metadata, utc_now_iso, write_json

log = get_logger("crude_benchmarks")

TICKERS = {
    "brent": "BZ=F",
    "wti": "CL=F",
    "inr_usd": "INR=X",
    "dubai": "MCO=F",   # Oman/Dubai proxy via MCO futures; falls back to Brent − 1
}


def fetch_history(period: str = "90d") -> pd.DataFrame:
    rows = []
    for name, ticker in TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if hist.empty:
                log.warning(f"{ticker} returned empty history — skipping")
                continue
            hist = hist.reset_index()
            hist["symbol"] = name
            hist["date"] = pd.to_datetime(hist["Date"]).dt.date
            rows.append(
                hist[["date", "symbol", "Open", "High", "Low", "Close", "Volume"]].rename(
                    columns=str.lower
                )
            )
        except Exception as exc:
            log.error(f"Failed fetching {ticker}: {exc}")

    if not rows:
        raise RuntimeError("All crude ticker fetches failed")

    df = pd.concat(rows, ignore_index=True)
    df["date"] = df["date"].astype(str)
    return df


def compute_indian_basket(latest: dict) -> float | None:
    """PPAC formula: ~70% Dubai/Oman + 30% Brent (USD/bbl)."""
    brent = latest.get("brent")
    dubai = latest.get("dubai") or (brent - 1.0 if brent else None)
    if brent is None:
        return None
    return round(0.70 * dubai + 0.30 * brent, 2)


def main() -> None:
    log.info("Fetching crude benchmarks…")
    df = fetch_history()

    out_csv = DATA_DIR / "crude_benchmarks.csv"
    if out_csv.exists():
        old = pd.read_csv(out_csv)
        df = pd.concat([old, df], ignore_index=True).drop_duplicates(
            subset=["date", "symbol"], keep="last"
        )
    df.to_csv(out_csv, index=False)
    log.info(f"Written {len(df)} rows → {out_csv}")

    latest = (
        df.sort_values("date")
        .groupby("symbol")
        .tail(1)
        .set_index("symbol")["close"]
        .to_dict()
    )

    indian_basket = compute_indian_basket(latest)
    if indian_basket:
        latest["indian_basket"] = indian_basket

    write_json(
        DATA_DIR / "crude_latest.json",
        {"as_of": utc_now_iso(), "prices_usd_bbl": latest},
    )
    log.info(f"Latest prices: {latest}")
    update_metadata("crude_benchmarks")


if __name__ == "__main__":
    main()
