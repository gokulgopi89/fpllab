import streamlit as st

st.set_page_config(page_title="FPLlab", layout="wide")

st.title("⚽ FPLlab - Squad Optimizer")
st.write("Welcome to FPLlab!")

# Test if basic dependencies work
try:
    import pandas as pd
    import plotly
    import requests
    st.success("✅ All dependencies loaded!")
except Exception as e:
    st.error(f"❌ Import error: {e}")

# Simple test
st.write("App is running successfully!")
