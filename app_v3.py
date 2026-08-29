"""
FPLlab v3 — Complete redesign with lineup visualization, analytics dashboard, and trading tools.

Run: streamlit run app_v3.py

Features:
- Tab 1: My Team (lineup visualization with names inside formation)
- Tab 2: Optimize (build squad with fixed widgets)
- Tab 3: Analytics (sub-tabs: Form | Comparison | Fixtures)
- Trade calculator
- Compare vs optimal squad
- Lineup image export
- Mobile responsive
"""
import io
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
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
# PAGE CONFIG & THEMING
# ============================================================================

st.set_page_config(
    page_title="FPLlab v3",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Blue color scheme
COLORS = {
    "primary": "#0066CC",
    "secondary": "#00A3E0",
    "accent": "#FFB81C",
    "good": "#10A760",
    "bad": "#E74C3C",
    "neutral": "#95A5A6",
    "bg": "#F8FBFF",
    "card": "#FFFFFF",
    "text": "#2C3E50",
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* {{
    font-family: 'Inter', sans-serif;
}}

.stApp {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
}}

.header {{
    background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
    padding: 2rem;
    border-radius: 12px;
    color: white;
    margin-bottom: 2rem;
}}

.header h1 {{
    margin: 0;
    font-size: 2.5rem;
    font-weight: 800;
}}

.header p {{
    margin: 0.5rem 0 0 0;
    opacity: 0.9;
    font-size: 1rem;
}}

.card {{
    background: {COLORS['card']};
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    transition: all 0.3s ease;
}}

.card:hover {{
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    transform: translateY(-2px);
}}

.card-good {{
    border-left: 4px solid {COLORS['good']};
}}

.card-bad {{
    border-left: 4px solid {COLORS['bad']};
}}

.metric {{
    text-align: center;
    padding: 1rem;
}}

.metric-value {{
    font-size: 2rem;
    font-weight: 700;
    color: {COLORS['primary']};
}}

.metric-label {{
    font-size: 0.8rem;
    color: {COLORS['neutral']};
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.5rem;
}}

.budget-meter {{
    background: #e0e0e0;
    border-radius: 8px;
    height: 24px;
    overflow: hidden;
    margin: 1rem 0;
}}

.budget-meter-fill {{
    background: linear-gradient(90deg, {COLORS['good']} 0%, {COLORS['accent']} 100%);
    height: 100%;
    transition: width 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 0.7rem;
    font-weight: 600;
}}

.status-badge {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}}

.status-good {{
    background: rgba(16, 167, 96, 0.1);
    color: {COLORS['good']};
}}

.status-bad {{
    background: rgba(231, 76, 60, 0.1);
    color: {COLORS['bad']};
}}

.formation {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.5rem;
    margin: 2rem 0;
    padding: 2rem;
    background: {COLORS['card']};
    border-radius: 12px;
    border: 2px solid {COLORS['primary']};
}}

.formation-row {{
    display: flex;
    justify-content: center;
    gap: 1rem;
    flex-wrap: wrap;
}}

.player-badge {{
    background: {COLORS['primary']};
    color: white;
    border-radius: 50%;
    width: 80px;
    height: 80px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    text-align: center;
    font-size: 0.7rem;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}}

.player-badge:hover {{
    background: {COLORS['secondary']};
    transform: scale(1.1);
    box-shadow: 0 6px 12px rgba(0,0,0,0.15);
}}

@media (max-width: 768px) {{
    .header h1 {{
        font-size: 1.8rem;
    }}
    
    .formation {{
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
        padding: 1rem;
    }}
    
    .player-badge {{
        width: 60px;
        height: 60px;
        font-size: 0.6rem;
    }}
}}

.stTabs {{
    background: transparent;
}}

.stTabs [data-baseweb="tab"] {{
    font-weight: 600;
    color: {COLORS['text']};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 1rem 2rem;
}}

