"""
FPLlab v6 — Enhanced with pictorial formations, auto-lock from squad, comprehensive metrics table

Run: streamlit run app_v6.py
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

st.set_page_config(page_title="FPLlab v6", page_icon="⚽", layout="wide", initial_sidebar_state="collapsed")

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

.header {{ background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']}); color: white; padding: 0.75rem 1.5rem; border-radius: 6px; margin-bottom: 1rem; }}
.header h1 {{ margin: 0; font-size: 1.5rem; font-weight: 700; }}
.header p {{ margin: 0.25rem 0 0 0; font-size: 0.8rem; opacity: 0.9; }}

.card {{ background: {COLORS['bg_light']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 0.75rem; margin-bottom: 0.75rem; }}
.card-title {{ font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.25rem; }}

.formation-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin: 1.5rem 0; padding: 1.5rem; background: linear-gradient(135deg, {COLORS['bg_light']}, white); border-radius: 8px; border: 2px solid {COLORS['primary']}; }}

.formation-row {{ display: flex; justify-content: center; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}

.player-position {{ text-align: center; font-size: 0.7rem; color: {COLORS['text_light']}; font-weight: 600; text-transform: uppercase; margin-bottom: 0.5rem; }}

.formation-player {{ 
    background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']}); 
    color: white; 
    border-radius: 8px; 
    padding: 0.75rem; 
    text-align: center; 
    font-weight: 600; 
    font-size: 0.75rem; 
    box-shadow: 0 2px 8px rgba(0,51,153,0.15);
    cursor: pointer;
    transition: all 0.2s ease;
    min-width: 70px;
}}

.formation-player:hover {{ transform: scale(1.05); box-shadow: 0 4px 12px rgba(0,51,153,0.25); }}

.player-name {{ font-size: 0.75rem; font-weight: 700; margin-bottom: 0.3rem; }}
.player-stats {{ font-size: 0.65rem; opacity: 0.9; }}

.bench-card {{ background: {COLORS['bg_light']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 0.75rem; text-align: center; transition: all 0.15s; cursor: pointer; }}
.bench-card:hover {{ border-color: {COLORS['primary']}; box-shadow: 0 2px 6px rgba(0,51,153,0.1); transform: translateY(-1px); }}

.bench-name {{ font-weight: 600; font-size: 0.8rem; margin: 0.25rem 0; }}
.bench-team {{ font-size: 0.7rem; color: {COLORS['text_light']}; margin-bottom: 0.25rem; }}
.bench-stat {{ font-size: 0.75rem; margin: 0.15rem 0; }}

.metric {{ background: {COLORS['bg_light']}; border-left: 3px solid {COLORS['primary']}; border-radius: 3px; padding: 0.5rem; text-align: center; }}
.metric-val {{ font-size: 1.3rem; font-weight: 700; color: {COLORS['primary']}; }}
.metric-lbl {{ font-size: 0.7rem; color: {COLORS['text_light']}; text-transform: uppercase; font-weight: 600; letter-spacing: 0.3px; }}

.stTabs [data-baseweb="tab"] {{ font-weight: 600; font-size: 0.85rem; }}
.stTabs [aria-selected="true"] {{ color: {COLORS['primary']}; border-bottom-color: {COLORS['primary']}; }}

.stButton > button {{ background-color: {COLORS['primary']}; color: white; border: none; border-radius: 4px; font-weight: 600; padding: 0.4rem 0.8rem; font-size: 0.85rem; }}
.stButton > button:hover {{ background-color: {COLORS['secondary']}; }}

[data-testid="column"] {{ padding: 0.25rem !important; }}

/* Table styling */
.dataframe {{ font-size: 0.85rem; }}
.dataframe td {{ padding: 0.5rem; }}

@media (max-width: 768px) {{
    .header h1 {{ font-size: 1.2rem; }}
    .formation-grid {{ grid-template-columns: repeat(2, 1fr); gap: 0.5rem; }}
    .formation-player {{ padding: 0.5rem; font-size: 0.65rem; min-width: 50px; }}
}}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ============================================================================
# CACHING & LOADING
# ============================================================================

@st.cache_data(show_spinner=False, ttl=3600)
def load_fpl_data(season: int, horizon: int, deep: int):
    cfg = Config(season=season, horizon_gws=horizon, deep_fetch_players=deep)
    cache = Cache(ttl_seconds=cfg.cache_ttl_seconds)
    bundle = load_bundle(cfg, cache=cache, deep=deep)
    return cfg, build_projections(bundle, cfg), bundle


@st.cache_data(show_spinner=False, ttl=300)
def load_user_squad_cached(user_id: int):
    return fetch_user_squad(user_id)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def render_formation_pictorial(squad_df: pd.DataFrame, title: str = "Formation") -> None:
    """Render squad as pictorial formation (like FPL app)."""
    
    if squad_df.empty:
        st.info("No squad to display")
        return
    
    # Get XI and bench
    positions = {1: [], 2: [], 3: [], 4: []}
    for _, row in squad_df.iterrows():
        positions[row['pos_id']].append(row)
    
    gk = positions[1][:1]
    def_players = sorted(positions[2][:5], key=lambda x: x['xpts'], reverse=True)
    mid_players = sorted(positions[3][:5], key=lambda x: x['xpts'], reverse=True)
    fwd_players = sorted(positions[4][:3], key=lambda x: x['xpts'], reverse=True)
    
    # Determine formation
    formation = f"{len(def_players)}-{len(mid_players)}-{len(fwd_players)}"
    
    st.markdown(f'<div class="card-title">{title} • {formation}</div>', unsafe_allow_html=True)
    
    # Render formation
    st.markdown('<div class="formation-grid">', unsafe_allow_html=True)
    
    # GK Row
    st.markdown('<div class="formation-row">', unsafe_allow_html=True)
    st.markdown('<div class="player-position">Goalkeeper</div>', unsafe_allow_html=True)
    for p in gk:
        st.markdown(
            f'<div class="formation-player">'
            f'<div class="player-name">{p["web_name"]}</div>'
            f'<div class="player-stats">£{p["price"]:.1f}m</div>'
            f'<div class="player-stats">{p["xpts"]:.1f}pt</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # DEF Row
    st.markdown('<div class="formation-row">', unsafe_allow_html=True)
    st.markdown('<div class="player-position">Defenders</div>', unsafe_allow_html=True)
    for p in def_players:
        st.markdown(
            f'<div class="formation-player">'
            f'<div class="player-name">{p["web_name"]}</div>'
            f'<div class="player-stats">£{p["price"]:.1f}m</div>'
            f'<div class="player-stats">{p["xpts"]:.1f}pt</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # MID Row
    st.markdown('<div class="formation-row">', unsafe_allow_html=True)
    st.markdown('<div class="player-position">Midfielders</div>', unsafe_allow_html=True)
    for p in mid_players:
        st.markdown(
            f'<div class="formation-player">'
            f'<div class="player-name">{p["web_name"]}</div>'
            f'<div class="player-stats">£{p["price"]:.1f}m</div>'
            f'<div class="player-stats">{p["xpts"]:.1f}pt</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # FWD Row
    st.markdown('<div class="formation-row">', unsafe_allow_html=True)
    st.markdown('<div class="player-position">Forwards</div>', unsafe_allow_html=True)
    for p in fwd_players:
        st.markdown(
            f'<div class="formation-player">'
            f'<div class="player-name">{p["web_name"]}</div>'
            f'<div class="player-stats">£{p["price"]:.1f}m</div>'
            f'<div class="player-stats">{p["xpts"]:.1f}pt</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_bench(squad_df: pd.DataFrame, xi_players: set) -> None:
    """Render bench as cards."""
    bench = squad_df[~squad_df['id'].isin(xi_players)].sort_values('xpts', ascending=False)
    
    if bench.empty:
        return
    
    st.markdown('<div class="card-title">Bench</div>', unsafe_allow_html=True)
    
    cols = st.columns(len(bench))
    for i, (_, player) in enumerate(bench.iterrows()):
        with cols[i]:
            st.markdown(
                f'<div class="bench-card">'
                f'<div style="font-size: 1.2rem; margin-bottom: 0.25rem;">{TEAM_BADGES.get(player["team"], "⚽")}</div>'
                f'<div class="bench-name">{player["web_name"]}</div>'
                f'<div class="bench-team">{player["team"]} • {player["pos"]}</div>'
                f'<div class="bench-stat" style="color: {COLORS["primary"]}; font-weight: 700;">£{player["price"]:.1f}m</div>'
                f'<div class="bench-stat" style="color: {COLORS["good"]}; font-weight: 600;">{player["xpts"]:.1f}pt</div>'
                f'</div>',
                unsafe_allow_html=True
            )


# ============================================================================
# MAIN APP
# ============================================================================

# Header
st.markdown(
    f"""<div class="header">
    <h1>⚽ FPLlab v6</h1>
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
# TAB 1: MY SQUAD (Pictorial)
# ============================================================================

