# Deployment Guide — India Energy Dashboard

Step-by-step instructions to go from zero to a live public dashboard.

---

## Prerequisites

- GitHub account (free)
- Python 3.11+ on your local machine
- `pip install -r requirements.txt`

---

## Step 1 — Test locally

```bash
# From the project root
pip install -r requirements.txt

# Run scrapers (order matters — attribution depends on markets/crude)
python -m scrapers.crude_benchmarks
python -m scrapers.markets
python -m scrapers.fuel_prices
python -m scrapers.private_omc
python -m scrapers.spr_isprl
python -m scrapers.lng_data
python -m scrapers.attribution

# Check data was written
ls data/

# Run tests
pytest tests/ -v

# Launch app locally
streamlit run app/streamlit_app.py
```

Visit http://localhost:8501 — all 7 panels should render with real data.

---

## Step 2 — Create GitHub repository

```bash
# On github.com: create new public repo named "india-energy-dashboard"
# (Do NOT initialise with README — we already have one)

# In your local project directory:
git init
git add .
git commit -m "feat: initial India Energy Dashboard v1.0"
git branch -M main
git remote add origin https://github.com/ImmadiVenkatesh/india-energy-dashboard.git
git push -u origin main
```

---

## Step 3 — Enable GitHub Actions

1. Go to your repo on GitHub
2. **Actions tab** → click "I understand my workflows, go ahead and enable them"
3. **Settings → Actions → General → Workflow permissions** → select **"Read and write permissions"** → Save
4. **Actions tab → Daily Data Update → Run workflow** (manual trigger to test)
5. Watch the run. If all scrapers pass: ✅ you're set. If a scraper fails, check the logs — usually a site layout change or network issue.

**Usage limits (public repo):**
- GitHub Actions free tier: **2,000 minutes/month**
- This workflow uses **~5 minutes/day × 30 = 150 min/month** — well within limits

---

## Step 4 — Deploy to Streamlit Cloud

1. Visit [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **New app**
4. Select:
   - **Repository**: `ImmadiVenkatesh/india-energy-dashboard`
   - **Branch**: `main`
   - **Main file path**: `app/streamlit_app.py`
5. Click **Deploy**
6. Your app URL will be: `https://immadivenkatesh-india-energy-dashboard.streamlit.app`

**Streamlit Cloud free tier:**
- 1 app per account (public repos)
- Sleeps after ~7 days of no traffic (15-30s cold start)
- The GitHub Actions keep-alive step pings your app URL daily to prevent sleep

---

## Step 5 — Add the keep-alive secret

To enable the daily ping that prevents Streamlit from sleeping:

1. Go to your GitHub repo → **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `STREAMLIT_APP_URL`
4. Value: `https://immadivenkatesh-india-energy-dashboard.streamlit.app`
5. Save

The `keep-alive` job in the workflow will now ping this URL after each daily data update.

---

## Step 6 — Monitor

### GitHub Actions
- Email notifications for failed runs: **Settings → Notifications** — enabled by default
- Check the **Actions tab** for run history and logs

### Streamlit
- The **Data freshness** expander on the dashboard shows last-updated time per source
- If a scraper fails, its status shows `error` in the metadata banner

### Optional: UptimeRobot
- [UptimeRobot](https://uptimerobot.com/) free tier → HTTP monitor → 5-min interval on your app URL
- Sends email/SMS if the app goes down

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Scraper fails with `403` | Site blocked bot UA | Update `User-Agent` in `scrapers/utils.py` |
| `fuel_prices_latest.json` empty | Aggregator site layout changed | Inspect the site's HTML, update parser in `fuel_prices.py` |
| Streamlit app shows "No data found" | Data files not committed | Check GitHub Actions run logs; run scrapers manually |
| `yfinance` returns empty | Yahoo Finance API change | `pip install --upgrade yfinance` |
| Attribution fails | Nifty download failed | `yfinance` rate limit; try after a few minutes |
| Streamlit cold start > 60s | App sleeping | Add keep-alive secret (Step 5) |

---

## Updating the data when PPAC releases new monthly figures

PPAC publishes monthly LNG import statistics. To update:

1. Edit `scrapers/lng_data.py`
2. Update the `ppac_import` dict:
   ```python
   ppac_import = {
       "month": "Apr-2025",
       "volume_mmt": 2.38,     # ← new figure
       "source": "PPAC Monthly LNG import statistics",
   }
   ```
3. Commit and push — the dashboard will show the new figure on next deploy

Similarly, update `scrapers/spr_isprl.py` when a new parliamentary statement gives a fresh SPR fill level.

---

## Cost summary

| Service | Plan | Monthly cost |
|---|---|---|
| GitHub | Free | $0 |
| GitHub Actions | Free (public repo) | $0 |
| Streamlit Cloud | Free | $0 |
| UptimeRobot | Free (50 monitors) | $0 |
| **Total** | | **$0** |
