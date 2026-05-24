"""
Daily market data: Nifty 50, NIFTY IT, Gold MCX, INR/USD.
All via yfinance (end-of-day, free, no API key).
Writes: data/markets.csv, data/markets_latest.json
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from scrapers.utils import DATA_DIR, get_logger, update_metadata, write_json

log = get_logger("markets")

TICKERS = {
    "nifty50":   "^NSEI",
    "nifty_it":  "^CNXIT",   # AI / tech-sector proxy
    "gold_mcx":  "GC=F",     # Gold futures (USD/oz; we display in INR context)
    "inr_usd":   "INR=X",    # USD per 1 INR → inverse for display
    "sensex":    "^BSESN",
}


def fetch(period: str = "90d") -> pd.DataFrame:
    rows = []
    for name, ticker in TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if hist.empty:
                log.warning(f"{ticker} empty — skip")
                continue
            hist = hist.reset_index()
            hist["symbol"] = name
            hist["date"] = pd.to_datetime(hist["Date"]).dt.date.astype(str)
            rows.append(
                hist[["date", "symbol", "Open", "High", "Low", "Close", "Volume"]].rename(
                    columns=str.lower
                )
            )
        except Exception as exc:
            log.error(f"{ticker} fetch failed: {exc}")

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build_latest(df: pd.DataFrame) -> dict:
    latest = (
        df.sort_values("date")
        .groupby("symbol")
        .tail(1)
        .set_index("symbol")["close"]
        .to_dict()
    )
    # Compute daily returns
    returns = {}
    for sym in df["symbol"].unique():
        sym_df = df[df["symbol"] == sym].sort_values("date")
        if len(sym_df) >= 2:
            today_close = sym_df["close"].iloc[-1]
            prev_close = sym_df["close"].iloc[-2]
            returns[sym] = round((today_close - prev_close) / prev_close * 100, 3)

    # INR display: INR=X is USD per 1 INR, so we flip for INR/USD
    inr_raw = latest.get("inr_usd")
    inr_display = round(1 / inr_raw, 4) if inr_raw and inr_raw != 0 else None

    return {
        "as_of": str(datetime.now(timezone.utc).date()),
        "latest": latest,
        "inr_per_usd": inr_display,
        "daily_returns_pct": returns,
    }


def main() -> None:
    log.info("Fetching market data…")
    df = fetch()
    if df.empty:
        log.error("All market fetches failed")
        update_metadata("markets", status="error")
        return

    hist_path = DATA_DIR / "markets.csv"
    if hist_path.exists():
        old = pd.read_csv(hist_path)
        df = pd.concat([old, df], ignore_index=True).drop_duplicates(
            subset=["date", "symbol"], keep="last"
        )
    df.to_csv(hist_path, index=False)

    latest = build_latest(df)
    write_json(DATA_DIR / "markets_latest.json", latest)

    log.info(f"Markets: Nifty={latest['latest'].get('nifty50'):.0f}, INR/USD={latest['inr_per_usd']}")
    update_metadata("markets")


if __name__ == "__main__":
    main()
