"""
FPLlab v5 — Professional compact UI with FPL API integration

Features:
- Compact, information-dense layout
- Pull squad directly from FPL API (user ID 2616028)
- Advanced player analytics with metric selector
- Professional charts with multiple perspectives
- Smaller fonts, reduced whitespace
- Mobile optimized

Run: streamlit run app_v5.py
"""
import io
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from fpllab.build import build_projections, load_bundle
from fpllab.cache import Cache
from fpllab.config import Config
from fpllab.fpl_rates import player_form_stats
from fpllab.fpl_user import fetch_user_squad, get_user_history
from fpllab.optimise import best_xi, load_squad_from_names, optimise_squad
from fpllab.squad_builder import build_best_squad

logging.basicConfig(level=logging.INFO)

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="FPLlab v5",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# FPL Colors
COLORS = {
    "primary": "#003399",
    "secondary": "#0055CC",
    "accent": "#FFB81C",
    "good": "#00B050",
    "bad": "#EE3124",
    "text": "#1F2937",
    "text_light": "#6B7280",
    "bg": "#FFFFFF",
    "bg_light": "#F3F4F6",
    "border": "#E5E7EB",
}

TEAM_BADGES = {
    "ARS": "🔴", "AST": "💜", "BOU": "❤️", "BRE": "⚪", "BRI": "🔵",
    "CHE": "🔵", "CRY": "🔴", "EVE": "🔵", "FUL": "⚫", "IPS": "🔵",
    "LEI": "🔵", "LEE": "⚪", "LIV": "🔴", "MCI": "🔵", "MUN": "🔴",
    "NEW": "⚫", "NFO": "🔴", "SOU": "⚪", "TOT": "⚪", "WHU": "⚫",
    "WOL": "🟠",
}

# Compact CSS
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&display=swap');

* {{ font-family: 'Roboto', sans-serif; }}
.stApp {{ background: {COLORS['bg']}; color: {COLORS['text']}; }}

/* Reduce all spacing */
.stApp > header {{ padding: 0.5rem 1rem !important; }}
section[data-testid="stSidebar"] > div {{ padding-top: 1rem !important; }}
.stTabs {{ margin: -0.5rem 0; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 0.25rem; }}
.stTab {{ padding: 0.25rem 0.75rem !important; }}

