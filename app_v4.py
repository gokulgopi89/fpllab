"""
FPLlab v4 — World-class FPL-themed UI

Features:
- FPL official color scheme
- Rich HTML/CSS components (not just Streamlit defaults)
- Plotly interactive charts
- Dense, information-rich layout
- Mobile responsive
- Visual player cards with team badges
- Professional design matching FPL.com

Run: streamlit run app_v4.py
"""
import io
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from fpllab.build import build_projections, load_bundle
from fpllab.cache import Cache
from fpllab.config import Config
from fpllab.fpl_rates import player_form_stats
from fpllab.optimise import best_xi, load_squad_from_names, optimise_squad, suggest_transfers
from fpllab.squad_builder import build_best_squad

logging.basicConfig(level=logging.INFO)

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="FPLlab",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# FPL Official Color Scheme
COLORS = {
    "primary": "#003399",      # FPL official blue
    "secondary": "#0055CC",    # Lighter blue
    "accent": "#FFB81C",       # Yellow
    "good": "#00B050",         # Green (up)
    "bad": "#EE3124",          # Red (down)
    "text": "#1F2937",         # Dark gray
    "text_light": "#6B7280",   # Light gray
    "bg": "#FFFFFF",           # White
    "bg_light": "#F3F4F6",     # Very light gray
    "border": "#E5E7EB",       # Border gray
}

# Team abbreviations to emojis/badges
TEAM_BADGES = {
    "ARS": "🔴", "AST": "💜", "BOU": "❤️", "BRE": "⚪", "BRI": "🔵",
    "CHE": "🔵", "CRY": "🔴", "EVE": "🔵", "FUL": "⚫", "IPS": "🔵",
    "LEI": "🔵", "LEE": "⚪", "LIV": "🔴", "MCI": "🔵", "MUN": "🔴",
    "NEW": "⚫", "NFO": "🔴", "SOU": "⚪", "TOT": "⚪", "WHU": "⚫",
    "WOL": "🟠",
}

POS_DISPLAY = {"GK": "Goalkeeper", "DEF": "Defender", "MID": "Midfielder", "FWD": "Forward"}
POS_SHORT = {"GK": "GK", "DEF": "DEF", "MID": "MID", "FWD": "FWD"}

# ============================================================================
# CSS THEMING
# ============================================================================

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&display=swap');

* {{
    font-family: 'Roboto', sans-serif;
}}

.stApp {{
    background: {COLORS['bg']};
    color: {COLORS['text']};
}}

