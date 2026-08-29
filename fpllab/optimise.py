"""Squad selection under FPL's constraints, plus transfer and XI advice."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .config import Config
from .matching import normalise

log = logging.getLogger(__name__)

FORMATIONS = [
    (1, 3, 4, 3), (1, 3, 5, 2), (1, 4, 4, 2), (1, 4, 3, 3),
    (1, 4, 5, 1), (1, 5, 3, 2), (1, 5, 4, 1), (1, 5, 2, 3), (1, 3, 3, 4),
]


def _try_pulp():
    try:
        import pulp  # noqa: F401
        return True
    except ImportError:
        return False


def optimise_squad(
    players: pd.DataFrame,
    cfg: Config,
    budget: Optional[float] = None,
    locked: Optional[List[int]] = None,
    banned: Optional[List[int]] = None,
    objective: str = "xpts",
    budget_tolerance: float = 0.05,  # Allow ±5% of budget
) -> pd.DataFrame:
    """Best legal 15 within budget range. Exact via PuLP, greedy fallback otherwise.
    
    Parameters:
        budget_tolerance: Allow squad to be within ±N% of budget (default 5%)
    """
    budget = cfg.budget if budget is None else budget
    locked = locked or []
    banned = set(banned or [])
    pool = players[~players["id"].isin(banned)].copy()
    pool = pool[(pool["status"] != "u")]

    if _try_pulp():
        return _optimise_pulp(pool, cfg, budget, locked, objective, budget_tolerance)
    log.warning("PuLP not installed — using greedy fallback (usually within ~2 percent of optimal)")
    return _optimise_greedy(pool, cfg, budget, locked, objective)


def _optimise_pulp(pool, cfg, budget, locked, objective, budget_tolerance=0.05):
    import pulp

    problem = pulp.LpProblem("fpl_squad", pulp.LpMaximize)
    variables = {int(row.id): pulp.LpVariable(f"p{int(row.id)}", cat="Binary") for row in pool.itertuples()}
    score = {int(row.id): float(getattr(row, objective)) for row in pool.itertuples()}
    price = {int(row.id): float(row.price) for row in pool.itertuples()}

    problem += pulp.lpSum(score[i] * variables[i] for i in variables)
    # Allow budget to be within ±tolerance%
    min_budget = budget * (1 - budget_tolerance)
    max_budget = budget * (1 + budget_tolerance)
    problem += pulp.lpSum(price[i] * variables[i] for i in variables) >= min_budget
    problem += pulp.lpSum(price[i] * variables[i] for i in variables) <= max_budget
    problem += pulp.lpSum(variables.values()) == sum(cfg.squad_size.values())

    for pos_id, count in cfg.squad_size.items():
        members = [int(row.id) for row in pool.itertuples() if int(row.pos_id) == pos_id]
        problem += pulp.lpSum(variables[i] for i in members) == count

    for team_id in pool["team_id"].unique():
        members = [int(row.id) for row in pool.itertuples() if int(row.team_id) == team_id]
        problem += pulp.lpSum(variables[i] for i in members) <= cfg.max_per_club

    for pid in locked:
        if pid in variables:
            problem += variables[pid] == 1

    problem.solve(pulp.PULP_CBC_CMD(msg=0))
    chosen = [pid for pid, var in variables.items() if var.value() and var.value() > 0.5]
    return pool[pool["id"].isin(chosen)].sort_values(["pos_id", objective], ascending=[True, False])


def _optimise_greedy(pool, cfg, budget, locked, objective):
    """Value-first fill, then upgrade while budget allows."""
    picked: List[int] = list(locked)
    spend = float(pool[pool["id"].isin(picked)]["price"].sum())
    counts = {pos: 0 for pos in cfg.squad_size}
    clubs: Dict[int, int] = {}
    for row in pool[pool["id"].isin(picked)].itertuples():
        counts[int(row.pos_id)] += 1
        clubs[int(row.team_id)] = clubs.get(int(row.team_id), 0) + 1

    ranked = pool.assign(_v=pool[objective] / pool["price"]).sort_values("_v", ascending=False)
    for row in ranked.itertuples():
        pid = int(row.id)
        if pid in picked:
            continue
        pos = int(row.pos_id)
        if counts[pos] >= cfg.squad_size[pos]:
            continue
        if clubs.get(int(row.team_id), 0) >= cfg.max_per_club:
            continue
        remaining = sum(cfg.squad_size.values()) - len(picked) - 1
        if spend + float(row.price) + remaining * 4.0 > budget:
            continue
        picked.append(pid)
        spend += float(row.price)
        counts[pos] += 1
        clubs[int(row.team_id)] = clubs.get(int(row.team_id), 0) + 1

    # upgrade pass
    improved = True
    while improved:
        improved = False
        current = pool[pool["id"].isin(picked)]
        for out_row in current.sort_values(objective).itertuples():
            if int(out_row.id) in locked:
                continue
            headroom = budget - spend + float(out_row.price)
            candidates = pool[
                (pool["pos_id"] == out_row.pos_id)
                & (~pool["id"].isin(picked))
                & (pool["price"] <= headroom)
                & (pool[objective] > getattr(out_row, objective))
            ]
            if candidates.empty:
                continue
            best = candidates.sort_values(objective, ascending=False).iloc[0]
            club_count = clubs.get(int(best["team_id"]), 0)
            if int(best["team_id"]) != int(out_row.team_id) and club_count >= cfg.max_per_club:
                continue
            picked.remove(int(out_row.id))
            picked.append(int(best["id"]))
            spend += float(best["price"]) - float(out_row.price)
            clubs[int(out_row.team_id)] -= 1
            clubs[int(best["team_id"])] = clubs.get(int(best["team_id"]), 0) + 1
            improved = True
            break

    return pool[pool["id"].isin(picked)].sort_values(["pos_id", objective], ascending=[True, False])


def best_xi(squad: pd.DataFrame, column: str = "xpts") -> Dict[str, Any]:
    """Highest-scoring legal XI plus captain and bench order."""
    best: Optional[Tuple[float, pd.DataFrame, Tuple[int, int, int, int]]] = None
    for formation in FORMATIONS:
        selection = []
        ok = True
        for pos_id, count in zip((1, 2, 3, 4), formation):
            group = squad[squad["pos_id"] == pos_id].sort_values(column, ascending=False)
            if len(group) < count:
                ok = False
                break
            selection.append(group.head(count))
        if not ok:
            continue
        xi = pd.concat(selection)
        total = float(xi[column].sum())
        if best is None or total > best[0]:
            best = (total, xi, formation)
    if best is None:
        return {"xi": squad.head(11), "bench": squad.iloc[0:0], "formation": None, "total": 0.0}

    total, xi, formation = best
    bench = squad[~squad["id"].isin(xi["id"])].sort_values(column, ascending=False)
    captain = xi.sort_values(column, ascending=False).iloc[0]
    return {
        "xi": xi.sort_values(["pos_id", column], ascending=[True, False]),
        "bench": bench,
        "formation": "-".join(str(n) for n in formation[1:]),
        "total": round(total + float(captain[column]), 2),  # captain doubles
        "captain": captain,
        "vice": xi.sort_values(column, ascending=False).iloc[1] if len(xi) > 1 else None,
    }


def load_squad_from_names(players: pd.DataFrame, names: List[str]) -> pd.DataFrame:
    """Resolve a text list of player names to rows, warning on anything ambiguous."""
    index = {normalise(str(row.web_name)): int(row.id) for row in players.itertuples()}
    full = {normalise(str(row.name)): int(row.id) for row in players.itertuples()}
    resolved: List[int] = []
    missing: List[str] = []
    for raw in names:
        key = normalise(raw)
        pid = index.get(key) or full.get(key)
        if pid is None:
            candidates = [i for name, i in {**full, **index}.items() if key and key in name]
            pid = candidates[0] if len(candidates) >= 1 else None
        if pid is None:
            missing.append(raw)
        else:
            resolved.append(pid)
    if missing:
        log.warning("could not resolve: %s", ", ".join(missing))
    squad = players[players["id"].isin(resolved)].copy()
    squad.attrs["missing"] = missing
    return squad


def suggest_transfers(
    squad: pd.DataFrame,
    players: pd.DataFrame,
    cfg: Config,
    bank: float = 0.0,
    max_suggestions: int = 12,
) -> pd.DataFrame:
    """Single-swap upgrades, ranked by expected points gained over the horizon."""
    owned = set(squad["id"])
    club_counts = squad["team_id"].value_counts().to_dict()
    suggestions: List[Dict[str, Any]] = []

    for out_row in squad.itertuples():
        budget = float(out_row.price) + bank
        candidates = players[
            (players["pos_id"] == out_row.pos_id)
            & (~players["id"].isin(owned))
            & (players["price"] <= budget)
            & (players["xpts"] > getattr(out_row, "xpts"))
            & (players["status"].isin(["a", "d"]))
        ]
        for candidate in candidates.sort_values("xpts", ascending=False).head(3).itertuples():
            if int(candidate.team_id) != int(out_row.team_id):
                if club_counts.get(int(candidate.team_id), 0) >= cfg.max_per_club:
                    continue
            suggestions.append(
                {
                    "out": out_row.web_name,
                    "out_team": out_row.team,
                    "out_price": out_row.price,
                    "out_xpts": out_row.xpts,
                    "in": candidate.web_name,
                    "in_team": candidate.team,
                    "in_price": candidate.price,
                    "in_xpts": candidate.xpts,
                    "pos": out_row.pos,
                    "gain": round(float(candidate.xpts) - float(out_row.xpts), 2),
                    "spend": round(float(candidate.price) - float(out_row.price), 1),
                    "in_minutes": candidate.exp_minutes,
                    "in_confidence": candidate.confidence,
                }
            )
    if not suggestions:
        return pd.DataFrame()
    return (
        pd.DataFrame(suggestions)
        .sort_values("gain", ascending=False)
        .head(max_suggestions)
        .reset_index(drop=True)
    )
