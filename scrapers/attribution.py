"""
Daily attribution: what drove Nifty's return today?
Honest multivariate OLS regression:
  Nifty ~ Brent + NIFTY_IT + INR/USD

This is the 'honest reframe' from the plan — instead of a made-up
"X% oil, Y% AI" pie chart, we show defensible regression coefficients
and today's decomposition with R².
Writes: data/attribution_latest.json, data/attribution_history.csv
"""
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from scrapers.utils import DATA_DIR, get_logger, update_metadata, write_json

log = get_logger("attribution")
warnings.filterwarnings("ignore", category=FutureWarning)

TICKERS = {
    "nifty":    "^NSEI",
    "brent":    "BZ=F",
    "nifty_it": "^CNXIT",   # AI / tech sentiment proxy
    "inr":      "INR=X",
    "gold":     "GC=F",
}

FEATURE_LABELS = {
    "brent":    "🛢️ Oil (Brent)",
    "nifty_it": "💻 Tech / AI (NIFTY IT)",
    "inr":      "💱 Currency (INR/USD)",
}


def download_returns(period: str = "1y") -> pd.DataFrame:
    """Download adjusted closes and compute daily % returns."""
    data = {}
    for name, ticker in TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period=period)
            if not hist.empty:
                data[name] = hist["Close"]
        except Exception as exc:
            log.warning(f"{ticker} failed: {exc}")

    if "nifty" not in data:
        raise RuntimeError("Could not download Nifty data — attribution skipped")

    df = pd.DataFrame(data).dropna(how="all")
    returns = df.pct_change().dropna()
    return returns


def run_regression(returns: pd.DataFrame) -> dict:
    features = [f for f in ["brent", "nifty_it", "inr"] if f in returns.columns]
    if not features:
        raise RuntimeError("No feature columns available for regression")

    X = returns[features].values
    y = returns["nifty"].values

    model = LinearRegression(fit_intercept=True)
    model.fit(X, y)

    r2 = float(model.score(X, y))
    coefs = {feat: float(model.coef_[i]) for i, feat in enumerate(features)}

    # Today's decomposition
    today = returns.iloc[-1]
    contributions: dict[str, float] = {}
    for feat in features:
        contributions[feat] = float(coefs[feat] * today[feat])

    explained = sum(contributions.values())
    contributions["unexplained"] = float(today["nifty"] - explained)

    return {
        "as_of": str(datetime.now(timezone.utc).date()),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nifty_return_today_pct": round(float(today["nifty"]) * 100, 4),
        "r_squared": round(r2, 4),
        "regression_period": "trailing 1 year daily returns",
        "features": features,
        "coefficients": {k: round(v, 6) for k, v in coefs.items()},
        "today_contributions_pct": {
            k: round(v * 100, 4) for k, v in contributions.items()
        },
        "feature_labels": FEATURE_LABELS,
        "interpretation": (
            "R² shows how much of historical Nifty variance is explained by these 3 factors. "
            "Each bar shows the estimated contribution (in percentage points) of that factor "
            "to today's Nifty return. 'Unexplained' captures everything else — sentiment, "
            "institutional flows, domestic news, and other idiosyncratic drivers."
        ),
        "caveat": (
            "Regression coefficients are estimated on trailing 1-year data and assume linear, "
            "stationary relationships. They do not imply causation, and should not be used "
            "for investment decisions."
        ),
    }


def main() -> None:
    log.info("Running attribution regression…")
    try:
        returns = download_returns()
        result = run_regression(returns)
        write_json(DATA_DIR / "attribution_latest.json", result)

        # Append to history
        hist_path = DATA_DIR / "attribution_history.csv"
        row = {
            "date": result["as_of"],
            "nifty_return_pct": result["nifty_return_today_pct"],
            "r_squared": result["r_squared"],
            **{f"contrib_{k}_pct": v for k, v in result["today_contributions_pct"].items()},
        }
        df_new = pd.DataFrame([row])
        if hist_path.exists():
            old = pd.read_csv(hist_path)
            df_new = pd.concat([old, df_new], ignore_index=True).drop_duplicates(
                subset=["date"], keep="last"
            )
        df_new.to_csv(hist_path, index=False)

        log.info(f"Attribution: Nifty {result['nifty_return_today_pct']:+.2f}% | R²={result['r_squared']:.2%}")
        log.info(f"  Contributions: {result['today_contributions_pct']}")
        update_metadata("attribution")

    except Exception as exc:
        log.error(f"Attribution failed: {exc}")
        update_metadata("attribution", status="error")
        raise


if __name__ == "__main__":
    main()
