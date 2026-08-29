"""Fixture schedule, and how hard each one actually is.

FDR is a hand-set 1-5 rating. We use it only as a fallback and as a display
column; the real difficulty comes from expected goals for/against, built from
Understat match history blended with FPL's own strength ratings (which are the
only signal available for newly promoted sides).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

LEAGUE_MEAN_GOALS = 1.42  # per team per game, long-run Premier League average


def upcoming_fixtures(
    fixtures: List[Dict[str, Any]],
    start_gw: int,
    horizon: int,
) -> Dict[int, List[Dict[str, Any]]]:
    """team_id -> list of fixtures in [start_gw, start_gw + horizon).

    Naturally handles blanks (no entry for that GW) and doubles (two entries).
    """
    window = range(start_gw, start_gw + horizon)
    out: Dict[int, List[Dict[str, Any]]] = {}
    for fixture in fixtures:
        event = fixture.get("event")
        if event is None or event not in window:
            continue
        for side, opp_side, is_home in (("team_h", "team_a", True), ("team_a", "team_h", False)):
            team_id = fixture[side]
            out.setdefault(team_id, []).append(
                {
                    "gw": event,
                    "fixture_id": fixture.get("id"),
                    "opponent": fixture[opp_side],
                    "is_home": is_home,
                    "fdr": fixture.get("team_h_difficulty" if is_home else "team_a_difficulty", 3),
                    "kickoff": fixture.get("kickoff_time"),
                }
            )
    for team_id in out:
        out[team_id].sort(key=lambda f: (f["gw"], f["kickoff"] or ""))
    return out


def _fpl_strength_rates(teams: List[Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
    """Convert FPL's 1000-1400 strength scale into goals-per-game style indices."""
    attack_home = [t.get("strength_attack_home", 1100) for t in teams]
    attack_away = [t.get("strength_attack_away", 1100) for t in teams]
    defence_home = [t.get("strength_defence_home", 1100) for t in teams]
    defence_away = [t.get("strength_defence_away", 1100) for t in teams]
    mean_ah = sum(attack_home) / max(len(attack_home), 1)
    mean_aa = sum(attack_away) / max(len(attack_away), 1)
    mean_dh = sum(defence_home) / max(len(defence_home), 1)
    mean_da = sum(defence_away) / max(len(defence_away), 1)

    # Safety: ensure means are never zero
    mean_ah = max(mean_ah, 1100)
    mean_aa = max(mean_aa, 1100)
    mean_dh = max(mean_dh, 1100)
    mean_da = max(mean_da, 1100)

    rates: Dict[int, Dict[str, float]] = {}
    for team in teams:
        rates[team["id"]] = {
            "att_home": team.get("strength_attack_home", mean_ah) / mean_ah,
            "att_away": team.get("strength_attack_away", mean_aa) / mean_aa,
            # higher defence strength = better defence = concedes fewer
            "def_home": mean_dh / max(team.get("strength_defence_home", mean_dh), 1),
            "def_away": mean_da / max(team.get("strength_defence_away", mean_da), 1),
        }
    return rates

def build_team_strength(
    teams: List[Dict[str, Any]],
    team_map: Dict[int, str],
    understat_rates: Dict[str, Dict[str, float]],
    blend: float = 0.65,
    min_matches: int = 8,
) -> Dict[int, Dict[str, float]]:
    """team_id -> attack/defence indices where 1.0 is a league-average side."""
    fpl_rates = _fpl_strength_rates(teams)

    usable = {
        title: rates
        for title, rates in understat_rates.items()
        if rates.get("matches", 0) >= min_matches
    }
    if usable:
        league_xg_home = sum(r["xg_home"] for r in usable.values()) / len(usable)
        league_xg_away = sum(r["xg_away"] for r in usable.values()) / len(usable)
        league_xga_home = sum(r["xga_home"] for r in usable.values()) / len(usable)
        league_xga_away = sum(r["xga_away"] for r in usable.values()) / len(usable)
        # Ensure we never divide by zero
        league_xg_home = max(league_xg_home, LEAGUE_MEAN_GOALS)
        league_xg_away = max(league_xg_away, LEAGUE_MEAN_GOALS)
        league_xga_home = max(league_xga_home, LEAGUE_MEAN_GOALS)
        league_xga_away = max(league_xga_away, LEAGUE_MEAN_GOALS)
    else:
        league_xg_home = league_xg_away = league_xga_home = league_xga_away = LEAGUE_MEAN_GOALS
        
    out: Dict[int, Dict[str, float]] = {}
    for team in teams:
        team_id = team["id"]
        base = dict(fpl_rates.get(team_id, {"att_home": 1.0, "att_away": 1.0, "def_home": 1.0, "def_away": 1.0}))
        title = team_map.get(team_id)
        rates = usable.get(title) if title else None
        if rates:
            understat_view = {
                "att_home": rates["xg_home"] / league_xg_home,
                "att_away": rates["xg_away"] / league_xg_away,
                "def_home": rates["xga_home"] / league_xga_home,
                "def_away": rates["xga_away"] / league_xga_away,
            }
            for key in base:
                base[key] = blend * understat_view[key] + (1 - blend) * base[key]
            base["source"] = "understat+fpl"
            base["matches"] = rates["matches"]
        else:
            base["source"] = "fpl-only"
            base["matches"] = 0.0
        base["name"] = team.get("name", "")
        base["short"] = team.get("short_name", "")
        out[team_id] = base
    return out


def expected_goals(
    team_id: int,
    opponent_id: int,
    is_home: bool,
    strength: Dict[int, Dict[str, float]],
    home_advantage: float = 0.20,
) -> Dict[str, float]:
    """Expected goals scored and conceded by `team_id` in this fixture."""
    team = strength.get(team_id, {})
    opponent = strength.get(opponent_id, {})
    att = team.get("att_home" if is_home else "att_away", 1.0)
    opp_def = opponent.get("def_away" if is_home else "def_home", 1.0)
    opp_att = opponent.get("att_away" if is_home else "att_home", 1.0)
    own_def = team.get("def_home" if is_home else "def_away", 1.0)

    edge = home_advantage / 2
    scored = LEAGUE_MEAN_GOALS * att * opp_def + (edge if is_home else -edge)
    conceded = LEAGUE_MEAN_GOALS * opp_att * own_def + (-edge if is_home else edge)
    return {"xgf": max(scored, 0.15), "xga": max(conceded, 0.15)}


def fixture_run(
    team_id: int,
    schedule: Dict[int, List[Dict[str, Any]]],
    strength: Dict[int, Dict[str, float]],
    home_advantage: float = 0.20,
) -> List[Dict[str, Any]]:
    """Annotate a team's fixture list with expected goals both ways."""
    rows = []
    for fixture in schedule.get(team_id, []):
        goals = expected_goals(team_id, fixture["opponent"], fixture["is_home"], strength, home_advantage)
        row = dict(fixture)
        row.update(goals)
        row["opponent_short"] = strength.get(fixture["opponent"], {}).get("short", "?")
        rows.append(row)
    return rows
