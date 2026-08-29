"""Understat has no public API: the data sits in the page as escaped JSON.

Each league page contains lines shaped like:
    var playersData = JSON.parse('\\x5B\\x7B\\x22id\\x22...');
so we pull the string out and unescape it.
"""
from __future__ import annotations

import codecs
import json
import logging
import re
from typing import Any, Dict, List

import requests

from .cache import Cache

log = logging.getLogger(__name__)
LEAGUE_URL = "https://understat.com/league/{league}/{season}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}


def _unescape(raw: str) -> Any:
    decoded = codecs.decode(raw, "unicode_escape")
    try:  # understat serves utf-8 that survives the escape round-trip as latin-1
        decoded = decoded.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return json.loads(decoded)


def extract_var(html: str, name: str) -> Any:
    match = re.search(rf"var\s+{name}\s*=\s*JSON\.parse\('(.+?)'\)\s*;", html, re.DOTALL)
    if not match:
        raise ValueError(f"could not find `{name}` on the page — Understat may have changed layout")
    return _unescape(match.group(1))


class UnderstatClient:
    def __init__(self, cache: Cache, timeout: int = 25):
        self.cache = cache
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _league_html(self, season: int, league: str = "EPL") -> str:
        key = f"understat::html::{league}::{season}"
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        url = LEAGUE_URL.format(league=league, season=season)
        log.debug("GET %s", url)
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        self.cache.set(key, response.text)
        return response.text

    def league(self, season: int, league: str = "EPL") -> Dict[str, Any]:
        """Returns {'players': [...], 'teams': {...}} for one season."""
        html = self._league_html(season, league)
        out: Dict[str, Any] = {"season": season, "players": [], "teams": {}}
        try:
            out["players"] = extract_var(html, "playersData")
        except ValueError as exc:
            log.warning("no player data for %s: %s", season, exc)
        try:
            out["teams"] = extract_var(html, "teamsData")
        except ValueError as exc:
            log.warning("no team data for %s: %s", season, exc)
        return out


def team_rates(teams_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Collapse each team's match history into home/away xG and xGA per game."""
    rates: Dict[str, Dict[str, float]] = {}
    for entry in teams_data.values():
        title = entry.get("title")
        history: List[Dict[str, Any]] = entry.get("history", []) or []
        if not title:
            continue
        buckets = {"h": {"xg": [], "xga": []}, "a": {"xg": [], "xga": []}}
        for match in history:
            venue = match.get("h_a", "h")
            if venue not in buckets:
                continue
            buckets[venue]["xg"].append(float(match.get("xG", 0.0)))
            buckets[venue]["xga"].append(float(match.get("xGA", 0.0)))
        played = len(history)

        def mean(values: List[float], fallback: float) -> float:
            return sum(values) / len(values) if values else fallback

        all_xg = buckets["h"]["xg"] + buckets["a"]["xg"]
        all_xga = buckets["h"]["xga"] + buckets["a"]["xga"]
        overall_xg = mean(all_xg, 1.35)
        overall_xga = mean(all_xga, 1.35)
        rates[title] = {
            "matches": float(played),
            "xg_home": mean(buckets["h"]["xg"], overall_xg),
            "xg_away": mean(buckets["a"]["xg"], overall_xg),
            "xga_home": mean(buckets["h"]["xga"], overall_xga),
            "xga_away": mean(buckets["a"]["xga"], overall_xga),
            "xg": overall_xg,
            "xga": overall_xga,
        }
    return rates
