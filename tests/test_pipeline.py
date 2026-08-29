"""Offline end-to-end check. Runs the whole pipeline on synthetic payloads
shaped like the real ones, so you can verify the maths without hitting the
network: `python -m tests.test_pipeline`
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fpllab.build import DataBundle, build_projections  # noqa: E402
from fpllab.config import Config  # noqa: E402
from fpllab.optimise import best_xi, load_squad_from_names, optimise_squad, suggest_transfers  # noqa: E402

random.seed(7)

TEAMS = [
    ("Manchester City", "MCI"), ("Arsenal", "ARS"), ("Liverpool", "LIV"), ("Chelsea", "CHE"),
    ("Tottenham", "TOT"), ("Manchester United", "MUN"), ("Newcastle United", "NEW"), ("Brighton", "BHA"),
    ("Aston Villa", "AVL"), ("Bournemouth", "BOU"), ("Brentford", "BRE"), ("Crystal Palace", "CRY"),
    ("Everton", "EVE"), ("Fulham", "FUL"), ("Nottingham Forest", "NFO"), ("West Ham", "WHU"),
    ("Wolverhampton Wanderers", "WOL"), ("Leeds", "LEE"), ("Coventry", "COV"), ("Hull City", "HUL"),
]


def fake_bootstrap():
    teams = []
    for index, (name, short) in enumerate(TEAMS, start=1):
        tier = 1.0 + (20 - index) * 0.012
        teams.append({
            "id": index, "name": name, "short_name": short,
            "strength_attack_home": int(1100 * tier), "strength_attack_away": int(1060 * tier),
            "strength_defence_home": int(1080 * tier), "strength_defence_away": int(1040 * tier),
        })

    elements = []
    pid = 0
    for team in teams:
        for pos_id, count in ((1, 2), (2, 6), (3, 8), (4, 4)):
            for slot in range(count):
                pid += 1
                starter = slot < {1: 1, 2: 4, 3: 4, 4: 2}[pos_id]
                minutes = random.randint(1800, 3100) if starter else random.randint(120, 900)
                elements.append({
                    "id": pid,
                    "first_name": f"Player{pid}",
                    "second_name": f"Surname{pid}",
                    "web_name": f"Surname{pid}",
                    "team": team["id"],
                    "element_type": pos_id,
                    "now_cost": random.choice([40, 45, 50, 55, 60, 70, 85, 100, 145]),
                    "selected_by_percent": str(round(random.uniform(0, 40), 1)),
                    "status": "a" if random.random() > 0.05 else "d",
                    "chance_of_playing_next_round": None,
                    "news": "",
                    "minutes": 0,
                    "bps": 0,
                    "saves": 0,
                    "penalties_order": 1 if (pos_id == 4 and slot == 0 and random.random() > 0.6) else None,
                })
    events = [{"id": gw, "finished": False, "is_current": False, "is_next": gw == 1} for gw in range(1, 39)]
    return {"teams": teams, "elements": elements, "events": events}


def fake_fixtures():
    fixtures = []
    fixture_id = 0
    ids = [t["id"] for t in fake_bootstrap()["teams"]]
    for gw in range(1, 9):
        shuffled = ids[:]
        random.shuffle(shuffled)
        for i in range(0, len(shuffled), 2):
            fixture_id += 1
            fixtures.append({
                "id": fixture_id, "event": gw,
                "team_h": shuffled[i], "team_a": shuffled[i + 1],
                "team_h_difficulty": random.randint(2, 5),
                "team_a_difficulty": random.randint(2, 5),
                "kickoff_time": f"2026-08-{14 + gw:02d}T14:00:00Z",
            })
    return fixtures


def fake_understat(bootstrap, season):
    players = []
    for element in bootstrap["elements"]:
        team = next(t for t in bootstrap["teams"] if t["id"] == element["team"])
        minutes = random.randint(1500, 3200) if random.random() > 0.35 else random.randint(200, 1100)
        rate = {1: 0.0, 2: 0.06, 3: 0.20, 4: 0.42}[element["element_type"]] * random.uniform(0.3, 1.9)
        npxg = rate * minutes / 90
        xa = rate * 0.6 * minutes / 90
        players.append({
            "id": str(element["id"]),
            "player_name": f"Player{element['id']} Surname{element['id']}",
            "games": max(1, minutes // 80), "time": minutes,
            "goals": round(npxg * 1.05), "npg": round(npxg),
            "xG": round(npxg * 1.08, 2), "npxG": round(npxg, 2),
            "assists": round(xa), "xA": round(xa, 2),
            "shots": int(npxg * 9), "key_passes": int(xa * 11),
            "team_title": team["name"],
        })
    teams_data = {}
    for team in bootstrap["teams"]:
        quality = 1.6 - team["id"] * 0.045
        history = []
        for match in range(38):
            home = match % 2 == 0
            history.append({
                "h_a": "h" if home else "a",
                "xG": max(0.2, random.gauss(quality + (0.15 if home else 0), 0.4)),
                "xGA": max(0.2, random.gauss(2.6 - quality - (0.15 if home else 0), 0.4)),
            })
        teams_data[str(team["id"])] = {"id": str(team["id"]), "title": team["name"], "history": history}
    return {"season": season, "players": players, "teams": teams_data}


def main():
    cfg = Config(horizon_gws=5, deep_fetch_players=0, season=2026)
    bootstrap = fake_bootstrap()
    random.seed(7)
    bootstrap = fake_bootstrap()  # deterministic re-roll so fixtures line up
    bundle = DataBundle(
        bootstrap=bootstrap,
        fixtures=fake_fixtures(),
        understat_current={"season": 2026, "players": [], "teams": {}},
        understat_prior=fake_understat(bootstrap, 2025),
        summaries={},
    )

    result = build_projections(bundle, cfg)
    players = result["players"]
    assert not players.empty, "no players projected"
    assert players["xpts"].max() > 10, "top projection implausibly low"
    assert (players["xpts"] >= 0).all(), "negative projections"
    print(f"projected {len(players)} players from GW{result['start_gw']}")
    print(players.head(8)[["web_name", "team", "pos", "price", "exp_minutes", "fixtures", "xpts", "value"]].to_string(index=False))

    squad = optimise_squad(players, cfg)
    assert len(squad) == 15, f"squad size {len(squad)}"
    assert squad["price"].sum() <= cfg.budget + 1e-6, "over budget"
    assert squad["team_id"].value_counts().max() <= 3, "too many from one club"
    print(f"\noptimal 15: £{squad['price'].sum():.1f}m -> {squad['xpts'].sum():.1f} pts")

    xi = best_xi(squad)
    assert len(xi["xi"]) == 11
    print(f"best XI {xi['formation']}, captain {xi['captain']['web_name']}, {xi['total']:.1f} pts")

    names = list(players.sample(15, random_state=3)["web_name"])
    loaded = load_squad_from_names(players, names)
    assert len(loaded) == 15, f"resolved {len(loaded)}/15 names"
    transfers = suggest_transfers(loaded, players, cfg, bank=2.0)
    print(f"\n{len(transfers)} transfer suggestions, best gain {transfers['gain'].max() if not transfers.empty else 0}")

    print("\nall checks passed")


if __name__ == "__main__":
    main()