with tab1:
    try:
        user_squad, user_meta = load_user_squad_cached(user_id)
        
        if not user_squad.empty:
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
            
            # Pictorial formation
            xi = best_xi(user_squad)
            render_formation_pictorial(xi['xi'], f"Your XI • {xi['formation']}")
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown(f'<div class="metric"><div class="metric-lbl">Captain</div><div class="metric-val">{xi["captain"]["web_name"]}</div></div>', unsafe_allow_html=True)
            with col_m2:
                st.markdown(f'<div class="metric"><div class="metric-lbl">XI + Cap</div><div class="metric-val">{xi["total"]:.0f} pts</div></div>', unsafe_allow_html=True)
            
            # Bench
            render_bench(user_squad, set(xi['xi']['id'].values))
            
            # Total squad info
            spent = user_squad['price'].sum()
            st.markdown(f'<div class="card"><b>Total Squad:</b> £{spent:.1f}m | {user_squad["xpts"].sum():.0f} pts | Avg value: {user_squad["value"].mean():.2f}x</div>', unsafe_allow_html=True)
            
            # Export
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                csv = user_squad[['web_name', 'team', 'pos', 'price', 'xpts']].to_csv(index=False)
                st.download_button("📥 CSV", csv, f"squad_gw{start_gw}.csv", "text/csv", use_container_width=True)
            with col_exp2:
                pass
    
    except Exception as e:
        st.error(f"Error: {e}")

