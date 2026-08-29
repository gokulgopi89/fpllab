"""Command line interface: python -m fpllab.cli <command>"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from .build import build_projections, load_bundle
from .cache import Cache
from .config import Config
from .optimise import best_xi, load_squad_from_names, optimise_squad, suggest_transfers

OUT_DIR = Path("data")


def _setup(args) -> tuple[Config, dict]:
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    cfg = Config.load(Path(args.config) if args.config else None)
    if getattr(args, "gws", None):
        cfg.horizon_gws = args.gws
    if getattr(args, "season", None):
        cfg.season = args.season
    if getattr(args, "budget", None):
        cfg.budget = args.budget
    cache = Cache(ttl_seconds=0 if getattr(args, "fresh", False) else cfg.cache_ttl_seconds)
    bundle = load_bundle(cfg, cache=cache)
    return cfg, build_projections(bundle, cfg, start_gw=getattr(args, "start_gw", None))


def _write(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    result["players"].to_csv(out_dir / "projections.csv", index=False)
    result["fixtures"].to_csv(out_dir / "fixtures.csv", index=False)
    result["team_strength"].to_csv(out_dir / "team_strength.csv", index=False)
    print(f"\nwrote {out_dir}/projections.csv, fixtures.csv, team_strength.csv")


def _show(frame: pd.DataFrame, columns: list[str], rows: int = 20) -> None:
    available = [c for c in columns if c in frame.columns]
    with pd.option_context("display.width", 200, "display.max_columns", 50):
        print(frame[available].head(rows).to_string(index=False))


def cmd_project(args):
    cfg, result = _setup(args)
    players = result["players"]
    print(f"\nProjections from GW{result['start_gw']} over {cfg.horizon_gws} gameweeks")
    columns = ["web_name", "team", "pos", "price", "exp_minutes", "npxg90", "xa90", "n_fixtures", "fixtures", "xpts", "value", "confidence"]
    for position in ("GK", "DEF", "MID", "FWD"):
        print(f"\n=== top {position} ===")
        _show(players[players["pos"] == position], columns, args.rows)
    _write(result, Path(args.out))


def cmd_fixtures(args):
    cfg, result = _setup(args)
    fixtures = result["fixtures"]
    pivot = fixtures.pivot_table(index="team", columns="gw", values="xga", aggfunc="mean")
    attack = fixtures.pivot_table(index="team", columns="gw", values="xgf", aggfunc="mean")
    print("\nExpected goals conceded per fixture (lower = better attacking target for opponents' rivals)")
    print(pivot.round(2).to_string())
    print("\nExpected goals scored per fixture (higher = better attacking prospects)")
    print(attack.round(2).sort_values(attack.columns[0], ascending=False).to_string())
    _write(result, Path(args.out))


def cmd_optimise(args):
    cfg, result = _setup(args)
    squad = optimise_squad(result["players"], cfg, budget=cfg.budget)
    xi = best_xi(squad)
    print(f"\nOptimal 15 for GW{result['start_gw']}-{result['start_gw'] + cfg.horizon_gws - 1} "
          f"— £{squad['price'].sum():.1f}m, {squad['xpts'].sum():.1f} projected points")
    _show(squad, ["web_name", "team", "pos", "price", "exp_minutes", "fixtures", "xpts", "value"], 15)
    print(f"\nBest XI ({xi['formation']}), captain {xi['captain']['web_name']}: {xi['total']:.1f} pts incl. armband")
    _show(xi["xi"], ["web_name", "team", "pos", "price", "xpts"], 11)
    _write(result, Path(args.out))


def cmd_squad(args):
    cfg, result = _setup(args)
    players = result["players"]
    names = [line.strip() for line in Path(args.file).read_text().splitlines() if line.strip() and not line.startswith("#")]
    squad = load_squad_from_names(players, names)
    missing = squad.attrs.get("missing", [])
    if missing:
        print(f"unresolved names: {', '.join(missing)}")

    print(f"\nYour squad, GW{result['start_gw']}-{result['start_gw'] + cfg.horizon_gws - 1}: "
          f"£{squad['price'].sum():.1f}m, {squad['xpts'].sum():.1f} projected points")
    _show(squad.sort_values("xpts", ascending=False),
          ["web_name", "team", "pos", "price", "exp_minutes", "fixtures", "xpts", "value", "confidence", "news"], 15)

    xi = best_xi(squad)
    print(f"\nBest XI ({xi['formation']}) — captain {xi['captain']['web_name']}, vice {xi['vice']['web_name']}")
    _show(xi["xi"], ["web_name", "team", "pos", "xpts"], 11)
    print("\nBench order:")
    _show(xi["bench"], ["web_name", "team", "pos", "xpts"], 4)

    print(f"\nUpgrades available (bank £{args.bank}m):")
    transfers = suggest_transfers(squad, players, cfg, bank=args.bank)
    if transfers.empty:
        print("  none that beat what you already own")
    else:
        _show(transfers, ["pos", "out", "out_team", "out_xpts", "in", "in_team", "in_price", "in_xpts", "gain", "spend"], 12)

    if args.rebuild:
        rebuilt = optimise_squad(players, cfg, budget=cfg.budget)
        print(f"\nUnlimited-transfer rebuild — £{rebuilt['price'].sum():.1f}m, {rebuilt['xpts'].sum():.1f} pts")
        _show(rebuilt, ["web_name", "team", "pos", "price", "fixtures", "xpts", "value"], 15)
        kept = set(rebuilt["id"]) & set(squad["id"])
        print(f"\nkeeps {len(kept)} of your 15: {', '.join(sorted(squad[squad['id'].isin(kept)]['web_name']))}")
    _write(result, Path(args.out))


def cmd_clear_cache(args):
    count = Cache().clear()
    print(f"cleared {count} cached files")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fpllab", description="FPL + Understat projection toolkit")
    parser.add_argument("--config", help="path to a JSON config file")
    parser.add_argument("--gws", type=int, help="horizon in gameweeks (default 5)")
    parser.add_argument("--season", type=int, help="season start year, e.g. 2026")
    parser.add_argument("--start-gw", type=int, dest="start_gw", help="override the first gameweek")
    parser.add_argument("--out", default=str(OUT_DIR), help="output directory for CSVs")
    parser.add_argument("--rows", type=int, default=15)
    parser.add_argument("--fresh", action="store_true", help="ignore the cache")
    parser.add_argument("--verbose", "-v", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("project", help="rank every player by projected points").set_defaults(func=cmd_project)
    sub.add_parser("fixtures", help="fixture difficulty from expected goals").set_defaults(func=cmd_fixtures)

    opt = sub.add_parser("optimise", help="build the best legal 15 from scratch")
    opt.add_argument("--budget", type=float, default=100.0)
    opt.set_defaults(func=cmd_optimise)

    squad = sub.add_parser("squad", help="analyse a squad from a names file")
    squad.add_argument("--file", default="my_squad.txt")
    squad.add_argument("--bank", type=float, default=0.0)
    squad.add_argument("--budget", type=float, default=100.0)
    squad.add_argument("--rebuild", action="store_true", help="also show the unlimited-transfer rebuild")
    squad.set_defaults(func=cmd_squad)

    sub.add_parser("clear-cache").set_defaults(func=cmd_clear_cache)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
