"""
Panel: Overview — quick KPIs across all domains.
"""
import json
from pathlib import Path

import streamlit as st

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load(filename: str) -> dict | None:
    p = DATA_DIR / filename
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def kpi_card(col, icon: str, label: str, value: str, note: str = "") -> None:
    col.markdown(
        f"""
        <div style='
            background: #1A1F2C;
            border: 1px solid #FF6B00;
            border-radius:8px;
            padding:0.8rem 1rem;
            margin-bottom:0.5rem;
        '>
            <div style='font-size:1.6rem;'>{icon}</div>
            <div style='color:#aaa; font-size:0.75rem; margin-top:0.2rem;'>{label}</div>
            <div style='color:white; font-size:1.3rem; font-weight:bold;'>{value}</div>
            <div style='color:#888; font-size:0.7rem;'>{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    st.header("🇮🇳 India Energy — Live Snapshot")

    spr     = _load("spr_status.json")
    crude   = _load("crude_latest.json")
    fuel    = _load("fuel_prices_latest.json")
    markets = _load("markets_latest.json")
    attr    = _load("attribution_latest.json")

    st.caption(
        "All figures auto-updated daily at 06:30 IST via GitHub Actions. "
        "Click any tab for full panel with charts and downloads."
    )

    # Row 1
    c1, c2, c3, c4 = st.columns(4)

    # SPR
    if spr:
        kpi_card(c1, "🛢️", "SPR Fill (Phase-1)",
                 f"{spr['fill_mmt']} MMT / {spr['fill_pct']:.0f}%",
                 f"{spr['days_of_import_cover']} days import cover")
    else:
        c1.info("SPR data unavailable")

    # Brent
    if crude:
        brent = crude.get("prices_usd_bbl", {}).get("brent")
        basket = crude.get("prices_usd_bbl", {}).get("indian_basket")
        kpi_card(c2, "📈", "Brent Crude",
                 f"${brent:,.2f}/bbl" if brent else "N/A",
                 f"Indian Basket: ${basket:,.2f}" if basket else "")
    else:
        c2.info("Crude data unavailable")

    # Fuel prices
    if fuel and fuel.get("rows"):
        rows = fuel["rows"]
        delhi = next((r for r in rows if r["city"] == "Delhi"), None)
        if delhi:
            kpi_card(c3, "⛽", "Delhi Fuel Prices",
                     f"Petrol ₹{delhi.get('petrol_per_litre', 'N/A')}/L",
                     f"Diesel ₹{delhi.get('diesel_per_litre', 'N/A')}/L")
        else:
            kpi_card(c3, "⛽", "Avg Fuel (Petrol)",
                     f"₹{sum(r.get('petrol_per_litre',0) for r in rows)/len(rows):.2f}/L",
                     f"Across {len(rows)} cities")
    else:
        c3.info("Fuel data unavailable")

    # Nifty
    if markets:
        nifty = markets.get("latest", {}).get("nifty50")
        ret   = markets.get("daily_returns_pct", {}).get("nifty50")
        inr   = markets.get("inr_per_usd")
        kpi_card(c4, "📊", "Nifty 50",
                 f"{nifty:,.0f}" if nifty else "N/A",
                 f"{ret:+.2f}% · INR/USD ₹{inr:.2f}" if ret and inr else "")
    else:
        c4.info("Market data unavailable")

    # Row 2
    st.divider()
    c5, c6, c7, c8 = st.columns(4)

    if markets:
        nifty_it = markets.get("latest", {}).get("nifty_it")
        ret_it   = markets.get("daily_returns_pct", {}).get("nifty_it")
        kpi_card(c5, "💻", "NIFTY IT (Tech/AI)",
                 f"{nifty_it:,.0f}" if nifty_it else "N/A",
                 f"{ret_it:+.2f}% today" if ret_it else "")

        gold = markets.get("latest", {}).get("gold_mcx")
        ret_g = markets.get("daily_returns_pct", {}).get("gold_mcx")
        kpi_card(c6, "🥇", "Gold",
                 f"${gold:,.2f}/oz" if gold else "N/A",
                 f"{ret_g:+.2f}% today" if ret_g else "")

    if attr:
        nifty_r = attr.get("nifty_return_today_pct", 0)
        r2      = attr.get("r_squared", 0)
        contrib = attr.get("today_contributions_pct", {})
        top_driver = max(contrib, key=lambda k: abs(contrib[k])) if contrib else "N/A"
        labels_m = attr.get("feature_labels", {})
        kpi_card(c7, "🔬", "Attribution (R²)",
                 f"{r2:.0%} explained",
                 f"Top driver today: {labels_m.get(top_driver, top_driver)}")
        kpi_card(c8, "📉", "Nifty Return Today",
                 f"{nifty_r:+.3f}%",
                 "Via regression decomposition")
    else:
        c7.info("Attribution data unavailable")

    # Data health summary
    st.divider()
    meta_p = DATA_DIR / "metadata.json"
    if meta_p.exists():
        import json as _json
        meta = _json.loads(meta_p.read_text(encoding="utf-8"))
        ok = sum(1 for v in meta.values() if v.get("status") == "ok")
        total = len(meta)
        if ok == total:
            st.success(f"✅ All {total} data sources updated successfully")
        else:
            st.warning(f"⚠️ {ok}/{total} data sources OK — check the Data Freshness expander in the sidebar")
    else:
        st.warning("Run the scrapers to populate data.")