.stTabs [aria-selected="true"] {{
    color: {COLORS['primary']};
    border-bottom-color: {COLORS['primary']};
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


def draw_formation(squad: pd.DataFrame) -> Image.Image:
    """Draw a lineup formation as an image."""
    img = Image.new("RGB", (800, 1000), color=(248, 251, 255))
    draw = ImageDraw.Draw(img)
    
    # Simple font (use default)
    try:
        font_large = ImageFont.truetype("/Library/Fonts/Arial.ttf", 14)
        font_small = ImageFont.truetype("/Library/Fonts/Arial.ttf", 10)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw field
    draw.rectangle([50, 50, 750, 950], outline=(0, 102, 204), width=3)
    
    # Center line
    draw.line([400, 50, 400, 950], fill=(0, 102, 204), width=2)
    
    # Circle
    draw.ellipse([300, 400, 500, 600], outline=(0, 102, 204), width=2)
    
    # Position players
    positions = {1: [], 2: [], 3: [], 4: []}
    for row in squad.itertuples():
        positions[row.pos_id].append(row)
    
    # Arrange by formation
    gk = positions[1][:1]
    def_players = positions[2][:5]
    mid_players = positions[3][:5]
    fwd_players = positions[4][:3]
    
    y_gk = 150
    y_def = 300
    y_mid = 500
    y_fwd = 750
    
    # Draw GK
    for i, p in enumerate(gk):
        x = 400
        draw.ellipse([x-30, y_gk-30, x+30, y_gk+30], fill=(0, 102, 204), outline=(255, 255, 255), width=2)
        draw.text((x-20, y_gk-8), p.web_name[:10], font=font_small, fill=(255, 255, 255))
    
    # Draw DEF
    for i, p in enumerate(def_players):
        x = 150 + (i * 130)
        draw.ellipse([x-30, y_def-30, x+30, y_def+30], fill=(0, 102, 204), outline=(255, 255, 255), width=2)
        draw.text((x-25, y_def-8), p.web_name[:8], font=font_small, fill=(255, 255, 255))
    
    # Draw MID
    for i, p in enumerate(mid_players):
        x = 150 + (i * 130)
        draw.ellipse([x-30, y_mid-30, x+30, y_mid+30], fill=(0, 102, 204), outline=(255, 255, 255), width=2)
        draw.text((x-25, y_mid-8), p.web_name[:8], font=font_small, fill=(255, 255, 255))
    
    # Draw FWD
    for i, p in enumerate(fwd_players):
        x = 250 + (i * 130)
        draw.ellipse([x-30, y_fwd-30, x+30, y_fwd+30], fill=(0, 102, 204), outline=(255, 255, 255), width=2)
        draw.text((x-25, y_fwd-8), p.web_name[:8], font=font_small, fill=(255, 255, 255))
    
    return img


def format_player_card(player: pd.Series, summary: dict | None = None) -> dict:
    """Format player info for display."""
    form = player_form_stats(player.to_dict(), summary, gws=5) if summary else {}
    
    return {
        "name": player["web_name"],
        "team": player["team"],
        "pos": player["pos"],
        "price": player["price"],
        "xpts": player["xpts"],
        "value": player["value"],
        "ownership": player["selected_by"],
        "form_goals": form.get("goals", 0),
        "form_assists": form.get("assists", 0),
        "form_games": form.get("games", 0),
        "form_avg_pts": form.get("avg_points", 0),
    }


def calculate_trade_impact(squad: pd.DataFrame, out_player_id: int, in_player: pd.Series, budget_remaining: float) -> dict:
    """Calculate impact of a trade."""
    out_player = squad[squad["id"] == out_player_id].iloc[0]
    
    money_change = in_player["price"] - out_player["price"]
    points_change = in_player["xpts"] - out_player["xpts"]
    value_change = in_player["value"] - out_player["value"]
    
    return {
        "out_name": out_player["web_name"],
        "in_name": in_player["web_name"],
        "money_change": money_change,
        "points_change": points_change,
        "value_change": value_change,
        "new_budget": budget_remaining - money_change,
        "feasible": (budget_remaining - money_change) >= 0,
    }


# ============================================================================
# MAIN APP
# ============================================================================

# Header
st.markdown(
    f"<div class='header'><h1>⚽ FPLlab v3</h1><p>Optimize your Fantasy Premier League squad</p></div>",
    unsafe_allow_html=True
)

# Global settings (collapsed by default)
with st.expander("⚙️ Settings", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        season = st.number_input("Season", 2018, 2035, Config().season)
    with col2:
        horizon_main = st.slider("Gameweeks", 1, 10, 5, key="horizon_main")
    with col3:
        deep = st.slider("Deep fetch", 0, 500, 0, step=20)
    
    fresh = st.button("🔄 Refresh data", use_container_width=True)

if fresh:
    st.cache_data.clear()

# Load data
with st.spinner("Loading data…"):
    try:
        cfg, result, bundle = load_data(int(season), int(horizon_main), int(deep), fresh, None)
    except Exception as exc:
        st.error(f"Failed to load data: {exc}")
        st.stop()

players = result["players"]
fixtures = result["fixtures"]
start_gw = result["start_gw"]
gws = list(range(start_gw, start_gw + horizon_main))
cfg.budget = 100.0

# ============================================================================
# TAB 1: MY TEAM
# ============================================================================

tab1, tab2, tab3 = st.tabs(["👥 My Team", "⚙️ Optimize", "📊 Analytics"])

with tab1:
    st.markdown("### Your Squad")
    
    # Input squad
    col1, col2 = st.columns([3, 1])
    with col1:
        squad_text = st.text_area(
            "Paste player names (one per line)",
            height=150,
            placeholder="Haaland\nSaka\nOdegaard\n...",
            key="team_input"
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("📋 Load squad", use_container_width=True):
            st.session_state.squad_loaded = True
    
    if squad_text.strip() and st.session_state.get("squad_loaded"):
        squad_names = [n.strip() for n in squad_text.splitlines() if n.strip()]
        squad = load_squad_from_names(players, squad_names) if squad_names else players.iloc[0:0]
        
        if not squad.empty:
            # Budget display
            spent = squad["price"].sum()
            budget = cfg.budget
            pct = (spent / budget) * 100
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Budget spent", f"£{spent:.1f}m")
            col2.metric("Remaining", f"£{budget - spent:.1f}m")
            col3.metric("Ownership", f"{squad['selected_by'].mean():.1f}%")
            col4.metric("Projected (5GW)", f"{squad['xpts'].sum():.0f} pts")
            
            # Budget meter
            st.markdown(f"<div class='budget-meter'><div class='budget-meter-fill' style='width: {pct}%;'>{pct:.0f}%</div></div>", unsafe_allow_html=True)
            
            # Formation visualization
            xi = best_xi(squad)
            st.markdown(f"### Formation: {xi['formation']}")
            st.markdown(f"**Captain:** {xi['captain']['web_name']} ({xi['captain']['team']}) | **Vice:** {xi['vice']['web_name']}")
            st.markdown(f"**Projected:** {xi['total']:.0f} pts (with captain armband)")
            
            # Draw formation
            formation_img = draw_formation(xi["xi"])
            st.image(formation_img, use_column_width=True, caption="Your Starting XI")
            
            # Bench
            st.markdown("### Bench")
            bench_cols = st.columns(4)
            for i, (idx, p) in enumerate(xi["bench"].head(4).iterrows()):
                with bench_cols[i % 4]:
                    st.markdown(f"**{p['web_name']}**  \n{p['team']} • {p['pos']}  \n£{p['price']:.1f}m • {p['xpts']:.1f} pts")
            
            # Export lineup image
            col1, col2, col3 = st.columns(3)
            with col1:
                buf = io.BytesIO()
                formation_img.save(buf, format="PNG")
                st.download_button(
                    "🖼️ Download lineup",
                    data=buf.getvalue(),
                    file_name=f"lineup_gw{start_gw}.png",
                    mime="image/png",
                    use_container_width=True
                )
            
            with col2:
                csv = squad[["web_name", "team", "pos", "price", "xpts", "value"]].to_csv(index=False)
                st.download_button(
                    "📥 CSV export",
                    data=csv,
                    file_name=f"squad_gw{start_gw}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col3:
                st.markdown("**[→ Optimize squad](/?tab=2)**")
        else:
            st.warning("No players found. Check spelling.")
    else:
        st.info("Enter player names above to see your squad lineup.")

# ============================================================================
# TAB 2: OPTIMIZE
# ============================================================================

with tab2:
    st.markdown("### Build Optimized Squad")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("**⚙️ Settings**")
        opt_gws = st.slider("Gameweeks", 1, 10, horizon_main, key="opt_gws")
        opt_budget = st.slider("Budget (£m)", 80.0, 120.0, 100.0, step=0.5, key="opt_budget")
        
        st.markdown("**🔒 Lock players**")
        locked_names = st.multiselect(
            "Lock in (optional)",
            options=sorted(players["web_name"].unique()),
            key="locked_players_main"
        )
        
        if st.button("🗑️ Clear locked", use_container_width=True):
            st.session_state.locked_players_main = []
            st.rerun()
        
        if st.button("🔨 Build squad", use_container_width=True, key="build_main"):
            st.session_state.built_squad = True
    
    with col2:
        if st.session_state.get("built_squad"):
            with st.spinner("Optimizing…"):
                cfg_opt = Config(horizon_gws=opt_gws)
                cfg_opt.budget = opt_budget
                
                res_opt = build_best_squad(players, cfg_opt, budget=opt_budget, locked_names=locked_names)
                sq_opt = res_opt["squad"]
                xi_opt = res_opt["xi"]
                
                if res_opt["missing"]:
                    st.warning(f"Not found: {', '.join(res_opt['missing'])}")
                
                # Results
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Spend", f"£{sq_opt['price'].sum():.1f}m")
                col_b.metric("Projected", f"{sq_opt['xpts'].sum():.0f}")
                col_c.metric("XI+Cap", f"{xi_opt['total']:.0f}")
                col_d.metric("Formation", xi_opt["formation"])
                
                st.markdown("### Full Squad")
                st.dataframe(
                    sq_opt[["web_name", "team", "pos", "price", "xpts", "value", "confidence"]].sort_values(["pos", "xpts"], ascending=[True, False]),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Formation image
                st.markdown("### Starting XI")
                formation_opt_img = draw_formation(xi_opt["xi"])
                st.image(formation_opt_img, use_column_width=True)
                
                # Export
                col_x, col_y = st.columns(2)
                with col_x:
                    buf_opt = io.BytesIO()
                    formation_opt_img.save(buf_opt, format="PNG")
                    st.download_button(
                        "🖼️ Download lineup",
                        data=buf_opt.getvalue(),
                        file_name=f"optimal_squad_gw{start_gw}.png",
                        mime="image/png",
                        use_container_width=True
                    )
                
                with col_y:
                    csv_opt = sq_opt[["web_name", "team", "pos", "price", "xpts", "value"]].to_csv(index=False)
                    st.download_button(
                        "📥 CSV export",
                        data=csv_opt,
                        file_name=f"optimal_squad_gw{start_gw}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
        else:
            st.info("Click **Build squad** to generate optimal team.")

# ============================================================================
# TAB 3: ANALYTICS
# ============================================================================

with tab3:
    st.markdown("### Analytics & Insights")
    
    # Sub-tabs
    subtab_form, subtab_comp, subtab_fix = st.tabs(["📈 Form", "🎯 Comparison", "🗓️ Fixtures"])
    
    # FORM TAB
    with subtab_form:
        st.markdown("#### Player Form")
        
        col_filters, col_data = st.columns([1, 3])
        
        with col_filters:
            st.markdown("**Filters**")
            pos_filter = st.multiselect(
                "Position",
                options=["GK", "DEF", "MID", "FWD"],
                default=["GK", "DEF", "MID", "FWD"]
            )
            price_min = st.slider("Min price", 3.5, 16.0, 3.5, key="price_min_form")
            price_max = st.slider("Max price", 3.5, 16.0, 16.0, key="price_max_form")
            form_filter = st.selectbox("Form (last 5GW)", ["All", "Hot (↑)", "Warm", "Cold (↓)"])
        
        with col_data:
            view_form = players[
                (players["pos"].isin(pos_filter)) &
                (players["price"] >= price_min) &
                (players["price"] <= price_max)
            ].sort_values("xpts", ascending=False)
            
            # Form color coding
            st.markdown("**Top players this week**")
            for idx, p in view_form.head(15).iterrows():
                form_status = "🔥 Hot" if p["xpts"] > view_form["xpts"].quantile(0.75) else "🟡 Warm" if p["xpts"] > view_form["xpts"].quantile(0.25) else "❄️ Cold"
                st.markdown(f"**{p['web_name']}** ({p['team']}, {p['pos']})  \n£{p['price']:.1f}m • {p['xpts']:.1f} pts • {form_status} • {p['selected_by']:.1f}% owned")
            
            # Form chart
            if not view_form.empty:
                fig, ax = plt.subplots(figsize=(12, 5))
                ax.barh(view_form["web_name"].head(10), view_form["xpts"].head(10), color=COLORS["primary"])
                ax.set_xlabel("Expected points (5GW)")
                ax.set_title("Top 10 players by form")
                ax.invert_yaxis()
                st.pyplot(fig, use_container_width=True)
    
    # COMPARISON TAB
    with subtab_comp:
        st.markdown("#### Squad Comparison")
        
        col_squad_txt, col_optimal = st.columns(2)
        
        with col_squad_txt:
            st.markdown("**Your squad**")
            your_squad_text = st.text_area(
                "Paste your squad",
                height=150,
                key="compare_squad"
            )
            your_squad_names = [n.strip() for n in your_squad_text.splitlines() if n.strip()]
        
        with col_optimal:
            st.markdown("**Optimal squad**")
            if st.button("Generate optimal", use_container_width=True, key="gen_optimal"):
                st.session_state.show_optimal = True
        
        if your_squad_names and st.session_state.get("show_optimal"):
            your_sq = load_squad_from_names(players, your_squad_names)
            cfg_cmp = Config(horizon_gws=horizon_main)
            res_cmp = build_best_squad(players, cfg_cmp, budget=100.0)
            opt_sq = res_cmp["squad"]
            
            col_y, col_o = st.columns(2)
            
            with col_y:
                st.markdown("### Your squad")
                st.metric("Value", f"£{your_sq['price'].sum():.1f}m")
                st.metric("Points", f"{your_sq['xpts'].sum():.0f}")
                st.dataframe(your_sq[["web_name", "team", "pos", "xpts"]], use_container_width=True, hide_index=True)
            
            with col_o:
                st.markdown("### Optimal")
                st.metric("Value", f"£{opt_sq['price'].sum():.1f}m")
                st.metric("Points", f"{opt_sq['xpts'].sum():.0f}")
                st.dataframe(opt_sq[["web_name", "team", "pos", "xpts"]], use_container_width=True, hide_index=True)
            
            # Differences
            st.markdown("### Differences")
            in_your = set(your_sq["id"]) & set(opt_sq["id"])
            only_your = set(your_sq["id"]) - set(opt_sq["id"])
            only_opt = set(opt_sq["id"]) - set(your_sq["id"])
            
            col_keep, col_remove, col_add = st.columns(3)
            
            with col_keep:
                st.markdown("**Keep** (in both)")
                for pid in list(in_your)[:5]:
                    p = your_sq[your_sq["id"] == pid].iloc[0]
                    st.markdown(f"✓ {p['web_name']}")
            
            with col_remove:
                st.markdown("**Remove** (only in yours)")
                for pid in list(only_your)[:5]:
                    p = your_sq[your_sq["id"] == pid].iloc[0]
                    st.markdown(f"✗ {p['web_name']}")
            
            with col_add:
                st.markdown("**Add** (only in optimal)")
                for pid in list(only_opt)[:5]:
                    p = opt_sq[opt_sq["id"] == pid].iloc[0]
                    st.markdown(f"✓ {p['web_name']}")
    
    # FIXTURES TAB
    with subtab_fix:
        st.markdown("#### Fixture Analysis")
        
        metric_type = st.selectbox("Show", ["Attacking (xGF)", "Defensive (xGA)"])
        key = "xgf" if "Attacking" in metric_type else "xga"
        
        pivot = fixtures.pivot_table(index="team", columns="gw", values=key, aggfunc="mean")
        
        if not pivot.empty:
            st.dataframe(pivot.round(2), use_container_width=True)
            
            # Heatmap
            fig, ax = plt.subplots(figsize=(12, 8))
            im = ax.imshow(pivot.values, cmap="RdYlGn_r" if key == "xga" else "RdYlGn", aspect="auto")
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_yticks(range(len(pivot.index)))
            ax.set_xticklabels([f"GW{c}" for c in pivot.columns])
            ax.set_yticklabels(pivot.index)
            ax.set_title(f"{metric_type}")
            plt.colorbar(im, ax=ax)
            st.pyplot(fig, use_container_width=True)

st.markdown("---")
st.markdown("<center><small>FPLlab v3 • Data from FPL API • Made with ❤️</small></center>", unsafe_allow_html=True)
