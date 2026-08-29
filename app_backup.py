"""Local dashboard:  streamlit run app.py

Reads nothing you haven't fetched yourself, writes nothing anywhere but your
own cache directory.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from fpllab.build import build_projections, load_bundle
from fpllab.cache import Cache
from fpllab.config import Config
from fpllab.optimise import best_xi, load_squad_from_names, optimise_squad, suggest_transfers

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Fixture Room", page_icon="◆", layout="wide")

# --- surface -----------------------------------------------------------------
# Floodlit night match: deep slate pitch, sodium-lamp amber as the only accent,
# monospaced numerals because every column here is meant to be compared.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600;800&family=Inter:wght@400;500&family=IBM+Plex+Mono:wght@400;600&display=swap');

:root {
  --ink:#101820; --surface:#18222C; --line:#2B3946;
  --chalk:#E8EDF2; --mute:#8C9BAA;
  --lamp:#F0B429; --brick:#C05746; --grass:#3F8F6B;
}
.stApp { background:var(--ink); color:var(--chalk); font-family:'Inter',sans-serif; }
h1,h2,h3 { font-family:'Archivo',sans-serif; letter-spacing:-0.02em; }
h1 { font-weight:800; font-size:2.1rem; text-transform:uppercase; }
h2 { font-weight:600; font-size:1.05rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--mute); }
.masthead { border-bottom:2px solid var(--lamp); padding-bottom:.6rem; margin-bottom:1.2rem; }
.masthead .sub { font-family:'IBM Plex Mono',monospace; color:var(--mute); font-size:.8rem; letter-spacing:.06em; }
[data-testid="stMetricValue"] { font-family:'IBM Plex Mono',monospace; color:var(--lamp); font-size:1.6rem; }
[data-testid="stMetricLabel"] { text-transform:uppercase; letter-spacing:.08em; font-size:.7rem; color:var(--mute); }
[data-testid="stSidebar"] { background:var(--surface); border-right:1px solid var(--line); }
.stTabs [data-baseweb="tab"] { font-family:'Archivo',sans-serif; text-transform:uppercase; letter-spacing:.07em; font-size:.8rem; }
.stTabs [aria-selected="true"] { color:var(--lamp); border-bottom-color:var(--lamp); }
.stDataFrame { font-family:'IBM Plex Mono',monospace; }
.note { color:var(--mute); font-size:.8rem; line-height:1.5; }

/* signature: the ticker, drawn like a chalk grid on the pitch */
.ticker { border-collapse:collapse; font-family:'IBM Plex Mono',monospace; font-size:.72rem; width:100%; }
.ticker th { color:var(--mute); font-weight:400; text-align:center; padding:.35rem; border-bottom:1px solid var(--line);
             text-transform:uppercase; letter-spacing:.08em; }
.ticker td { padding:.3rem .2rem; text-align:center; border-bottom:1px solid rgba(43,57,70,.5); }
.ticker td.team { text-align:left; font-weight:600; color:var(--chalk); letter-spacing:.05em; padding-left:.4rem; }
.cell { display:block; border-radius:2px; padding:.28rem .1rem; color:#0D141A; font-weight:600; }
.cell .v { display:block; font-size:.6rem; opacity:.72; font-weight:400; }
.blank { color:var(--mute); opacity:.45; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _load(season: int, horizon: int, deep: int, fresh: bool, start_gw: int | None):
    cfg = Config(season=season, horizon_gws=horizon, deep_fetch_players=deep)
    cache = Cache(ttl_seconds=0 if fresh else cfg.cache_ttl_seconds)
    bundle = load_bundle(cfg, cache=cache, deep=deep)
    return cfg, build_projections(bundle, cfg, start_gw=start_gw)


def ramp(value: float, low: float, high: float) -> str:
    """Sodium amber (easy) through slate to brick (hard)."""
    span = max(high - low, 1e-6)
    t = min(max((value - low) / span, 0.0), 1.0)
    stops = [(0.0, (240, 180, 41)), (0.5, (150, 160, 150)), (1.0, (192, 87, 70))]
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            local = (t - p0) / (p1 - p0)
            rgb = [round(a + (b - a) * local) for a, b in zip(c0, c1)]
            return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
    return "rgb(192,87,70)"


def render_ticker(fixtures: pd.DataFrame, metric: str, gws: list[int]) -> str:
    """metric: 'xga' = how leaky the opponent run is for defenders,
    'xgf' = how much this team is expected to score."""
    if fixtures.empty:
        return "<p class='note'>No fixtures in this window.</p>"
    values = fixtures[metric]
    low, high = float(values.quantile(0.1)), float(values.quantile(0.9))
    if metric == "xgf":
        low, high = high, low  # scoring more is the good end

    order = (
        fixtures.groupby("team")[metric].mean().sort_values(ascending=(metric == "xga")).index.tolist()
    )
    head = "".join(f"<th>GW{gw}</th>" for gw in gws)
    rows = []
    for team in order:
        cells = []
        team_rows = fixtures[fixtures["team"] == team]
        for gw in gws:
            slice_ = team_rows[team_rows["gw"] == gw]
            if slice_.empty:
                cells.append("<td><span class='blank'>—</span></td>")
                continue
            inner = []
            for fixture in slice_.itertuples():
                colour = ramp(float(getattr(fixture, metric)), low, high)
                inner.append(
                    f"<span class='cell' style='background:{colour}'>{fixture.opponent}"
                    f"<span class='v'>{fixture.venue} · {getattr(fixture, metric):.2f}</span></span>"
                )
            cells.append(f"<td>{''.join(inner)}</td>")
        rows.append(f"<tr><td class='team'>{team}</td>{''.join(cells)}</tr>")
    return f"<table class='ticker'><tr><th style='text-align:left'>Team</th>{head}</tr>{''.join(rows)}</table>"


# --- controls ----------------------------------------------------------------
default_squad = Path("my_squad.txt")
with st.sidebar:
    st.markdown("## Setup")
    season = st.number_input("Season start year", 2018, 2035, Config().season)
    horizon = st.slider("Gameweeks ahead", 1, 10, 5)
    start_override = st.number_input("First gameweek (0 = auto)", 0, 38, 0)
    deep = st.slider("Deep-fetch player histories", 0, 500, 260, step=20,
                     help="Per-player FPL history. Improves bonus and defensive-contribution estimates. Slower on first run.")
    fresh = st.button("Refresh data", use_container_width=True)
    st.markdown("---")
    st.markdown("## Your squad")
    seed = default_squad.read_text() if default_squad.exists() else ""
    squad_text = st.text_area("One player per line", value=seed, height=260)
    bank = st.number_input("In the bank (£m)", 0.0, 50.0, 0.0, step=0.1)
    budget = st.number_input("Total budget (£m)", 80.0, 120.0, 100.0, step=0.5)

if fresh:
    _load.clear()

with st.spinner("Pulling FPL + Understat…"):
    try:
        cfg, result = _load(int(season), int(horizon), int(deep), fresh, int(start_override) or None)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Data pull failed: {exc}")
        st.stop()

cfg.budget = budget
players: pd.DataFrame = result["players"]
fixtures: pd.DataFrame = result["fixtures"]
start_gw = result["start_gw"]
gws = list(range(start_gw, start_gw + horizon))

st.markdown(
    f"<div class='masthead'><h1>Fixture Room</h1>"
    f"<div class='sub'>GW{start_gw}–{gws[-1]} · {len(players)} players · "
    f"{int(players['understat_matched'].sum())} matched to Understat</div></div>",
    unsafe_allow_html=True,
)

squad_names = [line.strip() for line in squad_text.splitlines() if line.strip() and not line.startswith("#")]
squad = load_squad_from_names(players, squad_names) if squad_names else players.iloc[0:0]

tab_squad, tab_ranks, tab_ticker, tab_build = st.tabs(["Squad", "Rankings", "Ticker", "Rebuild"])

SQUAD_COLS = ["web_name", "team", "pos", "price", "exp_minutes", "npxg90", "xa90", "fixtures", "xpts", "value", "confidence", "news"]

with tab_squad:
    if squad.empty:
        st.markdown("<p class='note'>Add players in the sidebar to see this.</p>", unsafe_allow_html=True)
    else:
        missing = squad.attrs.get("missing", [])
        if missing:
            st.warning("Couldn't resolve: " + ", ".join(missing))
        picked = best_xi(squad)
        columns = st.columns(4)
        columns[0].metric("Squad value", f"£{squad['price'].sum():.1f}m")
        columns[1].metric(f"Projected GW{start_gw}–{gws[-1]}", f"{squad['xpts'].sum():.0f}")
        columns[2].metric("Best XI + captain", f"{picked['total']:.0f}")
        columns[3].metric("Captain", str(picked["captain"]["web_name"]))

        st.markdown(f"## Starting XI · {picked['formation']}")
        st.dataframe(picked["xi"][SQUAD_COLS], use_container_width=True, hide_index=True)
        st.markdown("## Bench, in order")
        st.dataframe(picked["bench"][SQUAD_COLS], use_container_width=True, hide_index=True)

        st.markdown("## Weakest links")
        st.dataframe(
            squad.sort_values("xpts")[["web_name", "team", "pos", "price", "exp_minutes", "fixtures", "xpts", "value", "news"]].head(6),
            use_container_width=True, hide_index=True,
        )

        st.markdown("## Single-swap upgrades")
        transfers = suggest_transfers(squad, players, cfg, bank=bank, max_suggestions=15)
        if transfers.empty:
            st.markdown("<p class='note'>Nothing in range beats what you own.</p>", unsafe_allow_html=True)
        else:
            st.dataframe(transfers, use_container_width=True, hide_index=True)

with tab_ranks:
    left, right = st.columns([1, 3])
    with left:
        position = st.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"])
        max_price = st.slider("Max price (£m)", 3.5, 16.0, 16.0, step=0.5)
        min_minutes = st.slider("Min expected minutes", 0, 90, 45)
        sort_by = st.radio("Rank by", ["xpts", "value", "xpts_per_gw"], horizontal=False)
    view = players[(players["price"] <= max_price) & (players["exp_minutes"] >= min_minutes)]
    if position != "All":
        view = view[view["pos"] == position]
    with right:
        st.dataframe(
            view.sort_values(sort_by, ascending=False)[
                ["web_name", "team", "pos", "price", "exp_minutes", "npxg90", "xa90", "p_defcon",
                 "n_fixtures", "fixtures", "xpts", "value", "selected_by", "confidence"]
            ].head(60),
            use_container_width=True, hide_index=True, height=620,
        )

with tab_ticker:
    metric = st.radio(
        "Read the run as",
        ["Attacking prospects (xGF)", "Defensive prospects (xGA)"],
        horizontal=True,
    )
    key = "xgf" if metric.startswith("Attacking") else "xga"
    st.markdown(
        "<p class='note'>Expected goals per fixture, from Understat match history blended with FPL's "
        "strength ratings. Amber is the favourable end. Two cells in one column is a double gameweek; "
        "a dash is a blank.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(render_ticker(fixtures, key, gws), unsafe_allow_html=True)
    st.markdown("## Team strength")
    st.dataframe(result["team_strength"], use_container_width=True, hide_index=True)

with tab_build:
    st.markdown("<p class='note'>Unlimited transfers before the season starts means the current squad "
                "costs nothing to tear up. This is the highest-projecting legal 15 at your budget.</p>",
                unsafe_allow_html=True)
    keep = st.multiselect("Force in", options=list(players["web_name"].head(400)), default=[])
    if st.button("Build squad", use_container_width=False):
        locked = list(players[players["web_name"].isin(keep)]["id"])
        built = optimise_squad(players, cfg, budget=budget, locked=locked)
        picked = best_xi(built)
        columns = st.columns(3)
        columns[0].metric("Spend", f"£{built['price'].sum():.1f}m")
        columns[1].metric("Projected", f"{built['xpts'].sum():.0f}")
        columns[2].metric("XI + captain", f"{picked['total']:.0f}")
        st.dataframe(built[SQUAD_COLS], use_container_width=True, hide_index=True)
        if not squad.empty:
            kept = set(built["id"]) & set(squad["id"])
            st.markdown(f"## Overlap with your squad: {len(kept)}/15")
            if kept:
                st.markdown(
                    "<p class='note'>" + ", ".join(sorted(squad[squad["id"].isin(kept)]["web_name"])) + "</p>",
                    unsafe_allow_html=True,
                )
