"""
Streamlit web app for NBA player performance predictions
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from simple_model import SimplePredictor
from database import get_session, Player, GameStats
from data_collector import NBADataCollector
from multi_pick_analyzer import Pick, Parlay, MultiPickAnalyzer
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import desc
from scipy.stats import norm

# Page configuration
st.set_page_config(
    page_title="NBA Player Performance Predictor",
    page_icon="🏀",
    layout="wide"
)

# Initialize session state
if 'mode_selected' not in st.session_state:
    st.session_state.mode_selected = None

if 'parlay_picks' not in st.session_state:
    st.session_state.parlay_picks = []

if 'parlay_result' not in st.session_state:
    st.session_state.parlay_result = None

# Helper functions
@st.cache_data(ttl=3600)
def check_and_update_data():
    """Check if data needs updating"""
    session = get_session()
    try:
        most_recent_game = session.query(GameStats).order_by(desc(GameStats.game_date)).first()
        if most_recent_game:
            most_recent_date = most_recent_game.game_date
            days_since_update = (datetime.now().date() - most_recent_date).days
            if days_since_update >= 1:
                return True, f"Data is {days_since_update} days old"
        else:
            return True, "No data in database"
        return False, f"Data is up to date (last game: {most_recent_date})"
    finally:
        session.close()

def update_player_data(player_name):
    """Update data for a specific player"""
    try:
        collector = NBADataCollector()
        collector.fetch_player_game_stats(player_name, season='2025-26', max_games=30)
        collector.close()
        return True
    except Exception as e:
        st.error(f"Error updating data: {e}")
        return False

@st.cache_resource
def get_players_list():
    session = get_session()
    players = session.query(Player).order_by(Player.name).all()
    player_names = [p.name for p in players]
    session.close()
    return player_names

@st.cache_resource
def get_teams_list():
    from database import Team
    session = get_session()
    teams = session.query(Team).order_by(Team.abbreviation).all()
    team_options = {f"{t.abbreviation} - {t.name}": t.abbreviation for t in teams}
    session.close()
    return team_options

@st.cache_data(ttl=3600)
def get_league_average_def_rating():
    """Calculate league average defensive rating"""
    from database import TeamDefensiveStats
    session = get_session()
    try:
        teams = session.query(TeamDefensiveStats).all()
        ratings = [t.def_rating for t in teams if t.def_rating is not None]
        if ratings:
            return round(sum(ratings) / len(ratings), 1)
        else:
            return 112.0
    finally:
        session.close()

def get_days_since_last_game(player_name):
    """Calculate days since player's last game"""
    session = get_session()
    try:
        player = session.query(Player).filter_by(name=player_name).first()
        if player:
            most_recent = session.query(GameStats)\
                .filter_by(player_id=player.id)\
                .order_by(desc(GameStats.game_date))\
                .first()
            if most_recent:
                days_since = (datetime.now().date() - most_recent.game_date).days - 1
                return max(0, days_since)
    except:
        pass
    finally:
        session.close()
    return None

# Load data
player_names = get_players_list()
teams_dict = get_teams_list()
league_avg_def = get_league_average_def_rating()

# Title
st.title("🏀 NBA Player Performance Predictor")
st.markdown("### Advanced predictions using moving averages and defensive adjustments")

# ==========================================
# MODE SELECTION SCREEN
# ==========================================
if st.session_state.mode_selected is None:
    st.markdown("## Select Analysis Mode")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📊 Player Analyzer")
        st.markdown("Analyze a single player's performance with detailed predictions, charts, and betting recommendations.")
        if st.button("🎯 Player Analyzer", use_container_width=True, type="primary", key="btn_player"):
            st.session_state.mode_selected = "player"
            st.rerun()

    with col2:
        st.markdown("### 🎲 Parlay Builder")
        st.markdown("Build and analyze multi-player parlays with auto-calculated payouts and probabilities.")
        if st.button("🔮 Parlay Builder", use_container_width=True, type="primary", key="btn_parlay"):
            st.session_state.mode_selected = "parlay"
            st.rerun()

    with col3:
        st.markdown("### 💰 Paper Trading")
        st.markdown("Track your prediction accuracy with a $1000 simulated bankroll. View performance metrics and bankroll progression.")
        if st.button("💸 Paper Trading", use_container_width=True, type="primary", key="btn_paper"):
            st.session_state.mode_selected = "paper_trading"
            st.rerun()

