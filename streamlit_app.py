import streamlit as st
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Run the main app
exec(open("app_v6.py").read())
