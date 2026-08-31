# Streamlit app entry point for Render deployment
import subprocess
import sys

try:
    import streamlit
    import plotly
    import pandas
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

exec(open("app_v6.py").read())
