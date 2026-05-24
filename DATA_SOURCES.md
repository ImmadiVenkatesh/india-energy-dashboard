# Data Sources — Honest Feasibility Matrix

Complete documentation of every data source used in this dashboard.

---

## ✅ Fully automated (free, reliable)

### Brent & WTI Crude — yfinance
- **Tickers**: `BZ=F` (Brent futures), `CL=F` (WTI futures)
- **Frequency**: End-of-day (US trading hours)
- **Library**: [yfinance](https://github.com/ranaroussi/yfinance)
- **Lag**: ~1 trading day
- **Scraper**: `scrapers/crude_benchmarks.py`

### Indian Basket Crude — Computed
- **Formula**: 70% Dubai/Oman + 30% Brent (matches PPAC formula)
- **Note**: PPAC publishes the exact figure in a daily PDF bulletin (~18:00 IST).
  We use the formula as primary; if PDF parsing is added in Phase 2, it overrides.
- **Scraper**: `scrapers/crude_benchmarks.py` → `compute_indian_basket()`

### Nifty 50, NIFTY IT, Gold, INR/USD — yfinance
- **Tickers**: `^NSEI`, `^CNXIT`, `GC=F`, `INR=X`, `^BSESN`
- **Frequency**: End-of-day
- **Scraper**: `scrapers/markets.py`

### Henry Hub Natural Gas — EIA API
- **URL**: `https://api.eia.gov/v2/natural-gas/pri/fut/data/` (no API key needed for basic access)
- **Fallback**: yfinance `NG=F`
- **Frequency**: Weekly
- **Scraper**: `scrapers/lng_data.py` → `fetch_jkm_proxy()`

---

## ⚠️ Partially automated (scrapers may need maintenance)

### PSU Fuel Prices (IOC / BPCL / HPCL) — goodreturns.in
- **URL**: `https://www.goodreturns.in/<city-slug>.html`
- **Frequency**: Daily 06:00 IST
- **Method**: BeautifulSoup HTML parse of price table
- **Risk**: Site layout changes will break the parser. Monitor GitHub Actions logs.
- **Fallback**: Direct scrape of `iocl.com/petrol-diesel-price`
- **Scraper**: `scrapers/fuel_prices.py`

### JKM Spot Price — investing.com
- **URL**: `https://www.investing.com/commodities/lng-japan-korea-marker-platts`
- **Method**: JSON embedded in page HTML
- **Risk**: Paywall or JS rendering may block. Check logs if `jkm_spot` is null.
- **Note**: True JKM is published by Platts (subscription). This is the best public proxy.
- **Scraper**: `scrapers/lng_data.py` → `fetch_jkm_spot()`

### PIB (Press Information Bureau) — ISPRL news
- **URL**: `https://pib.gov.in/allRel.aspx?ModId=6&reg=3&lang=1`
- **Method**: Link text scan for ISPRL/reserve mentions
- **Frequency**: Daily (checks for new releases)
- **Scraper**: `scrapers/spr_isprl.py` → `scrape_pib()`

---

## 📋 Manually maintained (updated when new data is released)

### SPR Fill Level — Parliament Q&A
- **Reality**: ISPRL does not publish daily or even monthly fill levels.
  The government answers Parliamentary Questions (PQ) on SPR status — typically quarterly or on demand.
- **Process**: When a new PQ answer or PIB release appears with a fill figure, update `LAST_KNOWN` in `scrapers/spr_isprl.py`
- **Current value**: Phase-1 (5.33 MMT) fully filled as of early 2024 (Parliament Standing Committee, Feb 2024)
- **How to update**:
  ```python
  # In scrapers/spr_isprl.py
  LAST_KNOWN = {
      "fill_mmt": 5.33,              # ← update this
      "fill_pct": 100.0,             # ← update this
      "verified_date": "2024-02-01", # ← update this
      "source": "Parliament ...",    # ← update citation
  }
  ```

### PPAC Monthly LNG Imports
- **Source**: [PPAC LNG statistics](https://www.ppac.gov.in/content/149_1_LNG.aspx)
- **Frequency**: Monthly (published ~30 days after month end)
- **Process**: Download Excel from PPAC, read the latest month row, update `scrapers/lng_data.py`
- **How to update**: See [DEPLOYMENT.md](DEPLOYMENT.md#updating-the-data-when-ppac-releases-new-monthly-figures)

### Petronet Terminal Utilization
- **Source**: Petronet LNG investor presentations (BSE/NSE filings), quarterly
- **Process**: After each quarterly earnings release, update `PETRONET_UTILIZATION` in `scrapers/lng_data.py`

---

## ❌ Not attempted (honest scope limits)

| Data | Reason |
|---|---|
| Real-time intraday fuel prices | OMCs revise once per day at 06:00 IST. More frequent polling is wasted compute. |
| "X% oil / Y% AI" attribution | No legitimate methodology. We use OLS regression instead (see Attribution panel). |
| ISPRL daily inventory | Not published. Period. |
| LNG "strategic reserve days" | India has no strategic LNG reserve — only commercial inventory. |
| Private OMC official daily prices | Shell/Reliance/Nayara don't publish nationally aggregated daily figures. |
| Futures curves / forward prices | Subscription data (Platts, Argus, CME). Out of scope for free tier. |
| Investment recommendations | Not in scope. Ever. |

---

## 🔁 Source reliability tracking

The `data/metadata.json` file records last-updated timestamp and status per scraper.
The dashboard's "Data freshness" expander shows this on every page load.

If a scraper fails:
1. Check GitHub Actions logs for the error
2. Test manually: `python -m scrapers.<name>`
3. Common fixes: update User-Agent, adjust CSS selectors, upgrade yfinance
4. The workflow uses `continue-on-error: true` so one failure doesn't cascade
