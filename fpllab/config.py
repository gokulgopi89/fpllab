"""Every assumption in the model lives here so you can argue with it."""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional


def current_season_start_year(today: Optional[_dt.date] = None) -> int:
    """Understat labels 2026/27 as '2026'. Season rolls over in July."""
    today = today or _dt.date.today()
    return today.year if today.month >= 7 else today.year - 1


@dataclass
class Config:
    # --- scope -------------------------------------------------------------
    horizon_gws: int = 5
    season: int = field(default_factory=current_season_start_year)
    include_prior_season: bool = True

    # --- data pulling ------------------------------------------------------
    cache_ttl_seconds: int = 6 * 3600
    deep_fetch_players: int = 260   # per-player FPL history pulls (0 = skip)
    request_timeout: int = 25
    max_workers: int = 6

    # --- rate blending -----------------------------------------------------
    prior_season_weight: float = 0.55   # discount applied to last season's minutes
    shrinkage_minutes: float = 420.0    # pull toward positional mean by this much
    min_minutes_for_rate: float = 180.0

    # --- fixture model -----------------------------------------------------
    home_advantage_goals: float = 0.20   # goals added to home side's expectation
    strength_blend_understat: float = 0.65  # rest from FPL's own strength ratings
    max_fixture_multiplier: float = 1.60
    min_fixture_multiplier: float = 0.55

    # --- scoring -----------------------------------------------------------
    goal_points: Dict[int, int] = field(default_factory=lambda: {1: 10, 2: 6, 3: 5, 4: 4})
    clean_sheet_points: Dict[int, int] = field(default_factory=lambda: {1: 4, 2: 4, 3: 1, 4: 0})
    assist_points: int = 3
    save_points_per_save: float = 1 / 3
    concede_penalty_per_goal: Dict[int, float] = field(
        default_factory=lambda: {1: -0.5, 2: -0.5, 3: 0.0, 4: 0.0}
    )
    defcon_points: int = 2
    defcon_enabled: bool = True

    # bonus proxy: expected bonus = clip((bps90 - floor) / divisor, 0, cap)
    bps_floor: float = 19.0
    bps_divisor: float = 11.0
    bonus_cap: float = 2.4

    # penalties
    penalty_conversion: float = 0.79
    team_penalties_per_game: float = 0.13  # league-average rate, scaled by attack

    # --- availability ------------------------------------------------------
    rotation_floor_minutes: float = 20.0
    injury_status_multiplier: Dict[str, float] = field(
        default_factory=lambda: {"a": 1.0, "d": 0.5, "i": 0.0, "s": 0.0, "u": 0.0, "n": 0.0}
    )

    # --- squad rules -------------------------------------------------------
    squad_size: Dict[int, int] = field(default_factory=lambda: {1: 2, 2: 5, 3: 5, 4: 3})
    max_per_club: int = 3
    budget: float = 100.0

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        if path and Path(path).exists():
            raw = json.loads(Path(path).read_text())
            base = cls()
            for key, value in raw.items():
                if hasattr(base, key):
                    setattr(base, key, value)
            return base
        return cls()

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2))
