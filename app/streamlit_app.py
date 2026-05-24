"""
India Energy Intelligence Dashboard
Entry point for Streamlit Community Cloud.
"""
import sys
from pathlib import Path

# Ensure project root is on the path (needed for Streamlit Cloud)
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.components.header import render_header, render_metadata_banner
from app.panels import attribution, crude, fuel_prices, lng, markets, overview, spr

st.set_page_config(
    page_title="India Energy Dashboard",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Global CSS tweaks
st.markdown(
    """
    <style>
    .block-container { padding-top: 1rem; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: #aaa !important; }
    .stTabs [data-baseweb="tab"] { font-size: 0.9rem; padding: 6px 14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

render_header()
render_metadata_banner()

tabs = st.tabs([
    "🏠 Overview",
    "🛢️ SPR",
    "⛽ Fuel Prices",
    "📈 Crude",
    "🧊 LNG",
    "📊 Markets",
    "🔬 Attribution",
])

with tabs[0]:
    overview.render()

with tabs[1]:
    spr.render()

with tabs[2]:
    fuel_prices.render()

with tabs[3]:
    crude.render()

with tabs[4]:
    lng.render()

with tabs[5]:
    markets.render()

with tabs[6]:
    attribution.render()

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align:center; color:#555; font-size:0.75rem; padding: 0.5rem 0;'>
    India Energy Intelligence Dashboard · Open source · MIT License ·
    Data updated daily at 06:30 IST via GitHub Actions ·
    <a href='https://github.com/ImmadiVenkatesh/india-energy-dashboard' style='color:#FF6B00;'>GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)
