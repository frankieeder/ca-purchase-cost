import streamlit as st

PERCENT_MAX = 100


def percentage_input(label, value=None) -> float:
    percentage = st.number_input(
        label=label,
        min_value=0.0,
        max_value=100.0,
        value=value,
        step=1.0
    )
    percentage /= PERCENT_MAX
    return percentage
