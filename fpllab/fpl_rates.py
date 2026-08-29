"""Calculate expected points and rates directly from FPL API data.

When Understat data is unavailable, derive rates from FPL history.
This is more reliable than shrinking to positional means.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


def _f(value: Any, default: float = 0.0) -> float:
    """Safely convert to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_fpl_rates(
    elements: List[Dict[str, Any]],
    summaries: Dict[int, Dict[str, Any]],
    gws_played: int = 0,
) -> Dict[int, Dict[str, float]]:
    """
    Calculate npxG90 and xA90 from FPL data when Understat is unavailable.

    For each player, uses their FPL history to estimate:
    - Goals per 90 (proxy for xG)
    - Assists per 90 (proxy for xA)
    - Minutes per appearance

    Parameters:
        elements: FPL bootstrap elements (players)
        summaries: FPL element-summary data per player
        gws_played: Gameweeks completed this season

    Returns:
        Dict mapping player_id -> {"goals90": ..., "assists90": ..., "minutes_per_game": ...}
    """
    rates = {}

    for element in elements:
        pid = element["id"]
        summary = summaries.get(pid, {})
        position = element.get("element_type", 3)

        # Current season history
        history = summary.get("history", []) or []
        past = summary.get("history_past", []) or []

        # Aggregate current season
        goals_current = sum(_f(h.get("goals")) for h in history)
        assists_current = sum(_f(h.get("assists")) for h in history)
        minutes_current = sum(_f(h.get("minutes")) for h in history)
        games_current = len([h for h in history if _f(h.get("minutes")) >= 60])

        # Aggregate past season (as backup)
        goals_past = sum(_f(h.get("goals")) for h in past)
        assists_past = sum(_f(h.get("assists")) for h in past)
        minutes_past = sum(_f(h.get("minutes")) for h in past)
        games_past = len([h for h in past if _f(h.get("minutes")) >= 60])

        # Use current season if available, else past
        if minutes_current > 0:
            goals90 = (goals_current / minutes_current) * 90
            assists90 = (assists_current / minutes_current) * 90
            minutes_per_game = minutes_current / max(games_current, 1)
            source = "fpl_current"
        elif minutes_past > 0:
            goals90 = (goals_past / minutes_past) * 90
            assists90 = (assists_past / minutes_past) * 90
            minutes_per_game = minutes_past / max(games_past, 1)
            source = "fpl_past"
        else:
            # Fallback: position average (estimate from role)
            position_averages = {
                1: {"goals90": 0.0, "assists90": 0.05},  # GK rarely scores
                2: {"goals90": 0.08, "assists90": 0.09},  # DEF
                3: {"goals90": 0.15, "assists90": 0.12},  # MID
                4: {"goals90": 0.35, "assists90": 0.08},  # FWD
            }
            avg = position_averages.get(position, {"goals90": 0.1, "assists90": 0.1})
            goals90 = avg["goals90"]
            assists90 = avg["assists90"]
            minutes_per_game = {1: 90, 2: 75, 3: 65, 4: 60}.get(position, 70)
            source = "position_average"

        # Bonus points: estimated from BPS
        bps_total = _f(element.get("bps"))
        minutes_total = _f(element.get("minutes"))
        if minutes_total < 270 and past:
            bps_total += _f(past[-1].get("bps"))
            minutes_total += _f(past[-1].get("minutes"))
        bps90 = (bps_total / minutes_total * 90) if minutes_total > 0 else 0.0

        # Saves (GK only)
        saves_total = _f(element.get("saves"))
        save_minutes = _f(element.get("minutes"))
        if save_minutes < 270 and past:
            saves_total += _f(past[-1].get("saves"))
            save_minutes += _f(past[-1].get("minutes"))
        saves90 = (saves_total / save_minutes * 90) if save_minutes > 0 else 0.0

        rates[pid] = {
            "goals90": goals90,
            "assists90": assists90,
            "minutes_per_game": minutes_per_game,
            "bps90": bps90,
            "saves90": saves90,
            "source": source,
            "minutes_current": minutes_current,
            "goals_current": goals_current,
            "assists_current": assists_current,
        }

    return rates


def player_form_stats(
    element: Dict[str, Any],
    summary: Optional[Dict[str, Any]],
    gws: int = 5,
) -> Dict[str, float]:
    """
    Calculate player's recent form over last N gameweeks.

    Returns:
        Dict with: goals, assists, minutes, avg_points, games_played
    """
    if not summary:
        return {
            "goals": 0.0,
            "assists": 0.0,
            "minutes": 0.0,
            "avg_points": 0.0,
            "games": 0,
        }

    history = summary.get("history", []) or []
    if not history:
        return {
            "goals": 0.0,
            "assists": 0.0,
            "minutes": 0.0,
            "avg_points": 0.0,
            "games": 0,
        }

    recent = history[-gws:] if len(history) >= gws else history
    goals = sum(_f(h.get("goals")) for h in recent)
    assists = sum(_f(h.get("assists")) for h in recent)
    minutes = sum(_f(h.get("minutes")) for h in recent)
    points = sum(_f(h.get("total_points")) for h in recent)
    games = len([h for h in recent if _f(h.get("minutes")) >= 1])

    avg_points = points / max(games, 1)
    minutes_per_game = minutes / max(games, 1)

    return {
        "goals": goals,
        "assists": assists,
        "minutes": minutes,
        "avg_points": round(avg_points, 2),
        "games": games,
        "minutes_per_game": round(minutes_per_game, 1),
    }
