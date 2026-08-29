"""Squad builder module — logic for building and formatting optimal squads."""
from __future__ import annotations

import pandas as pd

from .config import Config
from .optimise import best_xi, optimise_squad


def build_best_squad(
    players: pd.DataFrame,
    cfg: Config,
    budget: float = 100.0,
    locked_names: list[str] | None = None,
) -> dict:
    """
    Build the best legal squad given budget and locked players.
    
    Returns dict with:
        - squad: DataFrame of 15 players
        - xi: dict with XI, captain, vice, formation, total
        - locked: list of locked player names
        - missing: list of names that couldn't be resolved
    """
    locked = []
    missing = []
    
    if locked_names:
        for name in locked_names:
            matches = players[players["web_name"].str.contains(name, case=False, na=False)]
            if matches.empty:
                missing.append(name)
            else:
                locked.append(int(matches.iloc[0]["id"]))
    
    squad = optimise_squad(players, cfg, budget=budget, locked=locked)
    xi = best_xi(squad)
    
    return {
        "squad": squad,
        "xi": xi,
        "locked": locked_names or [],
        "missing": missing,
        "budget": budget,
    }


def format_squad_table(squad: pd.DataFrame) -> pd.DataFrame:
    """Format squad for table display."""
    return squad[[
        "web_name", "team", "pos", "price", "exp_minutes",
        "npxg90", "xa90", "fixtures", "xpts", "value", "confidence"
    ]].sort_values(["pos", "xpts"], ascending=[True, False]).reset_index(drop=True)


def format_xi_table(xi: dict) -> pd.DataFrame:
    """Format XI for table display."""
    return xi["xi"][[
        "web_name", "team", "pos", "price", "exp_minutes", "fixtures", "xpts"
    ]].reset_index(drop=True)


def format_bench_table(xi: dict, rows: int = 4) -> pd.DataFrame:
    """Format bench in order."""
    return xi["bench"][[
        "web_name", "team", "pos", "price", "xpts"
    ]].head(rows).reset_index(drop=True)


def export_squad_csv(squad: pd.DataFrame, path: str) -> None:
    """Export squad to CSV."""
    squad[[
        "web_name", "team", "pos", "price", "exp_minutes",
        "npxg90", "xa90", "fixtures", "xpts", "value", "confidence"
    ]].to_csv(path, index=False)