# ============================================================================
# TAB 2: BUILD (Pictorial + Auto-lock from squad)
# ============================================================================

with tab2:
    col_ctrl, col_res = st.columns([1, 2])
    
    with col_ctrl:
        st.markdown('<div class="card"><div class="card-title">Settings</div></div>', unsafe_allow_html=True)
        b_gws = st.slider("GWs", 1, 10, horizon, key="b_gws")
        b_budget = st.slider("Budget", 80.0, 120.0, 100.0, step=0.5)
        
        st.markdown('<div class="card"><div class="card-title">Lock Players</div></div>', unsafe_allow_html=True)
        
        # Auto-populate from current squad
        if st.button("📋 Add from my squad", use_container_width=True, key="auto_lock"):
            try:
                user_squad_auto, _ = load_user_squad_cached(user_id)
                if not user_squad_auto.empty:
                    current_locked = st.session_state.get("locked_build", [])
                    squad_names = user_squad_auto['web_name'].tolist()
                    # Add missing players
                    for name in squad_names:
                        if name not in current_locked:
                            current_locked.append(name)
                    st.session_state.locked_build = current_locked
                    st.rerun()
            except:
                st.warning("Could not fetch squad")
        
        locked = st.multiselect(
            "Select players to keep",
            options=sorted(players['web_name'].unique()),
            default=st.session_state.get("locked_build", []),
            key="locked_build"
        )
        
        col_clr, col_clr2 = st.columns(2)
        with col_clr:
            if st.button("🗑️ Clear", use_container_width=True, key="clear_locked_b"):
                st.session_state.locked_build = []
                st.rerun()
        with col_clr2:
            pass
        
        if st.button("🔨 Build", use_container_width=True, key="do_build_b"):
            st.session_state.show_build_b = True
    
    with col_res:
        if st.session_state.get("show_build_b"):
            with st.spinner("Optimizing…"):
                cfg_b = Config(horizon_gws=b_gws)
                cfg_b.budget = b_budget
                res_b = build_best_squad(players, cfg_b, budget=b_budget, locked_names=locked)
                sq = res_b["squad"]
                xi_b = res_b["xi"]
                
                st.markdown('<div class="card"><div class="card-title">Optimal Squad</div></div>', unsafe_allow_html=True)
                
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.markdown(f'<div class="metric"><div class="metric-lbl">Cost</div><div class="metric-val">£{sq["price"].sum():.1f}m</div></div>', unsafe_allow_html=True)
                with col_m2:
                    st.markdown(f'<div class="metric"><div class="metric-lbl">Points</div><div class="metric-val">{sq["xpts"].sum():.0f}</div></div>', unsafe_allow_html=True)
                with col_m3:
                    st.markdown(f'<div class="metric"><div class="metric-lbl">XI+Cap</div><div class="metric-val">{xi_b["total"]:.0f}</div></div>', unsafe_allow_html=True)
                
                # Pictorial formation
                render_formation_pictorial(xi_b["xi"], f"Optimal XI • {xi_b['formation']}")
                
                # Bench
                render_bench(sq, set(xi_b['xi']['id'].values))
                
                # Export
                csv_b = sq[['web_name', 'team', 'pos', 'price', 'xpts']].to_csv(index=False)
                st.download_button("📥 CSV", csv_b, f"optimal_gw{start_gw}.csv", "text/csv", use_container_width=True)

