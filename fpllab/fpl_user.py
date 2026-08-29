"""Fetch user squad and data directly from FPL API."""
import requests
import pandas as pd
from typing import Dict, List, Tuple


def fetch_user_squad(user_id: int) -> Tuple[pd.DataFrame, Dict]:
    """
    Fetch user's current squad from FPL API.
    
    Args:
        user_id: FPL user ID (e.g., 2616028)
    
    Returns:
        (squad_df, metadata) where squad_df has columns:
        - id, name, team, position, price, points, status
    """
    try:
        # Fetch user data
        url = f"https://fantasy.premierleague.com/api/entry/{user_id}/"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        user_data = resp.json()
        
        # Fetch user picks (current gameweek)
        picks_url = f"https://fantasy.premierleague.com/api/entry/{user_id}/event/{user_data['current_event']}/picks/"
        picks_resp = requests.get(picks_url, timeout=10)
        picks_resp.raise_for_status()
        picks = picks_resp.json()["picks"]
        
        # Fetch bootstrap (all player data)
        bootstrap_url = "https://fantasy.premierleague.com/api/bootstrap-static/"
        bootstrap_resp = requests.get(bootstrap_url, timeout=10)
        bootstrap_resp.raise_for_status()
        bootstrap = bootstrap_resp.json()
        
        # Create player lookup
        elements = {e["id"]: e for e in bootstrap["elements"]}
        teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
        
        # Build squad dataframe
        squad_data = []
        for pick in picks:
            pid = pick["element"]
            player = elements[pid]
            squad_data.append({
                "id": pid,
                "web_name": player["web_name"],
                "team": teams[player["team"]],
                "pos": {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}[player["element_type"]],
                "pos_id": player["element_type"],
                "price": player["now_cost"] / 10.0,
                "points": player.get("total_points", 0),
                "status": player["status"],
                "is_captain": pick["is_captain"],
                "is_vice_captain": pick["is_vice_captain"],
                "multiplier": pick["multiplier"],
            })
        
        squad_df = pd.DataFrame(squad_data)
        
        metadata = {
            "user_id": user_id,
            "team_name": user_data.get("name"),
            "gameweek": user_data.get("current_event"),
            "total_points": user_data.get("summary_overall_points"),
            "rank": user_data.get("summary_overall_rank"),
            "bank": user_data.get("last_deadline_bank", 0) / 10.0,
            "transfers_left": user_data.get("transfers_available"),
        }
        
        return squad_df, metadata
    
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch FPL data: {e}")


def get_user_history(user_id: int) -> pd.DataFrame:
    """Get user's history of points by gameweek."""
    try:
        url = f"https://fantasy.premierleague.com/api/entry/{user_id}/history/"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        
        history = resp.json()["current"]
        df = pd.DataFrame(history)
        return df
    except:
        return pd.DataFrame()
