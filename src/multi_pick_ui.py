"""
Streamlit UI for multi-pick parlay analysis
"""

import streamlit as st
from database import get_session, Player
from simple_model import SimplePredictor
from multi_pick_analyzer import Pick, Parlay, MultiPickAnalyzer
import pandas as pd

# PrizePicks color scheme
PRIZEPICKS_GREEN = "#00d662"
DARK_BG = "#0e1117"
CARD_BG = "#1a1d24"

# Page configuration
st.set_page_config(
    page_title="Parlay Analyzer",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for PrizePicks styling
st.markdown(f"""
    <style>
    .main {{
        background-color: {DARK_BG};
    }}
    .stButton>button {{
        background-color: {PRIZEPICKS_GREEN};
        color: black;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
    }}
    .stButton>button:hover {{
        background-color: #00c158;
    }}
    .pick-card {{
        background-color: {CARD_BG};
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid {PRIZEPICKS_GREEN};
    }}
    .metric-card {{
        background-color: {CARD_BG};
        padding: 1.5rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem;
    }}
    .metric-value {{
        font-size: 2rem;
        font-weight: bold;
        color: {PRIZEPICKS_GREEN};
    }}
    .metric-label {{
        font-size: 0.9rem;
        color: #888;
        margin-top: 0.5rem;
    }}
    .recommendation-bet {{
        background-color: {PRIZEPICKS_GREEN};
        color: black;
        padding: 1rem;
        border-radius: 8px;
        font-size: 1.2rem;
        font-weight: bold;
        text-align: center;
        margin: 1rem 0;
    }}
    .recommendation-skip {{
        background-color: #ff4444;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        font-size: 1.2rem;
        font-weight: bold;
        text-align: center;
        margin: 1rem 0;
    }}
    h1, h2, h3 {{
        color: {PRIZEPICKS_GREEN};
    }}
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'picks' not in st.session_state:
    st.session_state.picks = []

if 'opponent_map' not in st.session_state:
    st.session_state.opponent_map = {}

if 'rest_map' not in st.session_state:
    st.session_state.rest_map = {}

# Load players from database
@st.cache_data
def load_players():
    """Load all players from database"""
    session = get_session()
    players = session.query(Player).order_by(Player.name).all()
    player_names = [p.name for p in players]
    session.close()
    return player_names

# Sidebar - Add Pick Form
st.sidebar.title("🏀 Add Pick")
st.sidebar.markdown("---")

with st.sidebar.form("add_pick_form", clear_on_submit=True):
    # Player dropdown
    player_names = load_players()

    if not player_names:
        st.error("No players found in database. Run data_collector.py first.")
    else:
        player = st.selectbox("Player", player_names)

        # Stat type dropdown
        stat_type = st.selectbox(
            "Stat Type",
            ["points", "rebounds", "assists", "steals", "blocks", "turnovers"]
        )

        # Line input
        line = st.number_input("Line", min_value=0.0, value=20.0, step=0.5)

        # Direction radio
        direction = st.radio("Direction", ["OVER", "UNDER"], horizontal=True)

        # Optional adjustments
        st.markdown("**Optional Adjustments**")
        opponent = st.text_input("Opponent (e.g., GSW, LAL)", value="")
        days_rest = st.number_input("Days Rest", min_value=0, max_value=7, value=None,
                                     help="0 = back-to-back, 2 = optimal")

        # Add button
        submitted = st.form_submit_button("➕ Add Pick", use_container_width=True)

        if submitted:
            # Create pick
            pick = Pick(
                player_name=player,
                stat_type=stat_type,
                line=line,
                direction=direction
            )

            # Add to session state
            st.session_state.picks.append(pick)

            # Store adjustments if provided
            if opponent:
                st.session_state.opponent_map[player] = opponent
            if days_rest is not None:
                st.session_state.rest_map[player] = days_rest

            st.success(f"Added {player} {stat_type} {direction} {line}")
            st.rerun()

# Sidebar - Current Picks
st.sidebar.markdown("---")
st.sidebar.title("📋 Current Picks")

if st.session_state.picks:
    for i, pick in enumerate(st.session_state.picks):
        col1, col2 = st.sidebar.columns([4, 1])

        with col1:
            st.markdown(f"""
                <div class="pick-card">
                    <strong>{pick.player_name}</strong><br>
                    {pick.stat_type.upper()} {pick.direction} {pick.line}
                </div>
            """, unsafe_allow_html=True)

        with col2:
            if st.button("❌", key=f"remove_{i}"):
                st.session_state.picks.pop(i)
                # Clean up adjustments
                if pick.player_name in st.session_state.opponent_map:
                    del st.session_state.opponent_map[pick.player_name]
                if pick.player_name in st.session_state.rest_map:
                    del st.session_state.rest_map[pick.player_name]
                st.rerun()

    if st.sidebar.button("🗑️ Clear All Picks", use_container_width=True):
        st.session_state.picks = []
        st.session_state.opponent_map = {}
        st.session_state.rest_map = {}
        st.rerun()
else:
    st.sidebar.info("No picks added yet. Use the form above to add picks.")

# Main Area
st.title("🎯 Parlay Analyzer")
st.markdown("---")

if not st.session_state.picks:
    st.info("👈 Add picks using the sidebar to get started!")
else:
    # Parlay configuration
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        # Default payout multipliers based on number of picks
        num_picks = len(st.session_state.picks)
        default_multipliers = {
            1: 1.0,
            2: 3.0,
            3: 6.0,
            4: 10.0,
            5: 15.0,
            6: 25.0
        }
        default_multiplier = default_multipliers.get(num_picks, num_picks * 3.0)

        payout_multiplier = st.number_input(
            "Payout Multiplier",
            min_value=1.0,
            value=default_multiplier,
            step=0.5,
            help=f"Default for {num_picks}-pick parlay"
        )

    with col2:
        stake = st.number_input(
            "Stake ($)",
            min_value=1.0,
            value=10.0,
            step=1.0
        )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_button = st.button("🔍 Analyze Parlay", use_container_width=True)

    # Analysis results
    if analyze_button:
        with st.spinner("Analyzing parlay..."):
            try:
                # Create parlay object
                parlay = Parlay(
                    picks=st.session_state.picks.copy(),
                    payout_multiplier=payout_multiplier,
                    stake=stake
                )

                # Initialize analyzer
                predictor = SimplePredictor(stat_type='points', lookback_games=10)
                analyzer = MultiPickAnalyzer(predictor)

                # Analyze parlay (suppress console output)
                import io
                import sys
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()

                result = analyzer.analyze_parlay(
                    parlay,
                    opponent_map=st.session_state.opponent_map,
                    rest_map=st.session_state.rest_map
                )

                sys.stdout = old_stdout
                predictor.close()

                # Display results
                st.markdown("## 📊 Analysis Results")
                st.markdown("---")

                # Recommendation banner
                if result.recommendation and "BET" in result.recommendation:
                    st.markdown(f"""
                        <div class="recommendation-bet">
                            ✅ {result.recommendation}
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class="recommendation-skip">
                            ❌ {result.recommendation}
                        </div>
                    """, unsafe_allow_html=True)

                # Metrics
                metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

                with metric_col1:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{result.parlay_probability*100:.1f}%</div>
                            <div class="metric-label">Parlay Probability</div>
                        </div>
                    """, unsafe_allow_html=True)

                with metric_col2:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">${result.expected_value:.2f}</div>
                            <div class="metric-label">Expected Value</div>
                        </div>
                    """, unsafe_allow_html=True)

                with metric_col3:
                    roi_color = PRIZEPICKS_GREEN if result.roi > 0 else "#ff4444"
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value" style="color: {roi_color};">{result.roi:.1f}%</div>
                            <div class="metric-label">ROI</div>
                        </div>
                    """, unsafe_allow_html=True)

                with metric_col4:
                    # Calculate Kelly
                    if result.payout_multiplier > 1 and result.parlay_probability:
                        kelly_fraction = (result.parlay_probability * result.payout_multiplier - 1) / \
                                       (result.payout_multiplier - 1)
                        quarter_kelly = kelly_fraction * 0.25 * 100
                    else:
                        quarter_kelly = 0

                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{quarter_kelly:.1f}%</div>
                            <div class="metric-label">Quarter Kelly</div>
                        </div>
                    """, unsafe_allow_html=True)

                # Payout breakdown
                st.markdown("### 💰 Payout Breakdown")
                potential_payout = stake * payout_multiplier
                potential_profit = potential_payout - stake

                payout_col1, payout_col2, payout_col3 = st.columns(3)
                with payout_col1:
                    st.metric("Stake", f"${stake:.2f}")
                with payout_col2:
                    st.metric("Potential Payout", f"${potential_payout:.2f}")
                with payout_col3:
                    st.metric("Potential Profit", f"${potential_profit:.2f}",
                             delta=f"{(potential_profit/stake)*100:.0f}%")

                # Individual pick breakdown
                st.markdown("### 📈 Individual Pick Breakdown")

                pick_data = []
                for pick in result.picks:
                    if pick.prediction is not None and pick.probability is not None:
                        pick_data.append({
                            "Player": pick.player_name,
                            "Stat": pick.stat_type.upper(),
                            "Line": pick.line,
                            "Direction": pick.direction,
                            "Prediction": f"{pick.prediction:.2f}",
                            "Probability": f"{pick.probability*100:.1f}%",
                            "Edge": f"{pick.prediction - pick.line:+.2f}" if pick.direction == "OVER"
                                    else f"{pick.line - pick.prediction:+.2f}"
                        })

                if pick_data:
                    df = pd.DataFrame(pick_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                # Show adjustments applied
                if st.session_state.opponent_map or st.session_state.rest_map:
                    st.markdown("### ⚙️ Adjustments Applied")

                    adj_data = []
                    for pick in result.picks:
                        adjustments = []
                        if pick.player_name in st.session_state.opponent_map:
                            adjustments.append(f"Opponent: {st.session_state.opponent_map[pick.player_name]}")
                        if pick.player_name in st.session_state.rest_map:
                            days = st.session_state.rest_map[pick.player_name]
                            rest_desc = {
                                0: "Back-to-back",
                                1: "1 day rest",
                                2: "2 days rest (optimal)",
                                3: "3 days rest"
                            }.get(days, f"{days} days rest")
                            adjustments.append(f"Rest: {rest_desc}")

                        if adjustments:
                            adj_data.append({
                                "Player": pick.player_name,
                                "Adjustments": ", ".join(adjustments)
                            })

                    if adj_data:
                        adj_df = pd.DataFrame(adj_data)
                        st.dataframe(adj_df, use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Error analyzing parlay: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #888; padding: 2rem 0;">
        <p>Built with ❤️ using Streamlit | Data powered by NBA API</p>
        <p><strong>Disclaimer:</strong> This is for educational purposes only.
        Gamble responsibly.</p>
    </div>
""", unsafe_allow_html=True)
