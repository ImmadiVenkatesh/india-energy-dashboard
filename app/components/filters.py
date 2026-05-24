"""Shared sidebar filter widgets."""
import streamlit as st


def city_filter(available_cities: list[str], key: str = "city_filter") -> list[str]:
    return st.multiselect(
        "Select cities",
        options=available_cities,
        default=available_cities[:6] if len(available_cities) >= 6 else available_cities,
        key=key,
    )


def date_range_filter(key: str = "date_range") -> tuple:
    import pandas as pd
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("From", value=pd.Timestamp.now() - pd.Timedelta(days=30), key=f"{key}_start")
    with col2:
        end = st.date_input("To", value=pd.Timestamp.now(), key=f"{key}_end")
    return start, end