/* Header */
.header {{ background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']}); color: white; padding: 0.75rem 1.5rem; border-radius: 6px; margin-bottom: 1rem; }}
.header h1 {{ margin: 0; font-size: 1.5rem; font-weight: 700; }}
.header p {{ margin: 0.25rem 0 0 0; font-size: 0.8rem; opacity: 0.9; }}

/* Cards & Sections */
.card {{ background: {COLORS['bg_light']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 0.75rem; margin-bottom: 0.75rem; }}
.card-title {{ font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.25rem; }}

/* Player Card */
.player-card {{ background: {COLORS['bg']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 0.6rem; text-align: center; transition: all 0.15s; cursor: pointer; }}
.player-card:hover {{ border-color: {COLORS['primary']}; box-shadow: 0 2px 6px rgba(0,51,153,0.1); transform: translateY(-1px); }}
.player-name {{ font-weight: 600; font-size: 0.8rem; margin: 0.25rem 0; }}
.player-team {{ font-size: 0.7rem; color: {COLORS['text_light']}; margin-bottom: 0.25rem; }}
.player-stat {{ font-size: 0.75rem; margin: 0.15rem 0; }}

/* Metrics */
.metric {{ background: {COLORS['bg_light']}; border-left: 3px solid {COLORS['primary']}; border-radius: 3px; padding: 0.5rem; text-align: center; }}
.metric-val {{ font-size: 1.3rem; font-weight: 700; color: {COLORS['primary']}; }}
.metric-lbl {{ font-size: 0.7rem; color: {COLORS['text_light']}; text-transform: uppercase; font-weight: 600; letter-spacing: 0.3px; }}

/* Budget Bar */
.budget-bar {{ background: {COLORS['border']}; border-radius: 3px; height: 20px; margin: 0.5rem 0; overflow: hidden; }}
.budget-fill {{ background: linear-gradient(90deg, {COLORS['primary']}, {COLORS['secondary']}); height: 100%; display: flex; align-items: center; justify-content: flex-end; padding-right: 0.3rem; color: white; font-size: 0.65rem; font-weight: 600; transition: width 0.3s; }}

/* Formation */
.formation-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(60px, 1fr)); gap: 0.5rem; margin: 0.75rem 0; padding: 0.75rem; background: {COLORS['bg_light']}; border-radius: 4px; border: 1px solid {COLORS['primary']}; }}
.formation-player {{ background: {COLORS['primary']}; color: white; border-radius: 4px; padding: 0.5rem; text-align: center; font-weight: 600; font-size: 0.75rem; }}

/* Status badge */
.status-good {{ background: rgba(0,176,80,0.1); color: {COLORS['good']}; padding: 0.2rem 0.5rem; border-radius: 3px; font-size: 0.7rem; font-weight: 600; }}
.status-bad {{ background: rgba(238,49,36,0.1); color: {COLORS['bad']}; padding: 0.2rem 0.5rem; border-radius: 3px; font-size: 0.7rem; font-weight: 600; }}

/* Tabs */
.stTabs [data-baseweb="tab"] {{ font-weight: 600; font-size: 0.85rem; }}
.stTabs [aria-selected="true"] {{ color: {COLORS['primary']}; border-bottom-color: {COLORS['primary']}; }}

/* Buttons */
.stButton > button {{ background-color: {COLORS['primary']}; color: white; border: none; border-radius: 4px; font-weight: 600; padding: 0.4rem 0.8rem; font-size: 0.85rem; }}
.stButton > button:hover {{ background-color: {COLORS['secondary']}; }}

/* Reduce margin on columns */
[data-testid="column"] {{ padding: 0.25rem !important; }}

/* Responsive */
@media (max-width: 768px) {{
    .header h1 {{ font-size: 1.2rem; }}
    .player-card {{ padding: 0.4rem; }}
    .formation-grid {{ grid-template-columns: repeat(2, 1fr); gap: 0.3rem; }}
}}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ============================================================================
# CACHING & LOADING
# ============================================================================

@st.cache_data(show_spinner=False, ttl=3600)
def load_fpl_data(season: int, horizon: int, deep: int):
    """Load base FPL data."""
    cfg = Config(season=season, horizon_gws=horizon, deep_fetch_players=deep)
    cache = Cache(ttl_seconds=cfg.cache_ttl_seconds)
    bundle = load_bundle(cfg, cache=cache, deep=deep)
    return cfg, build_projections(bundle, cfg), bundle


@st.cache_data(show_spinner=False, ttl=300)
def load_user_squad_cached(user_id: int):
    """Load user squad from API."""
    return fetch_user_squad(user_id)


def render_compact_player_card(player: pd.Series, show_captain: bool = False):
    """Render compact player card."""
    badge = TEAM_BADGES.get(player["team"], "⚽")
    form_color = COLORS['good'] if player.get('xpts', 0) > 20 else COLORS['bad'] if player.get('xpts', 0) < 10 else COLORS['text_light']
    
    captain_mark = "👑" if show_captain and player.get('is_captain') else ""
    
    html = f"""
    <div class="player-card">
        <div style="font-size: 1.1rem;">{badge}</div>
        <div class="player-name">{player['web_name']}{captain_mark}</div>
        <div class="player-team">{player['team']}</div>
        <div class="player-stat"><span style="color: {COLORS['primary']}; font-weight: 700;">£{player.get('price', 0):.1f}m</span></div>
        <div class="player-stat" style="color: {form_color}; font-weight: 600;">{player.get('xpts', player.get('points', 0)):.1f}pt</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def create_compact_grid(players_df: pd.DataFrame, cols: int = 5, show_captain: bool = False):
    """Create compact player grid."""
    if players_df.empty:
        st.info("No players")
        return
    
    for idx in range(0, len(players_df), cols):
        cols_list = st.columns(cols)
        for i, (_, player) in enumerate(players_df.iloc[idx:idx+cols].iterrows()):
            with cols_list[i % cols]:
                render_compact_player_card(player, show_captain)


# ============================================================================
# MAIN APP
# ============================================================================

# Header
st.markdown(
    f"""<div class="header">
    <h1>⚽ FPLlab</h1>
    <p>Advanced Fantasy Premier League Analytics</p>
    </div>""",
    unsafe_allow_html=True
)

# Sidebar Settings
with st.sidebar:
    st.markdown("### Settings")
    season = st.number_input("Season", 2018, 2035, Config().season, step=1)
    horizon = st.slider("GWs", 1, 10, 5)
    deep = st.slider("Deep fetch", 0, 500, 0, step=50)
    user_id = st.number_input("FPL User ID", value=2616028, step=1)
    refresh = st.button("🔄 Refresh", use_container_width=True)

if refresh:
    st.cache_data.clear()

# Load data
with st.spinner("Loading…"):
    cfg, result, bundle = load_fpl_data(int(season), int(horizon), int(deep))
    players = result["players"]
    fixtures = result["fixtures"]
    start_gw = result["start_gw"]

# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3 = st.tabs(["👥 My Squad", "⚙️ Build", "📊 Analytics"])

# ============================================================================
# TAB 1: MY SQUAD (FPL API Pull)
# ============================================================================

with tab1:
    st.markdown('<div class="card"><div class="card-title">Current Squad (Live)</div></div>', unsafe_allow_html=True)
    
    try:
        user_squad, user_meta = load_user_squad_cached(user_id)
        
        if not user_squad.empty:
            # Merge with projection data
            user_squad = user_squad.merge(
                players[['id', 'xpts', 'value', 'selected_by', 'npxg90', 'xa90']],
                on='id',
                how='left'
            ).fillna(0)
            
            # Metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.markdown(f'<div class="metric"><div class="metric-lbl">Team</div><div class="metric-val">{user_meta["team_name"]}</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric"><div class="metric-lbl">Rank</div><div class="metric-val">#{user_meta["rank"]:,}</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric"><div class="metric-lbl">Points</div><div class="metric-val">{user_meta["total_points"]}</div></div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="metric"><div class="metric-lbl">Bank</div><div class="metric-val">£{user_meta["bank"]:.1f}m</div></div>', unsafe_allow_html=True)
            with col5:
                st.markdown(f'<div class="metric"><div class="metric-lbl">Transfers</div><div class="metric-val">{user_meta["transfers_left"]}</div></div>', unsafe_allow_html=True)
            
            # Budget
            spent = user_squad['price'].sum()
            st.markdown(f'<div class="budget-bar"><div class="budget-fill" style="width: {(spent/100)*100:.0f}%;">{(spent/100)*100:.0f}%</div></div>', unsafe_allow_html=True)
            st.caption(f"£{spent:.1f}m spent • £{100 - spent:.1f}m remaining")
            
            # Squad grid
            st.markdown('<div class="card"><div class="card-title">Squad (15)</div></div>', unsafe_allow_html=True)
            create_compact_grid(user_squad.sort_values(['pos_id', 'xpts'], ascending=[True, False]), cols=5, show_captain=True)
            
            # Export
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                csv = user_squad[['web_name', 'team', 'pos', 'price', 'xpts']].to_csv(index=False)
                st.download_button("📥 CSV", csv, f"squad_gw{start_gw}.csv", "text/csv", use_container_width=True)
            with col_exp2:
                st.markdown(f'<div style="text-align:center; padding:0.5rem; background:{COLORS["bg_light"]}; border-radius:4px; font-size:0.85rem;">Total: £{spent:.1f}m | {user_squad["xpts"].sum():.0f} pts</div>', unsafe_allow_html=True)
        else:
            st.error("Could not fetch squad")
    
    except Exception as e:
        st.error(f"Error: {e}")
        st.write("Trying manual input instead...")
        squad_text = st.text_area("Paste squad (one per line):", height=100)

# ============================================================================
# TAB 2: BUILD SQUAD
# ============================================================================

with tab2:
    col_ctrl, col_res = st.columns([1, 2])
    
    with col_ctrl:
        st.markdown('<div class="card"><div class="card-title">Settings</div></div>', unsafe_allow_html=True)
        b_gws = st.slider("GWs", 1, 10, horizon, key="b_gws")
        b_budget = st.slider("Budget", 80.0, 120.0, 100.0, step=0.5)
        
        st.markdown('<div class="card"><div class="card-title">Lock Players</div></div>', unsafe_allow_html=True)
        locked = st.multiselect("Select", sorted(players['web_name'].unique()), key="locked_build")
        
        if st.button("🗑️ Clear", use_container_width=True, key="clear_locked"):
            st.session_state.locked_build = []
            st.rerun()
        
        if st.button("🔨 Build", use_container_width=True, key="do_build"):
            st.session_state.show_build = True
    
    with col_res:
        if st.session_state.get("show_build"):
            with st.spinner("Optimizing…"):
                cfg_b = Config(horizon_gws=b_gws)
                cfg_b.budget = b_budget
                res_b = build_best_squad(players, cfg_b, budget=b_budget, locked_names=locked)
                sq = res_b["squad"]
                xi = res_b["xi"]
                
                st.markdown('<div class="card"><div class="card-title">Optimal Squad</div></div>', unsafe_allow_html=True)
                
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.markdown(f'<div class="metric"><div class="metric-lbl">Cost</div><div class="metric-val">£{sq["price"].sum():.1f}m</div></div>', unsafe_allow_html=True)
                with col_m2:
                    st.markdown(f'<div class="metric"><div class="metric-lbl">Points</div><div class="metric-val">{sq["xpts"].sum():.0f}</div></div>', unsafe_allow_html=True)
                with col_m3:
                    st.markdown(f'<div class="metric"><div class="metric-lbl">XI+Cap</div><div class="metric-val">{xi["total"]:.0f}</div></div>', unsafe_allow_html=True)
                
                create_compact_grid(sq.sort_values(['pos_id', 'xpts'], ascending=[True, False]), cols=5)
                
                csv_b = sq[['web_name', 'team', 'pos', 'price', 'xpts']].to_csv(index=False)
                st.download_button("📥 CSV", csv_b, f"optimal_gw{start_gw}.csv", "text/csv", use_container_width=True)

# ============================================================================
# TAB 3: PLAYER ANALYTICS
# ============================================================================

with tab3:
    st.markdown('<div class="card"><div class="card-title">Player Analytics</div></div>', unsafe_allow_html=True)
    
    # Filters
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        pos_filter = st.multiselect("Position", ["GK", "DEF", "MID", "FWD"], default=["GK", "DEF", "MID", "FWD"], key="pos_a")
    with col_f2:
        price_min = st.slider("Min price", 3.5, 16.0, 3.5, key="pmin_a")
    with col_f3:
        price_max = st.slider("Max price", 3.5, 16.0, 16.0, key="pmax_a")
    with col_f4:
        metric_sel = st.selectbox("Metric", ["xpts", "value", "npxg90", "xa90", "selected_by"], key="metric_a")
    
    view = players[(players['pos'].isin(pos_filter)) & (players['price'] >= price_min) & (players['price'] <= price_max)].copy()
    
    if not view.empty:
        view = view.sort_values(metric_sel, ascending=False)
        
        # Top metrics
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        with col_t1:
            st.markdown(f'<div class="metric"><div class="metric-lbl">Top ({metric_sel})</div><div class="metric-val">{view[metric_sel].iloc[0]:.2f}</div></div>', unsafe_allow_html=True)
        with col_t2:
            st.markdown(f'<div class="metric"><div class="metric-lbl">Avg</div><div class="metric-val">{view[metric_sel].mean():.2f}</div></div>', unsafe_allow_html=True)
        with col_t3:
            st.markdown(f'<div class="metric"><div class="metric-lbl">Median</div><div class="metric-val">{view[metric_sel].median():.2f}</div></div>', unsafe_allow_html=True)
        with col_t4:
            st.markdown(f'<div class="metric"><div class="metric-lbl">Std Dev</div><div class="metric-val">{view[metric_sel].std():.2f}</div></div>', unsafe_allow_html=True)
        
        # Charts
        col_ch1, col_ch2 = st.columns(2)
        
        with col_ch1:
            # Top 12 bar chart
            fig_bar = go.Figure()
            top_view = view.head(12)
            fig_bar.add_trace(go.Bar(
                x=top_view[metric_sel],
                y=top_view['web_name'],
                orientation='h',
                marker=dict(
                    color=top_view[metric_sel],
                    colorscale='Viridis',
                    showscale=False
                ),
                text=top_view[metric_sel].round(2),
                textposition='outside',
            ))
            fig_bar.update_layout(
                title=f"Top 12 by {metric_sel}",
                xaxis_title=metric_sel,
                height=400,
                showlegend=False,
                margin=dict(l=120, r=50, t=40, b=30),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F3F4F6",
                font=dict(size=10)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_ch2:
            # Scatter: Price vs Metric
            fig_scatter = go.Figure()
            fig_scatter.add_trace(go.Scatter(
                x=view['price'],
                y=view[metric_sel],
                mode='markers',
                marker=dict(
                    size=view['selected_by']/3,
                    color=view['xpts'],
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="xPts", len=0.5)
                ),
                text=view['web_name'],
                hovertemplate='<b>%{text}</b><br>Price: £%{x:.1f}m<br>' + metric_sel + ': %{y:.2f}<extra></extra>'
            ))
            fig_scatter.update_layout(
                title=f"{metric_sel} vs Price (size = ownership)",
                xaxis_title="Price (£m)",
                yaxis_title=metric_sel,
                height=400,
                showlegend=False,
                margin=dict(l=60, r=80, t=40, b=30),
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F3F4F6",
                font=dict(size=10)
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Distribution histogram
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=view[metric_sel],
            nbinsx=30,
            marker=dict(color=COLORS['primary']),
            name=metric_sel
        ))
        fig_hist.update_layout(
            title=f"Distribution of {metric_sel}",
            xaxis_title=metric_sel,
            yaxis_title="Count",
            height=350,
            showlegend=False,
            margin=dict(l=50, r=50, t=40, b=30),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F3F4F6",
            font=dict(size=10)
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Top players
        st.markdown('<div class="card"><div class="card-title">Top 15 Players</div></div>', unsafe_allow_html=True)
        create_compact_grid(view.head(15), cols=5)

st.markdown("---")
st.caption(f"FPLlab v5 • GW{start_gw} • Data from FPL API")
