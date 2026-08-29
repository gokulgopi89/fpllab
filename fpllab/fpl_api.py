"""Client for the public Fantasy Premier League endpoints (no auth required)."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List, Optional

import requests

from .cache import Cache

log = logging.getLogger(__name__)
BASE = "https://fantasy.premierleague.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}


class FPLClient:
    def __init__(self, cache: Cache, timeout: int = 25, max_workers: int = 6):
        self.cache = cache
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get(self, path: str, ttl_key: Optional[str] = None, use_cache: bool = True) -> Any:
        key = ttl_key or f"fpl::{path}"
        if use_cache:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        url = f"{BASE}/{path.lstrip('/')}"
        log.debug("GET %s", url)
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        self.cache.set(key, data)
        return data

    # --- core static data -------------------------------------------------
    def bootstrap(self) -> Dict[str, Any]:
        """Players (`elements`), teams, positions (`element_types`), gameweeks."""
        return self._get("bootstrap-static/")

    def fixtures(self) -> List[Dict[str, Any]]:
        return self._get("fixtures/")

    def element_summary(self, player_id: int) -> Dict[str, Any]:
        """Per-GW history for the current season plus `history_past` season totals."""
        return self._get(f"element-summary/{player_id}/")

    def element_summaries(self, player_ids: Iterable[int]) -> Dict[int, Dict[str, Any]]:
        ids = list(player_ids)
        out: Dict[int, Dict[str, Any]] = {}

        def fetch(pid: int):
            try:
                return pid, self.element_summary(pid)
            except Exception as exc:  # noqa: BLE001 - one bad player shouldn't kill the run
                log.warning("element-summary %s failed: %s", pid, exc)
                return pid, None

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            for pid, payload in pool.map(fetch, ids):
                if payload:
                    out[pid] = payload
        return out

    # --- a manager's own team --------------------------------------------
    def entry(self, entry_id: int) -> Dict[str, Any]:
        return self._get(f"entry/{entry_id}/")

    def entry_picks(self, entry_id: int, gameweek: int) -> Dict[str, Any]:
        """Only available once that gameweek has kicked off."""
        return self._get(f"entry/{entry_id}/event/{gameweek}/picks/")

    def current_gameweek(self) -> int:
        events = self.bootstrap()["events"]
        for event in events:
            if event.get("is_current"):
                return event["id"]
        for event in events:
            if event.get("is_next"):
                return event["id"]
        return 1

    def next_gameweek(self) -> int:
        for event in self.bootstrap()["events"]:
            if event.get("is_next"):
                return event["id"]
        finished = [e["id"] for e in self.bootstrap()["events"] if e.get("finished")]
        return (max(finished) + 1) if finished else 1
