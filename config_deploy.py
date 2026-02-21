"""
Kickbase Dashboard Configuration - DEPLOYMENT VERSION
Uses Streamlit secrets for sensitive data
"""
import streamlit as st

# Try to load from Streamlit secrets (deployment)
# Fall back to environment variables or defaults
try:
    EMAIL = st.secrets["kickbase"]["email"]
    PASSWORD = st.secrets["kickbase"]["password"]
    ODDS_API_KEY = st.secrets["api"]["odds_api_key"]
    DEFAULT_LEAGUE_ID = st.secrets["leagues"]["default_league_id"]
except:
    # Fallback for local development without secrets
    EMAIL = "skinsstar06@gmail.com"
    PASSWORD = ""  # Will prompt for login
    ODDS_API_KEY = ""
    DEFAULT_LEAGUE_ID = "9830869"

# API Configuration
BASE_URL = "https://api.kickbase.com/v4"

# Your Leagues
LEAGUES = {
    "matchweek_challenge": {
        "id": "9830869",
        "name": "MLS Matchweek Challenge #1"
    },
    "season_challenge": {
        "id": "9860187",
        "name": "MLS Season Challenge 2026"
    },
    "red_bull": {
        "id": "9810244",
        "name": "Red Bull Fantasy"
    }
}

# Dashboard Settings
USE_REAL_API = True
PORT = 8523
