"""Local dashboard v2 — improved locked players, player details, form metrics.

Run: streamlit run app_v2.py
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from fpllab.build import build_projections, load_bundle
from fpllab.cache import Cache
from fpllab.config import Config
from fpllab.fpl_rates import player_form_stats
from fpllab.optimise import best_xi, load_squad_from_names, optimise_squad, suggest_transfers
from fpllab.squad_builder import build_best_squad, format_squad_table, format_xi_table, format_bench_table

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Fixture Room v2", page_icon="◆", layout="wide")

# --- surface -----------------------------------------------------------------
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
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _load(season: int, horizon: int, deep: int, fresh: bool, start_gw: int | None):
    cfg = Config(season=season, horizon_gws=horizon, deep_fetch_players=deep)
    cache = Cache(ttl_seconds=0 if fresh else cfg.cache_ttl_seconds)
    bundle = load_bundle(cfg, cache=cache, deep=deep)
    return cfg, build_projections(bundle, cfg, start_gw=start_gw), bundle


def format_player_form(player_id: int, players_df: pd.DataFrame, bundle) -> dict:
    """Get form details for a player."""
    row = players_df[players_df["id"] == player_id]
    if row.empty:
        return {}
    
    summary = bundle.summaries.get(int(player_id), {})
    form = player_form_stats(row.iloc[0].to_dict(), summary, gws=5)
    
    return {
        "name": row.iloc[0]["web_name"],
        "team": row.iloc[0]["team"],
        "pos": row.iloc[0]["pos"],
        "price": row.iloc[0]["price"],
        "selected_by": row.iloc[0]["selected_by"],
        "form_goals": form.get("goals", 0),
        "form_assists": form.get("assists", 0),
        "form_minutes": form.get("minutes", 0),
        "form_avg_points": form.get("avg_points", 0),
        "form_games": form.get("games", 0),
        "xpts": row.iloc[0]["xpts"],
        "value": row.iloc[0]["value"],
        "confidence": row.iloc[0]["confidence"],
    }


# --- controls ----------------------------------------------------------------
default_squad = Path("my_squad.txt")

with st.sidebar:
    st.markdown("## Settings")
    season = st.number_input("Season", 2018, 2035, Config().season)
    horizon = st.slider("Gameweeks ahead", 1, 10, 5, key="horizon_main")
    start_override = st.number_input("First gameweek (0 = auto)", 0, 38, 0)
    deep = st.slider("Deep fetch", 0, 500, 0, step=20)
    fresh = st.button("🔄 Refresh", use_container_width=True)
    
    st.markdown("---")
    st.markdown("## Squad")
    seed = default_squad.read_text() if default_squad.exists() else ""
    squad_text = st.text_area("Players (one per line)", value=seed, height=200, key="squad_area")
    bank = st.number_input("Bank (£m)", 0.0, 50.0, 0.0, step=0.1)
    budget = st.number_input("Budget (£m)", 80.0, 120.0, 100.0, step=0.5)

if fresh:
    _load.clear()

with st.spinner("Loading…"):
    try:
        cfg, result, bundle = _load(int(season), int(horizon), int(deep), fresh, int(start_override) or None)
    except Exception as exc:
        st.error(f"Load failed: {exc}")
        st.stop()

cfg.budget = budget
players = result["players"]
fixtures = result["fixtures"]
start_gw = result["start_gw"]
gws = list(range(start_gw, start_gw + horizon))

st.markdown(
    f"<div class='masthead'><h1>Fixture Room v2</h1>"
    f"<div class='sub'>GW{start_gw}–{gws[-1]} · {len(players)} players · "
    f"Budget £{budget}m (±5%)</div></div>",
    unsafe_allow_html=True,
)

squad_names = [line.strip() for line in squad_text.splitlines() if line.strip() and not line.startswith("#")]
squad = load_squad_from_names(players, squad_names) if squad_names else players.iloc[0:0]

tab_squad, tab_ranks, tab_ticker, tab_build, tab_player = st.tabs(["Squad", "Rankings", "Fixture", "Build", "Player"])

SQUAD_COLS = ["web_name", "team", "pos", "price", "exp_minutes", "xpts", "value", "confidence"]

with tab_squad:
    if squad.empty:
        st.info("Add players in the sidebar")
    else:
        missing = squad.attrs.get("missing", [])
        if missing:
            st.warning(f"Not found: {', '.join(missing)}")
        
        picked = best_xi(squad)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Value", f"£{squad['price'].sum():.1f}m")
        col2.metric(f"GW{start_gw}–{gws[-1]}", f"{squad['xpts'].sum():.0f}")
        col3.metric("XI+Cap", f"{picked['total']:.0f}")
        col4.metric("Captain", picked["captain"]["web_name"])

        st.markdown(f"### XI · {picked['formation']}")
        st.dataframe(picked["xi"][SQUAD_COLS], use_container_width=True, hide_index=True)
        
        st.markdown("### Bench")
        st.dataframe(picked["bench"][SQUAD_COLS].head(4), use_container_width=True, hide_index=True)
        
        st.markdown("### Weak links")
        weak = squad.sort_values("xpts")[["web_name", "team", "pos", "price", "xpts"]].head(5)
        st.dataframe(weak, use_container_width=True, hide_index=True)
        
        st.markdown("### Upgrades")
        transfers = suggest_transfers(squad, players, cfg, bank=bank, max_suggestions=10)
        if transfers.empty:
            st.caption("No upgrades in range")
        else:
            st.dataframe(transfers, use_container_width=True, hide_index=True)

with tab_ranks:
    col1, col2 = st.columns([1, 3])
    with col1:
        pos = st.selectbox("Pos", ["All", "GK", "DEF", "MID", "FWD"])
        max_price = st.slider("Max price", 3.5, 16.0, 16.0, step=0.5)
        min_mins = st.slider("Min mins", 0, 90, 45)
        sort = st.radio("Sort by", ["xpts", "value", "selected_by"])
    
    view = players[(players["price"] <= max_price) & (players["exp_minutes"] >= min_mins)]
    if pos != "All":
        view = view[view["pos"] == pos]
    
    with col2:
        st.dataframe(
            view.sort_values(sort, ascending=False)[
                ["web_name", "team", "pos", "price", "exp_minutes", "xpts", "value", "selected_by", "confidence"]
            ].head(80),
            use_container_width=True, hide_index=True, height=700,
        )

with tab_ticker:
    st.markdown("### Fixture difficulty")
    metric = st.radio("View", ["Attacking (xGF)", "Defensive (xGA)"], horizontal=True)
    key = "xgf" if "Attacking" in metric else "xga"
    
    pivot = fixtures.pivot_table(index="team", columns="gw", values=key, aggfunc="mean")
    if not pivot.empty:
        st.dataframe(pivot.round(2), use_container_width=True)

with tab_build:
    st.markdown("### Build optimized squad")
    st.caption(f"Budget: £{budget}m (allows ±5% = £{budget*0.95:.0f}–{budget*1.05:.0f})")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        b_budget = st.number_input("Budget", 80.0, 120.0, budget, step=0.5, key="build_budget")
    with col2:
        b_gws = st.slider("GWs", 1, 10, horizon, key="build_gws")
    with col3:
        st.write("")
    
    st.markdown("**Lock players (optional):**")
    lock_text = st.text_area(
        "One per line",
        value=st.session_state.get("locked_input", ""),
        placeholder="Haaland\nSaka",
        height=100,
        key="locked_input_v2"
    )
    
    if st.button("🔨 Build", use_container_width=True, key="build_btn"):
        locked = [n.strip() for n in lock_text.splitlines() if n.strip()]
        
        with st.spinner("Building…"):
            cfg_b = Config(horizon_gws=b_gws)
            cfg_b.budget = b_budget
            
            res_b = build_best_squad(players, cfg_b, budget=b_budget, locked_names=locked)
            sq = res_b["squad"]
            xi = res_b["xi"]
            
            if res_b["missing"]:
                st.warning(f"Not found: {', '.join(res_b['missing'])}")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Spend", f"£{sq['price'].sum():.1f}m")
            col2.metric("Proj", f"{sq['xpts'].sum():.0f}")
            col3.metric("XI+Cap", f"{xi['total']:.0f}")
            col4.metric("Form", xi["formation"])
            
            st.dataframe(format_squad_table(sq), use_container_width=True, hide_index=True)
            
            col_xi, col_bench = st.columns([2, 1])
            with col_xi:
                st.markdown(f"**XI · {xi['formation']}** — Cap: {xi['captain']['web_name']}")
                st.dataframe(format_xi_table(xi), use_container_width=True, hide_index=True)
            with col_bench:
                st.markdown("**Bench**")
                st.dataframe(format_bench_table(xi), use_container_width=True, hide_index=True)
            
            csv = sq[[
                "web_name", "team", "pos", "price", "xpts", "value", "confidence"
            ]].to_csv(index=False)
            st.download_button(
                "⬇️ CSV",
                data=csv,
                file_name=f"squad_gw{start_gw}_{b_gws}gws.csv",
                mime="text/csv",
            )

with tab_player:
    st.markdown("### Player details & form")
    
    search = st.selectbox(
        "Find player",
        options=sorted(players["web_name"].unique()),
        key="player_search"
    )
    
    if search:
        p = players[players["web_name"] == search].iloc[0]
        form = player_form_stats(
            p.to_dict(),
            bundle.summaries.get(int(p["id"]), {}),
            gws=5
        )
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Price", f"£{p['price']:.1f}m")
        col2.metric("Owned", f"{p['selected_by']:.1f}%")
        col3.metric("GW{start_gw}–{gws[-1]}", f"{p['xpts']:.1f}")
        col4.metric("Value", f"{p['value']:.2f}x")
        col5.metric("Confidence", p["confidence"])
        
        st.markdown("---")
        st.markdown("**Last 5 gameweeks:**")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Goals", int(form.get("goals", 0)))
        col2.metric("Assists", int(form.get("assists", 0)))
        col3.metric("Minutes", int(form.get("minutes", 0)))
        col4.metric("Games", int(form.get("games", 0)))
        col5.metric("Avg pts", form.get("avg_points", 0))
        
        st.markdown("---")
        st.markdown("**Projection:**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("xG90", f"{p['npxg90']:.3f}")
        col2.metric("xA90", f"{p['xa90']:.3f}")
        col3.metric("Exp mins", f"{p['exp_minutes']:.0f}")
        col4.metric("BPS90", f"{p['bps90']:.1f}")
        
        st.markdown("---")
        st.markdown("**Fixtures:**")
        st.caption(p["fixtures"])