# ==========================================
# PLAYER ANALYZER MODE
# ==========================================
elif st.session_state.mode_selected == "player":
    # Back button
    if st.sidebar.button("← Back to Mode Selection"):
        st.session_state.mode_selected = None
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("Player Analyzer Settings")

    # Data status
    needs_update, update_message = check_and_update_data()
    if needs_update:
        st.sidebar.warning(f"⚠️ {update_message}")
    else:
        st.sidebar.success(f"✅ {update_message}")

    # Player selection
    player_name = st.sidebar.selectbox(
        "Select Player",
        options=player_names,
        index=0 if player_names else None
    )

    # Refresh button
    if st.sidebar.button("🔄 Refresh Player Data"):
        with st.spinner(f"Updating data for {player_name}..."):
            if update_player_data(player_name):
                st.sidebar.success(f"✅ Updated data for {player_name}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.sidebar.error("Failed to update data")

    # Opponent Team Selection
    st.sidebar.subheader("🏀 Opponent Team")
    if teams_dict:
        opponent_selection = st.sidebar.selectbox(
            "Who are they playing against?",
            options=["None"] + list(teams_dict.keys()),
            index=0,
            help="Adjusts prediction based on opponent's defensive strength"
        )
        opponent_name = teams_dict[opponent_selection] if opponent_selection != "None" else None

        if opponent_name and opponent_name != "None":
            from database import Team, TeamDefensiveStats
            session = get_session()
            team = session.query(Team).filter_by(abbreviation=opponent_name).first()
            if team:
                def_stats = session.query(TeamDefensiveStats).filter_by(team_id=team.id).first()
                if def_stats and def_stats.def_rating:
                    diff = def_stats.def_rating - league_avg_def
                    if diff > 0:
                        st.sidebar.info(f"📊 {team.name} allows {def_stats.def_rating:.1f} pts/game ({diff:+.1f} vs league avg) - Easier matchup!")
                    else:
                        st.sidebar.info(f"📊 {team.name} allows {def_stats.def_rating:.1f} pts/game ({diff:+.1f} vs league avg) - Tougher matchup!")
            session.close()
    else:
        st.sidebar.warning("No teams in database")
        opponent_name = None

    # Stat type
    stat_type = st.sidebar.selectbox(
        "Stat Type",
        options=['points', 'rebounds', 'assists'],
        index=0
    )

    # Lookback games
    lookback_games = st.sidebar.slider(
        "Number of Recent Games",
        min_value=3,
        max_value=20,
        value=10,
        help="How many recent games to analyze"
    )

    # Decay factor
    decay_factor = st.sidebar.slider(
        "Decay Factor",
        min_value=0.7,
        max_value=1.0,
        value=0.9,
        step=0.05,
        help="Weight for recent games"
    )

    # Auto-calculate days of rest
    auto_days_rest = get_days_since_last_game(player_name)

    # Advanced options
    with st.sidebar.expander("Advanced Options"):
        if auto_days_rest is not None:
            st.info(f"Auto-detected: {auto_days_rest} days since last game")
            override_rest = st.checkbox("Override days of rest", value=False)
            if override_rest:
                days_rest = st.number_input(
                    "Custom Days of Rest",
                    min_value=0,
                    max_value=7,
                    value=auto_days_rest,
                    step=1
                )
            else:
                days_rest = auto_days_rest
        else:
            days_rest = st.number_input(
                "Days of Rest (optional)",
                min_value=0,
                max_value=7,
                value=None,
                step=1
            )

        st.markdown(f"**League Avg Defensive Rating:** {league_avg_def} pts/game")
        st.caption("Used as baseline for opponent adjustments")
        league_avg = league_avg_def

        line = st.number_input(
            "PrizePicks Line (optional)",
            min_value=0.0,
            value=None,
            step=0.5,
            help="Set to enable betting analysis"
        )

    # Generate Prediction button
    if st.sidebar.button("🔮 Generate Prediction", type="primary"):
        with st.spinner("Analyzing player performance..."):
            predictor = SimplePredictor(stat_type=stat_type, lookback_games=lookback_games)
            recent_stats = predictor.get_player_recent_stats(player_name)

            if recent_stats is None or recent_stats.empty:
                st.error(f"No data available for {player_name}")
                predictor.close()
            else:
                simple_pred, simple_std, _ = predictor.predict_simple_average(player_name, decay=decay_factor)
                weighted_pred, weighted_std, _ = predictor.predict_weighted_average(player_name, decay_factor=decay_factor)

                final_pred = weighted_pred
                adjustments_applied = []

                if opponent_name:
                    adjusted = predictor.apply_opponent_adjustment(final_pred, opponent_name, league_avg)
                    if adjusted != final_pred:
                        adjustments_applied.append(f"Opponent: {opponent_name}")
                        final_pred = adjusted

                if days_rest is not None:
                    adjusted = predictor.apply_rest_adjustment(final_pred, days_rest)
                    if adjusted != final_pred:
                        rest_desc = {0: "Back-to-back", 1: "1 day", 2: "2 days (optimal)", 3: "3 days", 4: "4+ days"}.get(min(days_rest, 4))
                        adjustments_applied.append(f"Rest: {rest_desc}")
                        final_pred = adjusted

                # Display results
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        label="Simple Average",
                        value=f"{simple_pred:.2f}",
                        delta=f"± {simple_std:.2f}"
                    )

                with col2:
                    st.metric(
                        label="Weighted Average",
                        value=f"{weighted_pred:.2f}",
                        delta=f"± {weighted_std:.2f}"
                    )

                with col3:
                    delta_val = final_pred - weighted_pred if adjustments_applied else None
                    st.metric(
                        label="Final Prediction",
                        value=f"{final_pred:.2f}",
                        delta=f"{delta_val:+.2f}" if delta_val else None
                    )

                if adjustments_applied:
                    st.info(f"**Adjustments Applied:** {', '.join(adjustments_applied)}")

                # Chart
                st.subheader(f"Recent {len(recent_stats)} Games Performance")

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(len(recent_stats), 0, -1)),
                    y=recent_stats[stat_type],
                    mode='lines+markers',
                    name='Actual',
                    line=dict(color='#1f77b4', width=2),
                    marker=dict(size=8)
                ))

                fig.add_hline(
                    y=final_pred,
                    line_dash="dash",
                    line_color="green",
                    annotation_text=f"Prediction: {final_pred:.2f}",
                    annotation_position="right"
                )

                fig.add_hrect(
                    y0=final_pred - weighted_std,
                    y1=final_pred + weighted_std,
                    fillcolor="green",
                    opacity=0.1,
                    line_width=0,
                    annotation_text="±1 SD",
                    annotation_position="left"
                )

                if line is not None:
                    fig.add_hline(
                        y=line,
                        line_dash="dot",
                        line_color="red",
                        annotation_text=f"Line: {line}",
                        annotation_position="right"
                    )

                fig.update_layout(
                    xaxis_title="Games Ago",
                    yaxis_title=stat_type.capitalize(),
                    hovermode='x unified',
                    showlegend=True,
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

                # Recent games table
                st.subheader("Recent Games Details")
                display_df = recent_stats[['date', 'opponent', 'is_home', 'days_rest', stat_type]].copy()
                display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
                display_df['is_home'] = display_df['is_home'].map({True: 'Home', False: 'Away'})
                display_df.columns = ['Date', 'Opponent', 'Home/Away', 'Days Rest', stat_type.capitalize()]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                # Betting analysis
                if line is not None:
                    st.subheader("📊 Betting Analysis")
                    eval_result = predictor.evaluate_against_line(final_pred, weighted_std, line)

                    if eval_result:
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("#### Probabilities")
                            prob_df = pd.DataFrame({
                                'Outcome': ['OVER', 'UNDER'],
                                'Probability': [
                                    f"{eval_result['prob_over']*100:.1f}%",
                                    f"{eval_result['prob_under']*100:.1f}%"
                                ],
                                'Expected Value': [
                                    f"{eval_result['ev_over']:.3f}",
                                    f"{eval_result['ev_under']:.3f}"
                                ]
                            })
                            st.dataframe(prob_df, use_container_width=True, hide_index=True)

                        with col2:
                            st.markdown("#### Recommendation")
                            recommendation = eval_result['recommendation']
                            confidence = eval_result['confidence']

                            if recommendation == 'OVER':
                                st.success(f"**BET OVER {line}**")
                            elif recommendation == 'UNDER':
                                st.success(f"**BET UNDER {line}**")
                            else:
                                st.warning("**SKIP THIS BET**")

                            st.metric(
                                label="Confidence Level",
                                value=f"{confidence:.2f} σ",
                                help="Standard deviations from the line"
                            )

                            z_score = eval_result['z_score']
                            if abs(z_score) >= 1.5:
                                st.info("High confidence bet")
                            elif abs(z_score) >= 1.0:
                                st.info("Moderate confidence bet")
                            else:
                                st.warning("Low confidence - consider skipping")

                        # Save as Paper Trade
                        st.markdown("---")
                        st.markdown("### 💾 Save as Paper Trade")

                        col_save1, col_save2, col_save3 = st.columns([1, 2, 1])

                        with col_save1:
                            stake_input = st.number_input(
                                "Stake Amount ($)",
                                min_value=1.0,
                                max_value=1000.0,
                                value=10.0,
                                step=1.0,
                                key="player_stake"
                            )

                        with col_save2:
                            direction_input = st.radio(
                                "Direction",
                                ["OVER", "UNDER"],
                                horizontal=True,
                                index=0 if recommendation == "OVER" else 1,
                                key="player_direction"
                            )

                        with col_save3:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("💾 Save Bet", type="primary", use_container_width=True, key="save_player_bet"):
                                from paper_trading import PaperTradingManager

                                manager = PaperTradingManager()

                                sufficient, available = manager.check_sufficient_funds(stake_input)
                                if not sufficient:
                                    st.error(f"Insufficient funds! Available: ${available:.2f}")
                                else:
                                    # Get player_id from database
                                    from database import Player
                                    session = manager.session
                                    player = session.query(Player).filter_by(name=player_name).first()

                                    if player:
                                        # Calculate EV for the selected direction
                                        prob = eval_result['prob_over'] if direction_input == 'OVER' else eval_result['prob_under']
                                        potential_payout = stake_input * (100 / 110)  # -110 odds
                                        ev = (prob * potential_payout) - ((1 - prob) * stake_input)

                                        bet_id = manager.place_single_bet(
                                            player_name=player_name,
                                            stat_type=stat_type,
                                            line=line,
                                            direction=direction_input,
                                            stake=stake_input,
                                            prediction=final_pred,
                                            probability=prob,
                                            confidence=abs(z_score),
                                            std_dev=weighted_std,
                                            opponent=opponent_name,
                                            days_rest=days_rest
                                        )

                                        if bet_id:
                                            st.success(f"✅ Bet saved! Bet ID: {bet_id}")
                                            st.balloons()
                                        else:
                                            st.error("Failed to save bet")
                                    else:
                                        st.error(f"Player {player_name} not found in database")

                                manager.close()

                predictor.close()

# ==========================================
# PARLAY BUILDER MODE
# ==========================================
elif st.session_state.mode_selected == "parlay":
    # Back button
    if st.sidebar.button("← Back to Mode Selection"):
        st.session_state.mode_selected = None
        st.session_state.parlay_picks = []  # Clear picks when going back
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("Parlay Builder")

    # Show current picks count
    num_picks = len(st.session_state.parlay_picks)
    st.sidebar.metric("Current Picks", num_picks)

    # Player selection
    player_name = st.sidebar.selectbox(
        "Select Player",
        options=player_names,
        key="parlay_player"
    )

    # Opponent
    st.sidebar.subheader("🏀 Opponent Team")
    if teams_dict:
        opponent_selection = st.sidebar.selectbox(
            "Who are they playing against?",
            options=["None"] + list(teams_dict.keys()),
            index=0,
            key="parlay_opponent"
        )
        opponent_name = teams_dict[opponent_selection] if opponent_selection != "None" else None
    else:
        opponent_name = None

    # Stat type
    stat_type = st.sidebar.selectbox(
        "Stat Type",
        options=['points', 'rebounds', 'assists'],
        index=0,
        key="parlay_stat"
    )

    # Line
    line = st.sidebar.number_input(
        "Line (Over/Under)",
        min_value=0.0,
        value=20.0,
        step=0.5,
        key="parlay_line",
        help="The PrizePicks line for this stat"
    )

    # Direction
    direction = st.sidebar.radio(
        "Direction",
        ["OVER", "UNDER"],
        horizontal=True,
        key="parlay_direction"
    )

    # Advanced options
    with st.sidebar.expander("Advanced Options for This Pick"):
        lookback_games = st.slider(
            "Number of Recent Games",
            min_value=3,
            max_value=20,
            value=10,
            key="parlay_lookback"
        )

        decay_factor = st.slider(
            "Decay Factor",
            min_value=0.7,
            max_value=1.0,
            value=0.9,
            step=0.05,
            key="parlay_decay"
        )

        auto_days_rest = get_days_since_last_game(player_name)
        if auto_days_rest is not None:
            st.info(f"Auto-detected: {auto_days_rest} days since last game")
            override_rest = st.checkbox("Override days of rest", value=False, key="parlay_override")
            if override_rest:
                days_rest = st.number_input(
                    "Custom Days of Rest",
                    min_value=0,
                    max_value=7,
                    value=auto_days_rest,
                    step=1,
                    key="parlay_rest"
                )
            else:
                days_rest = auto_days_rest
        else:
            days_rest = None

    # Add to Parlay button
    st.sidebar.markdown("---")
    if st.sidebar.button("➕ Add to Parlay", use_container_width=True):
        # Check duplicates
        duplicate = False
        for pick in st.session_state.parlay_picks:
            if pick['player'] == player_name and pick['stat_type'] == stat_type:
                st.sidebar.error(f"{player_name} {stat_type} already in parlay!")
                duplicate = True
                break

        if not duplicate:
            with st.spinner(f"Refreshing data for {player_name}..."):
                update_player_data(player_name)

            pick_config = {
                'player': player_name,
                'opponent': opponent_name,
                'stat_type': stat_type,
                'line': line,
                'direction': direction,
                'days_rest': days_rest,
                'lookback_games': lookback_games,
                'decay_factor': decay_factor
            }
            st.session_state.parlay_picks.append(pick_config)
            st.sidebar.success(f"Added {player_name} {stat_type} {direction} {line}")
            st.rerun()

    # Show current picks
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Current Picks")

    if st.session_state.parlay_picks:
        for i, pick in enumerate(st.session_state.parlay_picks):
            with st.sidebar.expander(
                f"Pick {i+1}: {pick['player']} | {pick['stat_type'].upper()} {pick['direction']} {pick['line']}",
                expanded=False
            ):
                st.write(f"**Player:** {pick['player']}")
                st.write(f"**Stat:** {pick['stat_type']}")
                st.write(f"**Line:** {pick['line']}")
                st.write(f"**Direction:** {pick['direction']}")
                if pick['opponent']:
                    st.write(f"**Opponent:** {pick['opponent']}")
                if pick['days_rest'] is not None:
                    st.write(f"**Days Rest:** {pick['days_rest']}")

                if st.button(f"❌ Remove", key=f"remove_{i}", use_container_width=True):
                    st.session_state.parlay_picks.pop(i)
                    st.rerun()

        if st.sidebar.button("🗑️ Clear All Picks", use_container_width=True):
            st.session_state.parlay_picks = []
            st.rerun()
    else:
        st.sidebar.info("No picks added yet. Configure a pick above and click 'Add to Parlay'.")

    # Main area
    if len(st.session_state.parlay_picks) == 0:
        st.info("👈 Add at least 2 picks using the sidebar to create a parlay!")
    elif len(st.session_state.parlay_picks) == 1:
        st.warning("Add at least 1 more pick to create a parlay. Single picks should use Player Analyzer mode.")
    else:
        st.markdown("## 🎯 Parlay Configuration")

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            num_picks = len(st.session_state.parlay_picks)
            standard_multipliers = {2: 3.0, 3: 6.0, 4: 10.0, 5: 15.0, 6: 25.0}
            default_multiplier = standard_multipliers.get(num_picks, num_picks * 2.5)

            payout_multiplier = st.number_input(
                f"Payout Multiplier ({num_picks}-leg parlay)",
                min_value=1.0,
                value=default_multiplier,
                step=0.5,
                help=f"Standard for {num_picks}-leg parlay: {default_multiplier}x"
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
            calculate_button = st.button("🔮 Calculate Parlay", type="primary", use_container_width=True)

        if calculate_button:
            with st.spinner("Calculating parlay probabilities..."):
                picks = []
                opponent_map = {}
                rest_map = {}

                for config in st.session_state.parlay_picks:
                    pick = Pick(
                        player_name=config['player'],
                        stat_type=config['stat_type'],
                        line=config['line'],
                        direction=config['direction']
                    )
                    picks.append(pick)

                    if config['opponent']:
                        opponent_map[config['player']] = config['opponent']
                    if config['days_rest'] is not None:
                        rest_map[config['player']] = config['days_rest']

                parlay = Parlay(
                    picks=picks,
                    payout_multiplier=payout_multiplier,
                    stake=stake
                )

                predictor = SimplePredictor(stat_type='points', lookback_games=10)
                analyzer = MultiPickAnalyzer(predictor)

                result = analyzer.analyze_parlay(
                    parlay,
                    opponent_map=opponent_map,
                    rest_map=rest_map
                )

                predictor.close()

                # Store result in session state
                st.session_state.parlay_result = result

        # Display results if they exist
        if st.session_state.parlay_result is not None:
            result = st.session_state.parlay_result

            # Recreate opponent_map and rest_map from session state
            opponent_map = {}
            rest_map = {}
            for config in st.session_state.parlay_picks:
                if config['opponent']:
                    opponent_map[config['player']] = config['opponent']
                if config['days_rest'] is not None:
                    rest_map[config['player']] = config['days_rest']

            st.markdown("---")
            st.markdown("## 📊 Parlay Analysis Results")

            if result.recommendation and "BET" in result.recommendation:
                st.success(f"✅ {result.recommendation}")
            else:
                st.error(f"❌ {result.recommendation}")

            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

            with metric_col1:
                st.metric(
                    "Parlay Probability",
                    f"{result.parlay_probability*100:.1f}%",
                    help="Probability all picks hit"
                )

            with metric_col2:
                st.metric(
                    "Expected Value",
                    f"${result.expected_value:.2f}",
                    delta=f"{result.roi:.1f}% ROI",
                    help="Expected profit/loss per bet"
                )

            with metric_col3:
                if result.payout_multiplier > 1 and result.parlay_probability:
                    kelly_fraction = (result.parlay_probability * result.payout_multiplier - 1) / (result.payout_multiplier - 1)
                    quarter_kelly = max(0, kelly_fraction * 0.25 * 100)
                else:
                    quarter_kelly = 0

                st.metric(
                    "Quarter Kelly",
                    f"{quarter_kelly:.1f}%",
                    help="Recommended bet size (% of bankroll)"
                )

            with metric_col4:
                potential_payout = stake * payout_multiplier
                potential_profit = potential_payout - stake

                st.metric(
                    "Potential Profit",
                    f"${potential_profit:.2f}",
                    delta=f"{payout_multiplier}x",
                    help="Profit if parlay hits"
                )

            # Individual pick breakdown
            st.markdown("### 📈 Individual Pick Breakdown")

            pick_data = []
            for pick in result.picks:
                if pick.prediction is not None and pick.probability is not None:
                    edge = pick.prediction - pick.line if pick.direction == "OVER" else pick.line - pick.prediction
                    pick_data.append({
                        "Player": pick.player_name,
                        "Stat": pick.stat_type.upper(),
                        "Line": pick.line,
                        "Direction": pick.direction,
                        "Prediction": f"{pick.prediction:.2f}",
                        "Probability": f"{pick.probability*100:.1f}%",
                        "Edge": f"{edge:+.2f}"
                    })

            if pick_data:
                df = pd.DataFrame(pick_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

            # Adjustments
            if opponent_map or rest_map:
                st.markdown("### ⚙️ Adjustments Applied")

                adj_data = []
                for pick in result.picks:
                    adjustments = []
                    if pick.player_name in opponent_map:
                        adjustments.append(f"Opponent: {opponent_map[pick.player_name]}")
                    if pick.player_name in rest_map:
                        days = rest_map[pick.player_name]
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

            # Explanation
            with st.expander("📖 How is Parlay Probability Calculated?"):
                st.markdown("**Individual Probabilities:**")
                for i, pick in enumerate(result.picks, 1):
                    if pick.probability:
                        st.write(f"- Pick {i} ({pick.player_name} {pick.stat_type.upper()} {pick.direction} {pick.line}): {pick.probability*100:.1f}%")

                st.markdown(f"""
                **Parlay Probability (assuming independence):**

                = {" × ".join([f"{p.probability*100:.1f}%" for p in result.picks if p.probability])}
                = **{result.parlay_probability*100:.1f}%**

                **Expected Value:**

                = (Probability × Payout) - ((1 - Probability) × Stake)
                = ({result.parlay_probability:.3f} × ${stake * payout_multiplier:.2f}) - ({1 - result.parlay_probability:.3f} × ${stake:.2f})
                = **${result.expected_value:.2f}**
                """)

            # Save Parlay as Paper Trade
            st.markdown("---")
            st.markdown("### 💾 Save Parlay as Paper Trade")

            col_parlay1, col_parlay2 = st.columns([3, 1])

            with col_parlay1:
                st.info(f"This {num_picks}-leg parlay will use the stake of ${stake:.2f} and {payout_multiplier}x multiplier configured above.")

            with col_parlay2:
                if st.button("💾 Save Parlay", type="primary", use_container_width=True, key="save_parlay_bet"):
                    from paper_trading import PaperTradingManager

                    manager = PaperTradingManager()

                    sufficient, available = manager.check_sufficient_funds(stake)
                    if not sufficient:
                        st.error(f"Insufficient funds! Available: ${available:.2f}")
                    else:
                        # Prepare picks data
                        picks_data = []
                        for pick in result.picks:
                            # Get player_id from database
                            from database import Player
                            session = manager.session
                            player = session.query(Player).filter_by(name=pick.player_name).first()

                            if player and pick.prediction is not None and pick.probability is not None:
                                # Find the corresponding config to get rest/opponent info
                                config = next((c for c in st.session_state.parlay_picks if c['player'] == pick.player_name and c['stat_type'] == pick.stat_type), None)

                                # Calculate confidence using z-score from normal distribution
                                # Using inverse CDF to get z-score from probability
                                if pick.direction == "OVER":
                                    z_score = abs(norm.ppf(1 - pick.probability)) if pick.probability < 1 else 3.0
                                else:
                                    z_score = abs(norm.ppf(1 - pick.probability)) if pick.probability < 1 else 3.0

                                picks_data.append({
                                    'player_id': player.id,
                                    'player_name': pick.player_name,
                                    'stat_type': pick.stat_type,
                                    'line': pick.line,
                                    'direction': pick.direction,
                                    'prediction': pick.prediction,
                                    'probability': pick.probability,
                                    'confidence': z_score,
                                    'opponent': config['opponent'] if config else None,
                                    'days_rest': config['days_rest'] if config else None
                                })

                        if len(picks_data) == len(result.picks):
                            try:
                                parlay_id = manager.place_parlay_bet(
                                    picks_data=picks_data,
                                    stake=stake,
                                    payout_multiplier=payout_multiplier,
                                    parlay_probability=result.parlay_probability,
                                    expected_value=result.expected_value
                                )

                                if parlay_id:
                                    st.success(f"✅ Parlay saved! Parlay ID: {parlay_id}")
                                    st.balloons()
                                else:
                                    st.error("Failed to save parlay - check console for details")
                            except Exception as e:
                                st.error(f"Error saving parlay: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
                        else:
                            st.error(f"Error: Some players not found in database. Found {len(picks_data)}/{len(result.picks)} players")

                    manager.close()

# ==========================================
# PAPER TRADING MODE
# ==========================================
elif st.session_state.mode_selected == "paper_trading":
    # Back button
    if st.sidebar.button("← Back to Mode Selection"):
        st.session_state.mode_selected = None
        st.rerun()

    from paper_trading_ui import render_paper_trading_mode
    render_paper_trading_mode()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
    <p>Model uses exponentially weighted moving averages with defensive and rest adjustments</p>
    <p>Always gamble responsibly. This is for educational purposes only.</p>
    </div>
    """,
    unsafe_allow_html=True
)
