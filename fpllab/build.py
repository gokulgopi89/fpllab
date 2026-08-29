"""Pull everything, join it, and produce the projection tables."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .cache import Cache
from .config import Config
from .fixtures import build_team_strength, fixture_run, upcoming_fixtures
from .fpl_api import FPLClient
from .matching import match_players, match_teams
from .model import POSITION_NAMES, build_player_rates, project_fixture
from .understat import UnderstatClient, team_rates

log = logging.getLogger(__name__)


@dataclass
class DataBundle:
    bootstrap: Dict[str, Any]
    fixtures: List[Dict[str, Any]]
    understat_current: Dict[str, Any]
    understat_prior: Dict[str, Any]
    summaries: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    @property
    def elements(self) -> List[Dict[str, Any]]:
        return self.bootstrap["elements"]

    @property
    def teams(self) -> List[Dict[str, Any]]:
        return self.bootstrap["teams"]


def load_bundle(cfg: Config, cache: Optional[Cache] = None, deep: Optional[int] = None) -> DataBundle:
    cache = cache or Cache(ttl_seconds=cfg.cache_ttl_seconds)
    fpl = FPLClient(cache, timeout=cfg.request_timeout, max_workers=cfg.max_workers)
    understat = UnderstatClient(cache, timeout=cfg.request_timeout)

    log.info("fetching FPL bootstrap + fixtures")
    bootstrap = fpl.bootstrap()
    fixtures = fpl.fixtures()

    log.info("fetching Understat %s", cfg.season)
    current = understat.league(cfg.season)
    prior: Dict[str, Any] = {"players": [], "teams": {}}
    if cfg.include_prior_season:
        try:
            prior = understat.league(cfg.season - 1)
        except Exception as exc:  # noqa: BLE001
            log.warning("prior season pull failed: %s", exc)

    limit = cfg.deep_fetch_players if deep is None else deep
    summaries: Dict[int, Dict[str, Any]] = {}
    if limit:
        ranked = sorted(
            bootstrap["elements"],
            key=lambda e: (float(e.get("selected_by_percent") or 0), e.get("now_cost", 0)),
            reverse=True,
        )[:limit]
        log.info("fetching per-player history for %d players", len(ranked))
        summaries = fpl.element_summaries([e["id"] for e in ranked])

    return DataBundle(bootstrap, fixtures, current, prior, summaries)


def _gws_played(bootstrap: Dict[str, Any]) -> int:
    return sum(1 for event in bootstrap["events"] if event.get("finished"))


def resolve_start_gw(bootstrap: Dict[str, Any]) -> int:
    for event in bootstrap["events"]:
        if event.get("is_next"):
            return event["id"]
    for event in bootstrap["events"]:
        if not event.get("finished"):
            return event["id"]
    return 1


def build_projections(
    bundle: DataBundle,
    cfg: Config,
    start_gw: Optional[int] = None,
) -> Dict[str, Any]:
    bootstrap = bundle.bootstrap
    start_gw = start_gw or resolve_start_gw(bootstrap)
    horizon = cfg.horizon_gws

    understat_titles = [
        entry.get("title") for entry in bundle.understat_current.get("teams", {}).values() if entry.get("title")
    ]
    if not understat_titles:
        understat_titles = [
            entry.get("title") for entry in bundle.understat_prior.get("teams", {}).values() if entry.get("title")
        ]
    team_map = match_teams(bundle.teams, understat_titles)

    rates_current = team_rates(bundle.understat_current.get("teams", {}))
    rates_prior = team_rates(bundle.understat_prior.get("teams", {}))
    combined = dict(rates_prior)
    for title, values in rates_current.items():
        if values.get("matches", 0) >= 5:
            combined[title] = values
        elif title in combined:  # early season: nudge last season's baseline
            blended = dict(combined[title])
            weight = values.get("matches", 0) / 5.0
            for key in ("xg_home", "xg_away", "xga_home", "xga_away", "xg", "xga"):
                blended[key] = (1 - weight) * blended[key] + weight * values[key]
            combined[title] = blended
        else:
            combined[title] = values

    strength = build_team_strength(
        bundle.teams, team_map, combined, blend=cfg.strength_blend_understat
    )
    schedule = upcoming_fixtures(bundle.fixtures, start_gw, horizon)

    us_current = match_players(bundle.elements, bundle.understat_current.get("players", []), team_map)
    us_prior = match_players(bundle.elements, bundle.understat_prior.get("players", []), team_map)
    log.info("matched %d current / %d prior Understat rows", len(us_current), len(us_prior))

    player_rates = build_player_rates(
        bundle.elements, us_current, us_prior, bundle.summaries, cfg, _gws_played(bootstrap)
    )

    team_lookup = {team["id"]: team for team in bundle.teams}
    baseline: Dict[int, float] = {}
    fixture_rows: List[Dict[str, Any]] = []
    runs: Dict[int, List[Dict[str, Any]]] = {}
    for team_id in team_lookup:
        run = fixture_run(team_id, schedule, strength, cfg.home_advantage_goals)
        runs[team_id] = run
        baseline[team_id] = (sum(f["xgf"] for f in run) / len(run)) if run else 1.35
        for fixture in run:
            fixture_rows.append(
                {
                    "team": team_lookup[team_id]["short_name"],
                    "team_id": team_id,
                    "gw": fixture["gw"],
                    "opponent": fixture["opponent_short"],
                    "venue": "H" if fixture["is_home"] else "A",
                    "fdr": fixture["fdr"],
                    "xgf": round(fixture["xgf"], 2),
                    "xga": round(fixture["xga"], 2),
                }
            )

    gw_columns = [f"gw{gw}" for gw in range(start_gw, start_gw + horizon)]
    rows: List[Dict[str, Any]] = []
    for element in bundle.elements:
        pid = element["id"]
        rates = player_rates[pid]
        team_id = element["team"]
        team = team_lookup[team_id]
        run = runs.get(team_id, [])
        row: Dict[str, Any] = {
            "id": pid,
            "name": f"{element.get('first_name','')} {element.get('second_name','')}".strip(),
            "web_name": element.get("web_name"),
            "team": team["short_name"],
            "team_id": team_id,
            "pos": POSITION_NAMES.get(element.get("element_type", 3), "?"),
            "pos_id": element.get("element_type", 3),
            "price": element.get("now_cost", 0) / 10.0,
            "selected_by": float(element.get("selected_by_percent") or 0),
            "status": rates["status"],
            "news": rates["news"],
            "exp_minutes": round(rates["exp_minutes"], 1),
            "npxg90": round(rates["npxg90"], 3),
            "xa90": round(rates["xa90"], 3),
            "bps90": round(rates["bps90"], 1),
            "p_defcon": round(rates["p_defcon"], 2),
            "pen_share": rates["pen_share"],
            "confidence": rates["confidence"],
            "understat_matched": pid in us_current or pid in us_prior,
        }
        total = 0.0
        goals = assists = clean_sheets = 0.0
        per_gw: Dict[int, float] = {}
        for fixture in run:
            projection = project_fixture(element, rates, fixture, baseline[team_id], cfg)
            per_gw[fixture["gw"]] = per_gw.get(fixture["gw"], 0.0) + projection["xpts"]
            total += projection["xpts"]
            goals += projection["goals"]
            assists += projection["assists"]
            clean_sheets += projection["cs"]
        for gw in range(start_gw, start_gw + horizon):
            row[f"gw{gw}"] = round(per_gw.get(gw, 0.0), 2)
        row["fixtures"] = " ".join(
            f"{f['opponent_short']}({'H' if f['is_home'] else 'A'})" for f in run
        )
        row["n_fixtures"] = len(run)
        row["xpts"] = round(total, 2)
        row["xpts_per_gw"] = round(total / max(horizon, 1), 2)
        row["value"] = round(total / max(row["price"], 0.1), 2)
        row["x_goals"] = round(goals, 2)
        row["x_assists"] = round(assists, 2)
        row["x_cs"] = round(clean_sheets, 2)
        rows.append(row)

    players = pd.DataFrame(rows).sort_values("xpts", ascending=False).reset_index(drop=True)
    fixtures_df = pd.DataFrame(fixture_rows).sort_values(["team", "gw"]).reset_index(drop=True)
    strength_df = (
        pd.DataFrame(
            [
                {
                    "team": values.get("short", ""),
                    "name": values.get("name", ""),
                    "att_home": round(values.get("att_home", 1.0), 3),
                    "att_away": round(values.get("att_away", 1.0), 3),
                    "def_home": round(values.get("def_home", 1.0), 3),
                    "def_away": round(values.get("def_away", 1.0), 3),
                    "source": values.get("source", ""),
                }
                for values in strength.values()
            ]
        )
        .sort_values("att_home", ascending=False)
        .reset_index(drop=True)
    )

    return {
        "players": players,
        "fixtures": fixtures_df,
        "team_strength": strength_df,
        "start_gw": start_gw,
        "gw_columns": gw_columns,
    }
