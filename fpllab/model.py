"""Turn raw stats into expected FPL points per fixture.

The chain is: per-90 underlying rates (shrunk toward positional means and
blended across seasons) -> expected minutes -> fixture-adjusted goal/assist/
clean-sheet expectations -> points.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .config import Config

POSITION_NAMES = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
DEFCON_THRESHOLD = {1: 99, 2: 10, 3: 12, 4: 12}
GAMES_IN_SEASON = 38


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _per90(total: float, minutes: float) -> float:
    return (total / minutes * 90.0) if minutes > 0 else 0.0


# ---------------------------------------------------------------------------
# rates
# ---------------------------------------------------------------------------
def _understat_rates(row: Optional[Dict[str, Any]]) -> Dict[str, float]:
    if not row:
        return {"minutes": 0.0, "games": 0.0, "npxg90": 0.0, "xa90": 0.0, "shots90": 0.0, "kp90": 0.0}
    minutes = _f(row.get("time"))
    return {
        "minutes": minutes,
        "games": _f(row.get("games")),
        "npxg90": _per90(_f(row.get("npxG")), minutes),
        "xa90": _per90(_f(row.get("xA")), minutes),
        "shots90": _per90(_f(row.get("shots")), minutes),
        "kp90": _per90(_f(row.get("key_passes")), minutes),
        "goals": _f(row.get("goals")),
        "npg": _f(row.get("npg")),
        "assists": _f(row.get("assists")),
    }


def positional_means(rates_by_player: Dict[int, Dict[str, Any]], positions: Dict[int, int]) -> Dict[int, Dict[str, float]]:
    """Minutes-weighted mean rate per position, used as the shrinkage target."""
    acc: Dict[int, Dict[str, float]] = {}
    for pid, rates in rates_by_player.items():
        pos = positions.get(pid)
        if pos is None:
            continue
        weight = rates["minutes_sample"]
        if weight <= 0:
            continue
        bucket = acc.setdefault(pos, {"w": 0.0, "npxg90": 0.0, "xa90": 0.0})
        bucket["w"] += weight
        bucket["npxg90"] += rates["raw_npxg90"] * weight
        bucket["xa90"] += rates["raw_xa90"] * weight
    means = {}
    for pos, bucket in acc.items():
        weight = max(bucket["w"], 1.0)
        means[pos] = {"npxg90": bucket["npxg90"] / weight, "xa90": bucket["xa90"] / weight}
    for pos in (1, 2, 3, 4):
        means.setdefault(pos, {"npxg90": 0.02, "xa90": 0.03})
    return means


def _defcon_probability(history: List[Dict[str, Any]], position: int, cfg: Config) -> Optional[float]:
    """Share of starts hitting the defensive-contribution threshold.

    The API field has changed shape before, so detect whether it holds a raw
    count (0-20) or the awarded points (0 or 2) and handle both.
    """
    if not cfg.defcon_enabled or position == 1:
        return 0.0
    values = [
        (_f(match.get("defensive_contribution")), _f(match.get("minutes")))
        for match in history
        if match.get("defensive_contribution") is not None
    ]
    starts = [(value, minutes) for value, minutes in values if minutes >= 60]
    if len(starts) < 3:
        return None
    looks_like_points = max(value for value, _ in starts) <= 2.0
    threshold = 2.0 if looks_like_points else DEFCON_THRESHOLD[position]
    hits = sum(1 for value, _ in starts if value >= threshold)
    return hits / len(starts)


def build_player_rates(
    elements: List[Dict[str, Any]],
    us_current: Dict[int, Dict[str, Any]],
    us_prior: Dict[int, Dict[str, Any]],
    summaries: Dict[int, Dict[str, Any]],
    cfg: Config,
    gws_played: int,
) -> Dict[int, Dict[str, Any]]:
    raw: Dict[int, Dict[str, Any]] = {}

    for element in elements:
        pid = element["id"]
        position = element.get("element_type", 3)
        current = _understat_rates(us_current.get(pid))
        prior = _understat_rates(us_prior.get(pid))

        weight_current = current["minutes"]
        weight_prior = prior["minutes"] * cfg.prior_season_weight
        total_weight = weight_current + weight_prior

        if total_weight > 0:
            npxg90 = (current["npxg90"] * weight_current + prior["npxg90"] * weight_prior) / total_weight
            xa90 = (current["xa90"] * weight_current + prior["xa90"] * weight_prior) / total_weight
        else:
            npxg90 = xa90 = 0.0

        # --- expected minutes ------------------------------------------------
        fpl_minutes = _f(element.get("minutes"))
        exp_minutes_current = fpl_minutes / gws_played if gws_played > 0 else 0.0
        prior_per_appearance = prior["minutes"] / prior["games"] if prior["games"] > 0 else 0.0
        exp_minutes_prior = 0.65 * (prior["minutes"] / GAMES_IN_SEASON) + 0.35 * prior_per_appearance

        current_credibility = fpl_minutes / (fpl_minutes + 500.0)
        if fpl_minutes <= 0 and prior["minutes"] <= 0:
            exp_minutes = 25.0  # unknown quantity: assume fringe until proven otherwise
            confidence = "low"
        elif prior["minutes"] <= 0:
            exp_minutes = exp_minutes_current
            confidence = "medium" if fpl_minutes > 270 else "low"
        else:
            exp_minutes = current_credibility * exp_minutes_current + (1 - current_credibility) * exp_minutes_prior
            confidence = "high" if (fpl_minutes + prior["minutes"]) > 1200 else "medium"

        raw[pid] = {
            "raw_npxg90": npxg90,
            "raw_xa90": xa90,
            "minutes_sample": current["minutes"] + prior["minutes"],
            "exp_minutes_base": min(exp_minutes, 90.0),
            "confidence": confidence,
            "us_current_minutes": current["minutes"],
            "us_prior_minutes": prior["minutes"],
            "prior_goals": prior.get("goals", 0.0),
            "prior_npg": prior.get("npg", 0.0),
            "shots90": current["shots90"] or prior["shots90"],
            "kp90": current["kp90"] or prior["kp90"],
        }

    positions = {e["id"]: e.get("element_type", 3) for e in elements}
    means = positional_means(raw, positions)

    # --- shrink, then layer on FPL-only signals ------------------------------
    for element in elements:
        pid = element["id"]
        position = element.get("element_type", 3)
        rates = raw[pid]
        sample = rates["minutes_sample"]
        k = cfg.shrinkage_minutes
        mean = means[position]
        rates["npxg90"] = (rates["raw_npxg90"] * sample + mean["npxg90"] * k) / (sample + k)
        rates["xa90"] = (rates["raw_xa90"] * sample + mean["xa90"] * k) / (sample + k)

        # availability
        status = (element.get("status") or "a").lower()
        multiplier = cfg.injury_status_multiplier.get(status, 1.0)
        chance = element.get("chance_of_playing_next_round")
        if chance is not None:
            multiplier = min(multiplier, _f(chance) / 100.0)
        rates["availability"] = multiplier
        rates["exp_minutes"] = rates["exp_minutes_base"] * multiplier
        rates["status"] = status
        rates["news"] = element.get("news") or ""

        # bonus proxy from BPS
        summary = summaries.get(pid, {})
        history = summary.get("history", []) or []
        past = summary.get("history_past", []) or []
        bps_total = _f(element.get("bps"))
        minutes_total = _f(element.get("minutes"))
        if minutes_total < 270 and past:
            last = past[-1]
            bps_total += _f(last.get("bps"))
            minutes_total += _f(last.get("minutes"))
        rates["bps90"] = _per90(bps_total, minutes_total)

        # goalkeeper saves
        saves_total = _f(element.get("saves"))
        save_minutes = _f(element.get("minutes"))
        if save_minutes < 270 and past:
            saves_total += _f(past[-1].get("saves"))
            save_minutes += _f(past[-1].get("minutes"))
        rates["saves90"] = _per90(saves_total, save_minutes) if position == 1 else 0.0

        # defensive contributions
        probability = _defcon_probability(history, position, cfg)
        if probability is None:
            probability = {1: 0.0, 2: 0.30, 3: 0.12, 4: 0.04}[position] if cfg.defcon_enabled else 0.0
            rates["defcon_source"] = "position-default"
        else:
            rates["defcon_source"] = "observed"
        rates["p_defcon"] = probability

        # penalties
        order = element.get("penalties_order")
        rates["pen_share"] = {1: 1.0, 2: 0.25}.get(order, 0.0) if order else 0.0
        if not order and rates["prior_goals"] > rates["prior_npg"]:
            rates["pen_share"] = 0.35  # took some last season, order not yet published

    return raw


# ---------------------------------------------------------------------------
# projection
# ---------------------------------------------------------------------------
def project_fixture(
    element: Dict[str, Any],
    rates: Dict[str, Any],
    fixture: Dict[str, Any],
    team_attack_baseline: float,
    cfg: Config,
) -> Dict[str, float]:
    position = element.get("element_type", 3)
    minutes = rates["exp_minutes"]
    if minutes <= 0:
        return {"xpts": 0.0, "minutes": 0.0, "goals": 0.0, "assists": 0.0, "cs": 0.0}

    share = minutes / 90.0
    attack_multiplier = fixture["xgf"] / max(team_attack_baseline, 0.1)
    attack_multiplier = max(cfg.min_fixture_multiplier, min(cfg.max_fixture_multiplier, attack_multiplier))

    goals = rates["npxg90"] * share * attack_multiplier
    if rates["pen_share"] > 0:
        pens = cfg.team_penalties_per_game * attack_multiplier * rates["pen_share"]
        goals += pens * cfg.penalty_conversion
    assists = rates["xa90"] * share * attack_multiplier

    xga = fixture["xga"]
    # smooth stand-ins for "played at all" and "played 60+", both needed for scoring
    p_appear = min(minutes / 20.0, 1.0)
    p_sixty = min(minutes / 60.0, 1.0)
    clean_sheet = math.exp(-xga) * p_sixty  # a clean sheet only pays from 60 minutes

    points = p_appear + p_sixty  # 1 point for appearing, 1 more at 60 minutes
    points += goals * cfg.goal_points[position]
    points += assists * cfg.assist_points
    points += clean_sheet * cfg.clean_sheet_points[position]
    points += xga * share * cfg.concede_penalty_per_goal.get(position, 0.0)

    if position == 1:
        expected_saves = rates["saves90"] * share * max(attack_multiplier, 0.6)
        points += expected_saves * cfg.save_points_per_save

    if cfg.defcon_enabled and position != 1:
        points += rates["p_defcon"] * cfg.defcon_points * p_sixty

    bonus = max(0.0, min(cfg.bonus_cap, (rates["bps90"] - cfg.bps_floor) / cfg.bps_divisor)) * share
    points += bonus

    return {
        "xpts": round(points, 3),
        "minutes": round(minutes, 1),
        "goals": round(goals, 3),
        "assists": round(assists, 3),
        "cs": round(clean_sheet, 3),
        "bonus": round(bonus, 3),
        "attack_multiplier": round(attack_multiplier, 3),
    }