# ============================================================================
# TAB 3: ANALYTICS (Comprehensive Metrics Table)
# ============================================================================

with tab3:
    st.markdown('<div class="card"><div class="card-title">Player Analytics & Metrics</div></div>', unsafe_allow_html=True)
    
    # Filters
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        pos_filter = st.multiselect("Position", ["GK", "DEF", "MID", "FWD"], default=["GK", "DEF", "MID", "FWD"], key="pos_a_v6")
    with col_f2:
        team_filter = st.multiselect("Team", sorted(players['team'].unique()), key="team_a_v6")
    with col_f3:
        price_min = st.slider("Min price", 3.5, 16.0, 3.5, key="pmin_a_v6")
    with col_f4:
        price_max = st.slider("Max price", 3.5, 16.0, 16.0, key="pmax_a_v6")
    
    # Filter data
    view = players[
        (players['pos'].isin(pos_filter)) & 
        (players['price'] >= price_min) & 
        (players['price'] <= price_max)
    ].copy()
    
    if team_filter:
        view = view[view['team'].isin(team_filter)]
    
    if not view.empty:
        # Summary metrics
        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
        with col_s1:
            st.markdown(f'<div class="metric"><div class="metric-lbl">Players</div><div class="metric-val">{len(view)}</div></div>', unsafe_allow_html=True)
        with col_s2:
            st.markdown(f'<div class="metric"><div class="metric-lbl">Avg xpts</div><div class="metric-val">{view["xpts"].mean():.1f}</div></div>', unsafe_allow_html=True)
        with col_s3:
            st.markdown(f'<div class="metric"><div class="metric-lbl">Avg value</div><div class="metric-val">{view["value"].mean():.2f}x</div></div>', unsafe_allow_html=True)
        with col_s4:
            st.markdown(f'<div class="metric"><div class="metric-lbl">Avg xG/90</div><div class="metric-val">{view["npxg90"].mean():.3f}</div></div>', unsafe_allow_html=True)
        with col_s5:
            st.markdown(f'<div class="metric"><div class="metric-lbl">Avg xA/90</div><div class="metric-val">{view["xa90"].mean():.3f}</div></div>', unsafe_allow_html=True)
        
        # Comprehensive metrics table
        st.markdown('<div class="card"><div class="card-title">All Player Metrics</div></div>', unsafe_allow_html=True)
        
        metrics_table = view[[
            'web_name', 'team', 'pos', 'price', 'xpts', 'value', 'npxg90', 'xa90', 
            'selected_by'
        ]].copy()
        
        metrics_table.columns = [
            'Player', 'Team', 'Pos', 'Price (£m)', 'xpts (5GW)', 'Value (x)', 
            'xG/90', 'xA/90', 'Ownership (%)'
        ]
        
        metrics_table = metrics_table.sort_values('xpts (5GW)', ascending=False)
        
        # Format for display
        metrics_table['Price (£m)'] = metrics_table['Price (£m)'].apply(lambda x: f"£{x:.1f}m")
        metrics_table['xpts (5GW)'] = metrics_table['xpts (5GW)'].apply(lambda x: f"{x:.1f}")
        metrics_table['Value (x)'] = metrics_table['Value (x)'].apply(lambda x: f"{x:.2f}x")
        metrics_table['xG/90'] = metrics_table['xG/90'].apply(lambda x: f"{x:.3f}")
        metrics_table['xA/90'] = metrics_table['xA/90'].apply(lambda x: f"{x:.3f}")
        metrics_table['Ownership (%)'] = metrics_table['Ownership (%)'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            metrics_table.head(100),
            use_container_width=True,
            hide_index=True,
            height=600
        )
        
        # Charts
        st.markdown('<div class="card"><div class="card-title">Metric Distributions</div></div>', unsafe_allow_html=True)
        
        col_ch1, col_ch2 = st.columns(2)
        
        with col_ch1:
            # xpts distribution
            fig_xpts = go.Figure()
            fig_xpts.add_trace(go.Histogram(
                x=view['xpts'],
                nbinsx=30,
                marker=dict(color=COLORS['primary']),
                name='xpts'
            ))
            fig_xpts.update_layout(
                title="Expected Points Distribution",
                xaxis_title="xpts",
                yaxis_title="Count",
                height=350,
                showlegend=False,
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F3F4F6",
                font=dict(size=10)
            )
            st.plotly_chart(fig_xpts, use_container_width=True)
        
        with col_ch2:
            # Value distribution
            fig_val = go.Figure()
            fig_val.add_trace(go.Histogram(
                x=view['value'],
                nbinsx=30,
                marker=dict(color=COLORS['good']),
                name='value'
            ))
            fig_val.update_layout(
                title="Value Distribution (xpts/£m)",
                xaxis_title="Value (x)",
                yaxis_title="Count",
                height=350,
                showlegend=False,
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F3F4F6",
                font=dict(size=10)
            )
            st.plotly_chart(fig_val, use_container_width=True)
        
        # Scatter: Price vs Value colored by xpts
        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(
            x=view['price'],
            y=view['value'],
            mode='markers',
            marker=dict(
                size=view['selected_by']/2,
                color=view['xpts'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="xpts", len=0.6)
            ),
            text=view['web_name'],
            hovertemplate='<b>%{text}</b><br>Price: £%{x:.1f}m<br>Value: %{y:.2f}x<extra></extra>'
        ))
        fig_scatter.update_layout(
            title="Value Analysis: Price vs Value (size = ownership, color = xpts)",
            xaxis_title="Price (£m)",
            yaxis_title="Value (x)",
            height=400,
            showlegend=False,
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F3F4F6",
            font=dict(size=10)
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        # xG vs xA scatter
        fig_xgxa = go.Figure()
        fig_xgxa.add_trace(go.Scatter(
            x=view['npxg90'],
            y=view['xa90'],
            mode='markers',
            marker=dict(
                size=view['xpts']/5,
                color=view['selected_by'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Ownership %", len=0.6)
            ),
            text=view['web_name'],
            hovertemplate='<b>%{text}</b><br>xG/90: %{x:.3f}<br>xA/90: %{y:.3f}<extra></extra>'
        ))
        fig_xgxa.update_layout(
            title="Player Role Analysis: xG/90 vs xA/90 (size = xpts, color = ownership)",
            xaxis_title="xG/90 (Shooting)",
            yaxis_title="xA/90 (Playmaking)",
            height=400,
            showlegend=False,
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F3F4F6",
            font=dict(size=10)
        )
        st.plotly_chart(fig_xgxa, use_container_width=True)

st.markdown("---")
st.caption(f"FPLlab v6 • GW{start_gw} • All metrics explained in METRICS_MATHEMATICS.md")