/* Header */
.header-main {{
    background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
    color: white;
    padding: 2rem;
    border-radius: 8px;
    margin-bottom: 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}

.header-main h1 {{
    margin: 0;
    font-size: 2.2rem;
    font-weight: 700;
    letter-spacing: -0.5px;
}}

.header-main p {{
    margin: 0.5rem 0 0 0;
    font-size: 0.95rem;
    opacity: 0.95;
}}

/* Cards */
.fpl-card {{
    background: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: all 0.2s ease;
}}

.fpl-card:hover {{
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}}

.fpl-card-header {{
    font-weight: 600;
    font-size: 1.1rem;
    margin-bottom: 1rem;
    border-bottom: 2px solid {COLORS['primary']};
    padding-bottom: 0.5rem;
}}

/* Player Card */
.player-card {{
    background: {COLORS['bg_light']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 1rem;
    text-align: center;
    transition: all 0.2s ease;
    cursor: pointer;
}}

.player-card:hover {{
    border-color: {COLORS['primary']};
    box-shadow: 0 4px 12px rgba(0, 51, 153, 0.15);
    transform: translateY(-2px);
}}

.player-name {{
    font-weight: 600;
    font-size: 0.95rem;
    margin: 0.5rem 0;
    color: {COLORS['text']};
}}

.player-team {{
    font-size: 0.8rem;
    color: {COLORS['text_light']};
    margin-bottom: 0.5rem;
}}

.player-stats {{
    font-size: 0.85rem;
    margin: 0.5rem 0;
}}

.player-price {{
    font-weight: 700;
    color: {COLORS['primary']};
    font-size: 0.95rem;
}}

.player-points {{
    font-weight: 700;
    color: {COLORS['good']};
    font-size: 1rem;
}}

/* Metrics */
.metric-box {{
    background: {COLORS['bg_light']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 1rem;
    text-align: center;
    border-left: 4px solid {COLORS['primary']};
}}

.metric-label {{
    font-size: 0.75rem;
    font-weight: 600;
    color: {COLORS['text_light']};
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;
}}

.metric-value {{
    font-size: 1.8rem;
    font-weight: 700;
    color: {COLORS['primary']};
}}

.metric-sub {{
    font-size: 0.8rem;
    color: {COLORS['text_light']};
    margin-top: 0.25rem;
}}

/* Budget Bar */
.budget-container {{
    margin: 1.5rem 0;
}}

.budget-bar {{
    background: {COLORS['border']};
    border-radius: 4px;
    height: 28px;
    overflow: hidden;
    position: relative;
    margin-top: 0.5rem;
}}

.budget-fill {{
    background: linear-gradient(90deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
    height: 100%;
    transition: width 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 0.5rem;
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
}}

/* Status badges */
.status-good {{
    background: rgba(0, 176, 80, 0.1);
    color: {COLORS['good']};
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
}}

.status-bad {{
    background: rgba(238, 49, 36, 0.1);
    color: {COLORS['bad']};
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
}}

.status-neutral {{
    background: rgba(107, 114, 128, 0.1);
    color: {COLORS['text_light']};
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
}}

/* Tabs */
.stTabs [data-baseweb="tab"] {{
    font-weight: 600;
    font-size: 0.95rem;
}}

.stTabs [aria-selected="true"] {{
    color: {COLORS['primary']};
    border-bottom-color: {COLORS['primary']};
}}

/* Buttons */
.stButton > button {{
    background-color: {COLORS['primary']};
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    padding: 0.5rem 1rem;
    transition: all 0.2s ease;
}}

.stButton > button:hover {{
    background-color: {COLORS['secondary']};
    box-shadow: 0 2px 8px rgba(0, 51, 153, 0.2);
}}

/* Inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > select {{
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 0.5rem;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background: {COLORS['bg_light']};
    border-right: 1px solid {COLORS['border']};
}}

/* Formation */
.formation-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
    gap: 1rem;
    margin: 2rem 0;
    padding: 2rem;
    background: {COLORS['bg_light']};
    border-radius: 8px;
    border: 2px solid {COLORS['primary']};
}}

.formation-player {{
    background: {COLORS['primary']};
    color: white;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
    font-weight: 600;
    font-size: 0.9rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    cursor: pointer;
    transition: all 0.2s ease;
}}

.formation-player:hover {{
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}}

/* Badges */
.badge {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    background: {COLORS['bg_light']};
    color: {COLORS['primary']};
    border: 1px solid {COLORS['primary']};
}}

/* Mobile responsive */
@media (max-width: 768px) {{
    .header-main h1 {{
        font-size: 1.5rem;
    }}
    
    .metric-box {{
        padding: 0.75rem;
    }}
    
    .player-card {{
        padding: 0.75rem;
    }}
}}

</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@st.cache_data(show_spinner=False)
def load_data(season: int, horizon: int, deep: int, fresh: bool, start_gw: int | None):
    """Load FPL data."""
    cfg = Config(season=season, horizon_gws=horizon, deep_fetch_players=deep)
    cache = Cache(ttl_seconds=0 if fresh else cfg.cache_ttl_seconds)
    bundle = load_bundle(cfg, cache=cache, deep=deep)
    return cfg, build_projections(bundle, cfg, start_gw=start_gw), bundle


def render_player_card(player: pd.Series, width: int = 3) -> None:
    """Render a single player card as HTML."""
    team_badge = TEAM_BADGES.get(player["team"], "⚽")
    price = f"£{player['price']:.1f}m"
    xpts = f"{player['xpts']:.1f}"
    value = f"{player['value']:.2f}x"
    
    # Color code form
    form_color = COLORS['good'] if player['xpts'] > 20 else COLORS['bad'] if player['xpts'] < 10 else COLORS['text_light']
    
    html = f"""
    <div class="player-card">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{team_badge}</div>
        <div class="player-name">{player['web_name']}</div>
        <div class="player-team">{player['team']} • {player['pos']}</div>
        <div class="player-stats">
            <div style="margin: 0.25rem 0;"><span class="player-price">{price}</span></div>
            <div style="margin: 0.25rem 0; color: {form_color}; font-weight: 600;">{xpts} pts</div>
            <div style="margin: 0.25rem 0; font-size: 0.75rem; color: {COLORS['text_light']};">{value} value</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def create_player_grid(players_df: pd.DataFrame, cols: int = 5) -> None:
    """Create a grid of player cards."""
    for idx in range(0, len(players_df), cols):
        cols_list = st.columns(cols)
        for i, (_, player) in enumerate(players_df.iloc[idx:idx+cols].iterrows()):
            with cols_list[i]:
                render_player_card(player)


def render_metric(label: str, value: str, sub: str = "") -> None:
    """Render a metric box."""
    html = f"""
    <div class="metric-box">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {'<div class="metric-sub">' + sub + '</div>' if sub else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def draw_formation_image(squad: pd.DataFrame) -> Image.Image:
    """Draw formation as image."""
    img = Image.new("RGB", (1000, 1200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font_name = ImageFont.truetype("/Library/Fonts/Arial.ttf", 16)
        font_small = ImageFont.truetype("/Library/Fonts/Arial.ttf", 12)
    except:
        font_name = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw field (official FPL colors)
    draw.rectangle([50, 50, 950, 1150], outline="#003399", width=4)
    draw.line([500, 50, 500, 1150], fill="#003399", width=2)
    draw.ellipse([350, 500, 650, 700], outline="#003399", width=2)
    draw.rectangle([400, 100, 600, 200], outline="#003399", width=2)
    draw.rectangle([400, 950, 600, 1050], outline="#003399", width=2)
    
    # Position players
    positions = {1: [], 2: [], 3: [], 4: []}
    for row in squad.itertuples():
        positions[row.pos_id].append(row)
    
    gk = positions[1][:1]
    def_players = positions[2][:5]
    mid_players = positions[3][:5]
    fwd_players = positions[4][:3]
    
    y_gk = 200
    y_def = 400
    y_mid = 700
    y_fwd = 950
    
    # Draw GK
    for p in gk:
        x = 500
        draw.ellipse([x-40, y_gk-40, x+40, y_gk+40], fill="#003399", outline="white", width=3)
        draw.text((x-30, y_gk-8), p.web_name[:12], font=font_name, fill="white")
    
    # Draw DEF
    for i, p in enumerate(def_players):
        x = 120 + (i * 170)
        draw.ellipse([x-40, y_def-40, x+40, y_def+40], fill="#003399", outline="white", width=3)
        draw.text((x-30, y_def-8), p.web_name[:10], font=font_small, fill="white")
    
    # Draw MID
    for i, p in enumerate(mid_players):
        x = 120 + (i * 170)
        draw.ellipse([x-40, y_mid-40, x+40, y_mid+40], fill="#003399", outline="white", width=3)
        draw.text((x-30, y_mid-8), p.web_name[:10], font=font_small, fill="white")
    
    # Draw FWD
    for i, p in enumerate(fwd_players):
        x = 200 + (i * 170)
        draw.ellipse([x-40, y_fwd-40, x+40, y_fwd+40], fill="#003399", outline="white", width=3)
        draw.text((x-30, y_fwd-8), p.web_name[:10], font=font_small, fill="white")
    
    return img


# ============================================================================
# MAIN APP
# ============================================================================

# Header
st.markdown(
    f"""<div class="header-main">
    <h1>⚽ FPLlab</h1>
    <p>Optimize your Fantasy Premier League squad with advanced analytics</p>
    </div>""",
    unsafe_allow_html=True
)

# Settings (sidebar)
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    season = st.number_input("Season", 2018, 2035, Config().season)
    horizon_main = st.slider("Gameweeks", 1, 10, 5, key="horizon_main")
    deep = st.slider("Deep fetch", 0, 500, 0, step=20)
    fresh = st.button("🔄 Refresh", use_container_width=True)

if fresh:
    st.cache_data.clear()

# Load data
with st.spinner("Loading data…"):
    try:
        cfg, result, bundle = load_data(int(season), int(horizon_main), int(deep), fresh, None)
    except Exception as exc:
        st.error(f"Error: {exc}")
        st.stop()

players = result["players"]
fixtures = result["fixtures"]
start_gw = result["start_gw"]
cfg.budget = 100.0

# ============================================================================
# MAIN TABS
# ============================================================================

tab1, tab2, tab3 = st.tabs(["👥 My Team", "⚙️ Optimize", "📊 Analytics"])

# ============================================================================
# TAB 1: MY TEAM
# ============================================================================

with tab1:
    st.markdown('<div class="fpl-card"><div class="fpl-card-header">Your Squad</div></div>', unsafe_allow_html=True)
    
    col_input, col_load = st.columns([3, 1])
    with col_input:
        squad_text = st.text_area(
            "Enter player names (one per line)",
            height=150,
            placeholder="Haaland\nSaka\nOdegaard",
            key="team_input"
        )
    with col_load:
        st.write("")
        st.write("")
        load_clicked = st.button("📋 Load", use_container_width=True, key="load_squad")
    
    if squad_text.strip() and load_clicked:
        squad_names = [n.strip() for n in squad_text.splitlines() if n.strip()]
        squad = load_squad_from_names(players, squad_names)
        
        if not squad.empty:
            # Metrics row
            st.write("")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                render_metric("Budget Spent", f"£{squad['price'].sum():.1f}m", f"of £{cfg.budget:.0f}m")
            with col2:
                render_metric("Remaining", f"£{cfg.budget - squad['price'].sum():.1f}m", "Available")
            with col3:
                render_metric("Avg Ownership", f"{squad['selected_by'].mean():.1f}%", "Selected by")
            with col4:
                render_metric("Projected Points", f"{squad['xpts'].sum():.0f}", f"{horizon_main} gameweeks")
            
            # Budget bar
            st.markdown('<div class="budget-container">', unsafe_allow_html=True)
            spent_pct = (squad['price'].sum() / cfg.budget) * 100
            st.markdown(
                f'<div class="budget-bar"><div class="budget-fill" style="width: {spent_pct}%;">{spent_pct:.0f}%</div></div>',
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # XI
            xi = best_xi(squad)
            st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">{xi["formation"]} Formation</div></div>', unsafe_allow_html=True)
            st.markdown(f"**Captain:** {xi['captain']['web_name']} ({xi['captain']['team']}) | **Projected:** {xi['total']:.0f} pts")
            
            # Formation image
            formation_img = draw_formation_image(xi["xi"])
            st.image(formation_img, width=600)
            
            # Export
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                buf = io.BytesIO()
                formation_img.save(buf, format="PNG")
                st.download_button(
                    "🖼️ Download lineup",
                    data=buf.getvalue(),
                    file_name=f"squad_gw{start_gw}.png",
                    mime="image/png",
                    use_container_width=True
                )
            with col_exp2:
                csv = squad[["web_name", "team", "pos", "price", "xpts"]].to_csv(index=False)
                st.download_button(
                    "📥 CSV export",
                    data=csv,
                    file_name=f"squad_gw{start_gw}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # Bench
            st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">Bench</div></div>', unsafe_allow_html=True)
            create_player_grid(xi["bench"].head(4), cols=4)

# ============================================================================
# TAB 2: OPTIMIZE
# ============================================================================

with tab2:
    col_settings, col_results = st.columns([1, 2])
    
    with col_settings:
        st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">Build Settings</div></div>', unsafe_allow_html=True)
        
        opt_gws = st.slider("Gameweeks", 1, 10, horizon_main, key="opt_gws")
        opt_budget = st.slider("Budget (£m)", 80.0, 120.0, 100.0, step=0.5)
        
        st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">Lock Players</div></div>', unsafe_allow_html=True)
        locked_names = st.multiselect(
            "Select players to keep",
            options=sorted(players["web_name"].unique()),
            key="locked_main"
        )
        
        col_clr, col_bld = st.columns(2)
        with col_clr:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.locked_main = []
                st.rerun()
        with col_bld:
            if st.button("🔨 Build", use_container_width=True, key="do_build"):
                st.session_state.show_build = True
    
    with col_results:
        if st.session_state.get("show_build"):
            with st.spinner("Optimizing squad…"):
                cfg_opt = Config(horizon_gws=opt_gws)
                cfg_opt.budget = opt_budget
                res_opt = build_best_squad(players, cfg_opt, budget=opt_budget, locked_names=locked_names)
                sq_opt = res_opt["squad"]
                xi_opt = res_opt["xi"]
                
                st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">Optimal Squad ({xi_opt["formation"]})</div></div>', unsafe_allow_html=True)
                
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    render_metric("Cost", f"£{sq_opt['price'].sum():.1f}m")
                with col_m2:
                    render_metric("Points", f"{sq_opt['xpts'].sum():.0f}")
                with col_m3:
                    render_metric("With Captain", f"{xi_opt['total']:.0f}")
                
                # Formation image
                formation_opt_img = draw_formation_image(xi_opt["xi"])
                st.image(formation_opt_img, width=600)
                
                # Player grid
                st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">Squad Players</div></div>', unsafe_allow_html=True)
                create_player_grid(sq_opt.sort_values("xpts", ascending=False), cols=5)
                
                # Export
                col_ex1, col_ex2 = st.columns(2)
                with col_ex1:
                    buf = io.BytesIO()
                    formation_opt_img.save(buf, format="PNG")
                    st.download_button(
                        "🖼️ Download",
                        data=buf.getvalue(),
                        file_name=f"optimal_gw{start_gw}.png",
                        mime="image/png",
                        use_container_width=True
                    )
                with col_ex2:
                    csv = sq_opt[["web_name", "team", "pos", "price", "xpts"]].to_csv(index=False)
                    st.download_button(
                        "📥 CSV",
                        data=csv,
                        file_name=f"optimal_gw{start_gw}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

# ============================================================================
# TAB 3: ANALYTICS
# ============================================================================

with tab3:
    subtab_form, subtab_comp, subtab_fix = st.tabs(["📈 Form", "🎯 Comparison", "🗓️ Fixtures"])
    
    # FORM
    with subtab_form:
        col_filter, col_chart = st.columns([1, 2])
        
        with col_filter:
            st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">Filters</div></div>', unsafe_allow_html=True)
            pos_f = st.multiselect("Position", ["GK", "DEF", "MID", "FWD"], default=["GK", "DEF", "MID", "FWD"], key="pos_f")
            price_min_f = st.slider("Min price", 3.5, 16.0, 3.5, key="min_f")
            price_max_f = st.slider("Max price", 3.5, 16.0, 16.0, key="max_f")
        
        with col_chart:
            view = players[(players["pos"].isin(pos_f)) & (players["price"] >= price_min_f) & (players["price"] <= price_max_f)].sort_values("xpts", ascending=False)
            
            if not view.empty:
                # Top 15 player cards
                st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">Top Players</div></div>', unsafe_allow_html=True)
                create_player_grid(view.head(15), cols=5)
                
                # Chart
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=view["xpts"].head(12),
                    y=view["web_name"].head(12),
                    orientation='h',
                    marker=dict(color=view["xpts"].head(12), colorscale="Viridis", showscale=False)
                ))
                fig.update_layout(
                    title="Top 12 Players by Expected Points",
                    xaxis_title="Expected Points",
                    height=400,
                    showlegend=False,
                    paper_bgcolor="#FFFFFF",
                    plot_bgcolor="#F3F4F6"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # COMPARISON
    with subtab_comp:
        col_y, col_o = st.columns(2)
        
        with col_y:
            st.markdown("**Your Squad**")
            your_text = st.text_area("Paste squad", height=150, key="your_squad_comp")
        
        with col_o:
            st.markdown("**Optimal**")
            if st.button("Generate optimal", use_container_width=True, key="gen_opt_comp"):
                st.session_state.show_comp = True
        
        if your_text.strip() and st.session_state.get("show_comp"):
            your_squad_names = [n.strip() for n in your_text.splitlines() if n.strip()]
            your_sq = load_squad_from_names(players, your_squad_names)
            cfg_cmp = Config(horizon_gws=horizon_main)
            res_cmp = build_best_squad(players, cfg_cmp)
            opt_sq = res_cmp["squad"]
            
            col_y2, col_o2 = st.columns(2)
            
            with col_y2:
                st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">Your Squad</div></div>', unsafe_allow_html=True)
                col_y_m1, col_y_m2 = st.columns(2)
                with col_y_m1:
                    render_metric("Value", f"£{your_sq['price'].sum():.1f}m")
                with col_y_m2:
                    render_metric("Points", f"{your_sq['xpts'].sum():.0f}")
                create_player_grid(your_sq, cols=3)
            
            with col_o2:
                st.markdown(f'<div class="fpl-card"><div class="fpl-card-header">Optimal Squad</div></div>', unsafe_allow_html=True)
                col_o_m1, col_o_m2 = st.columns(2)
                with col_o_m1:
                    render_metric("Value", f"£{opt_sq['price'].sum():.1f}m")
                with col_o_m2:
                    render_metric("Points", f"{opt_sq['xpts'].sum():.0f}")
                create_player_grid(opt_sq, cols=3)
    
    # FIXTURES
    with subtab_fix:
        metric_fix = st.selectbox("Show", ["Attacking Strength (xGF)", "Defensive Strength (xGA)"])
        key_fix = "xgf" if "Attacking" in metric_fix else "xga"
        
        pivot = fixtures.pivot_table(index="team", columns="gw", values=key_fix, aggfunc="mean")
        
        if not pivot.empty:
            fig_heat = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=[f"GW{c}" for c in pivot.columns],
                y=pivot.index,
                colorscale="RdYlGn_r" if key_fix == "xga" else "RdYlGn",
            ))
            fig_heat.update_layout(
                title=f"{metric_fix}",
                height=600,
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F3F4F6"
            )
            st.plotly_chart(fig_heat, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("<center><small>FPLlab v4 • Made with ❤️ for Fantasy Premier League</small></center>", unsafe_allow_html=True)
