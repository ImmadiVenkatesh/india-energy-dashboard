# ⛽ India Energy Intelligence Dashboard

> **Free, open-source, auto-updating dashboard** for India's oil, gas, and energy intelligence —
> Strategic Petroleum Reserves · Daily fuel prices · Crude benchmarks · LNG · Market attribution.

[![Daily Data Update](https://github.com/ImmadiVenkatesh/india-energy-dashboard/actions/workflows/daily-update.yml/badge.svg)](https://github.com/ImmadiVenkatesh/india-energy-dashboard/actions/workflows/daily-update.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://immadivenkatesh-india-energy-dashboard.streamlit.app)

---

## 🚀 Live Dashboard

**→ [Open the dashboard](https://immadivenkatesh-india-energy-dashboard.streamlit.app)**

Data is refreshed daily at **06:30 IST** via GitHub Actions and committed back to this repository.
The Streamlit app reads from the committed data files — fast page loads, no scraping at render time.

---

## 📊 What's Inside

| Panel | What it shows |
|---|---|
| **🏠 Overview** | Quick KPIs: SPR fill, Brent, Delhi fuel prices, Nifty |
| **🛢️ SPR** | ISPRL fill level, days of import cover, Phase-1/2 site map |
| **⛽ Fuel Prices** | Daily petrol/diesel for 10 cities (IOC/BPCL/HPCL + Shell/Reliance estimates) |
| **📈 Crude Benchmarks** | Brent, WTI, Indian Basket, Dubai — 90-day OHLCV + candlestick |
| **🧊 LNG** | Petronet terminal utilization, JKM/Henry Hub spot, monthly import volumes |
| **📊 Markets** | Nifty 50, NIFTY IT, Gold, INR/USD — normalized trend + Brent correlation |
| **🔬 Attribution** | Honest OLS regression: how much did oil / tech / FX explain today's Nifty move? |

---

## 🏗️ Architecture

```
GitHub Actions (cron 06:30 IST)
    └── Python scrapers (in /scrapers/)
         └── Writes JSON/CSV to /data/
              └── git commit + push
                   └── Streamlit Cloud reads /data/ → renders dashboard
```

**Why this design?**
- ✅ Zero cost (GitHub Actions free tier: ~5 min/day vs 2,000 min/month limit)
- ✅ Fast page loads (Streamlit reads pre-fetched files, no live scraping)
- ✅ Historical data captured automatically (append-only CSVs)
- ✅ No API keys required for the core pipeline

---

## 📦 Data Sources

| Domain | Source | Frequency | Method |
|---|---|---|---|
| SPR fill | ISPRL / Parliament Q&A / PIB | Quarterly+ | Web scrape |
| Fuel prices (PSU) | goodreturns.in / iocl.com | Daily 06:00 IST | BeautifulSoup |
| Fuel prices (private) | Aggregators + PSU estimate | Daily | Scrape + heuristic |
| Brent / WTI | Yahoo Finance (`yfinance`) | End-of-day | yfinance lib |
| Indian Basket | Computed (70% Dubai + 30% Brent) | Daily | Formula |
| Gold, Nifty, INR | Yahoo Finance | End-of-day | yfinance lib |
| LNG terminals | Petronet investor disclosures | Quarterly | PDF parse / hardcoded |
| JKM spot | EIA + investing.com | Daily | API + scrape |
| Henry Hub | EIA API (free tier) | Weekly | REST API |
| Attribution | yfinance (OLS regression) | Daily | sklearn |

### Honest caveats

- **SPR daily fill**: ISPRL does not publish this. We show the most recent verified parliamentary figure with a clear "last verified" date.
- **Private OMC prices**: Shell/Reliance/Nayara do not publish national aggregated daily prices. Records marked `source=estimated` use a PSU baseline + typical brand premium. Never presented as official.
- **Oil-shock vs AI attribution**: Not a clean headline number — presented as regression R² and decomposition, not a pie chart.

---

## 🛠️ Local Setup

### Prerequisites

- Python 3.11+
- `pip install -r requirements.txt`

### Run scrapers

```bash
# All at once
python -m scrapers.crude_benchmarks
python -m scrapers.markets
python -m scrapers.fuel_prices
python -m scrapers.private_omc
python -m scrapers.spr_isprl
python -m scrapers.lng_data
python -m scrapers.attribution
```

### Run the dashboard

```bash
streamlit run app/streamlit_app.py
```

Then open http://localhost:8501

### Run tests

```bash
pytest tests/ -v
```

---

## 🚢 Deployment (Streamlit Cloud)

1. **Fork this repo** (or use as-is)
2. Visit [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub
3. **New app** → pick this repo → branch: `main` → entry file: `app/streamlit_app.py`
4. Deploy. URL: `https://<your-username>-india-energy-dashboard.streamlit.app`
5. Add a GitHub secret `STREAMLIT_APP_URL` with your app URL to enable the keep-alive ping

### Enable GitHub Actions

1. **Actions tab** → enable workflows
2. **Settings → Actions → General → Workflow permissions** → "Read and write permissions"
3. **Actions tab → Daily Data Update → Run workflow** — verify it runs green
4. From then on, runs automatically at 06:30 IST daily

---

## 📁 Repository Structure

```
india-energy-dashboard/
├── .github/workflows/
│   └── daily-update.yml       # Cron job: fetch + commit data daily
├── scrapers/
│   ├── utils.py               # Shared helpers (retry, logging, JSON write)
│   ├── crude_benchmarks.py    # Brent, WTI, Indian Basket via yfinance
│   ├── fuel_prices.py         # Daily IOC/BPCL/HPCL prices (10 cities)
│   ├── private_omc.py         # Shell/Reliance/Nayara (scraped + estimated)
│   ├── spr_isprl.py           # Strategic Petroleum Reserve status
│   ├── lng_data.py            # LNG terminals, JKM/HH, PPAC imports
│   ├── markets.py             # Nifty, Gold, INR via yfinance
│   └── attribution.py         # OLS regression decomposition
├── data/                      # Auto-committed by GitHub Actions
│   ├── spr_status.json
│   ├── spr_history.csv
│   ├── fuel_prices_latest.json
│   ├── fuel_prices_history.csv
│   ├── crude_benchmarks.csv
│   ├── crude_latest.json
│   ├── lng_dashboard.json
│   ├── markets.csv
│   ├── markets_latest.json
│   ├── private_omc_latest.json
│   ├── attribution_latest.json
│   ├── attribution_history.csv
│   └── metadata.json
├── app/
│   ├── streamlit_app.py       # Main entry point
│   ├── panels/                # One module per tab
│   └── components/            # Shared header, filters
├── tests/
│   └── test_scrapers.py       # Data shape + freshness validation
├── requirements.txt
├── .streamlit/config.toml     # Dark theme, orange accent
└── LICENSE
```

---

## 🗺️ Roadmap

### Phase 1 — India MVP ✅ (this release)
- [x] SPR panel with ISPRL data and days-of-cover
- [x] Daily fuel prices for 10 cities + private OMC estimates
- [x] Crude benchmarks (Brent/WTI/Indian Basket) with OHLCV history
- [x] LNG terminal utilization + JKM/HH spot prices
- [x] Nifty/Gold/INR markets with Brent correlation
- [x] Honest attribution regression (not a made-up pie chart)
- [x] GitHub Actions daily cron + Streamlit Cloud deploy

### Phase 2 — Hardening
- [ ] PPAC PDF parser for Indian Basket (daily bulletin)
- [ ] Slack/email alert if any scraper fails > 2 consecutive days
- [ ] Per-panel CSV/JSON download buttons (all panels)
- [ ] UptimeRobot or GitHub Actions keep-alive ping

### Phase 3 — Global (Month 2+)
- [ ] Country selector: USA (EIA API), EU (Eurostat), China (limited)
- [ ] OPEC+ production cuts tracker
- [ ] Cross-country reserves coverage comparison (days of import cover)

---

## 📜 License

MIT — see [LICENSE](LICENSE). Free to use, fork, and extend.

---

## 🙏 Acknowledgements

- [ISPRL](https://www.isprl.in/) — India's Strategic Petroleum Reserves infrastructure
- [PPAC](https://www.ppac.gov.in/) — Petroleum Planning & Analysis Cell, MoPNG
- [yfinance](https://github.com/ranaroussi/yfinance) — Yahoo Finance market data
- [Streamlit](https://streamlit.io/) — The dashboard framework
- [EIA](https://www.eia.gov/) — US Energy Information Administration (Henry Hub data)

---

*Built by [Venkatesh Immadi](https://github.com/ImmadiVenkatesh) · India Energy Intelligence Dashboard v1.0*
