"""Joining FPL and Understat is the part that quietly breaks. Handle it explicitly."""
from __future__ import annotations

import difflib
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# Only the names that fuzzy matching genuinely struggles with.
TEAM_ALIASES = {
    "man city": "Manchester City",
    "man utd": "Manchester United",
    "spurs": "Tottenham",
    "nott'm forest": "Nottingham Forest",
    "wolves": "Wolverhampton Wanderers",
    "sheffield utd": "Sheffield United",
    "newcastle": "Newcastle United",
    "west ham": "West Ham",
    "brighton": "Brighton",
    "leeds": "Leeds",
    "leicester": "Leicester",
    "ipswich": "Ipswich",
    "luton": "Luton",
    "norwich": "Norwich",
    "coventry": "Coventry",
    "hull": "Hull City",
    "west brom": "West Bromwich Albion",
    "qpr": "Queens Park Rangers",
}


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("-", " ").replace("'", "")
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def match_teams(fpl_teams: List[Dict[str, Any]], understat_titles: List[str]) -> Dict[int, str]:
    """FPL team id -> Understat team title."""
    lookup = {normalise(title): title for title in understat_titles}
    mapping: Dict[int, str] = {}
    for team in fpl_teams:
        candidates = [team.get("name", ""), team.get("short_name", "")]
        alias = TEAM_ALIASES.get((team.get("name") or "").lower())
        if alias:
            candidates.insert(0, alias)
        found = None
        for candidate in candidates:
            key = normalise(candidate)
            if key in lookup:
                found = lookup[key]
                break
        if not found:
            close = difflib.get_close_matches(normalise(team.get("name", "")), lookup.keys(), n=1, cutoff=0.6)
            if close:
                found = lookup[close[0]]
        if found:
            mapping[team["id"]] = found
        else:
            log.info("no Understat team match for %s (likely newly promoted)", team.get("name"))
    return mapping


def _player_keys(first: str, second: str, web: str) -> List[str]:
    keys = [
        normalise(f"{first} {second}"),
        normalise(second),
        normalise(web),
        normalise(f"{first[:1]} {second}") if first else "",
    ]
    return [k for k in keys if k]


def match_players(
    elements: List[Dict[str, Any]],
    understat_players: List[Dict[str, Any]],
    team_map: Dict[int, str],
) -> Dict[int, Dict[str, Any]]:
    """FPL element id -> Understat player row. Team-constrained, then fuzzy."""
    by_team: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for row in understat_players:
        title = row.get("team_title", "")
        # a player transferred mid-season shows as "Team A,Team B"
        for part in str(title).split(","):
            by_team.setdefault(part.strip(), []).append((normalise(row.get("player_name", "")), row))

    global_index = [(normalise(r.get("player_name", "")), r) for r in understat_players]
    matched: Dict[int, Dict[str, Any]] = {}

    for element in elements:
        keys = _player_keys(
            element.get("first_name", ""), element.get("second_name", ""), element.get("web_name", "")
        )
        pool = by_team.get(team_map.get(element.get("team"), ""), [])
        hit: Optional[Dict[str, Any]] = None

        for key in keys:
            for name, row in pool:
                if name == key or name.endswith(f" {key}") or key.endswith(f" {name}"):
                    hit = row
                    break
            if hit:
                break

        if hit is None and pool:
            names = [n for n, _ in pool]
            close = difflib.get_close_matches(keys[0], names, n=1, cutoff=0.82)
            if close:
                hit = dict(pool)[close[0]] if False else next(r for n, r in pool if n == close[0])

        if hit is None:  # last resort: league-wide exact full-name match
            for key in keys[:1]:
                for name, row in global_index:
                    if name == key:
                        hit = row
                        break
                if hit:
                    break

        if hit is not None:
            matched[element["id"]] = hit
    return matched
