"""
NBA Sports Betting Analyzer - Web Interface
A modern, sporty UI for analyzing player performance and betting lines
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sys
sys.path.append('src')

from database import get_session, Player, GameStats
from simple_model import SimplePredictor
from data_collector import NBADataCollector

# Page configuration
st.set_page_config(
    page_title="PrizePicks Betting Analyzer",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for PrizePicks theme (green and black)
st.markdown("""
    <style>
    .main {
        background-color: #0d1117;
    }
    .stApp {
        background-color: #0d1117;
    }
    h1 {
        color: #00d662;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        font-family: 'Arial Black', sans-serif;
    }
    h2, h3 {
        color: #00d662;
        font-family: 'Arial', sans-serif;
    }
    .stButton>button {
        background: linear-gradient(135deg, #00d662 0%, #00a651 100%);
        color: white;
        font-weight: bold;
        border-radius: 10px;
        padding: 10px 25px;
        border: none;
        font-size: 16px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #00ff73 0%, #00d662 100%);
        transform: scale(1.05);
    }
    .metric-card {
        background: rgba(0, 214, 98, 0.1);
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #00d662;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00d662;
    }
    div[data-testid="stMetricLabel"] {
        color: #8b949e;
    }
    /* Hide the default Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Session state initialization
if 'selected_player' not in st.session_state:
    st.session_state.selected_player = None
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

def get_all_players():
    """Get list of all players in database"""
    session = get_session()
    players = session.query(Player).order_by(Player.name).all()
    player_names = [p.name for p in players]
    session.close()
    return player_names

def get_player_stats_df(player_name, n_games=20):
    """Get recent game stats as DataFrame"""
    predictor = SimplePredictor('points')
    df = predictor.get_player_recent_stats(player_name, n_games=n_games)
    predictor.close()
    return df

def create_performance_chart(df, stat_type='points'):
    """Create interactive performance chart"""
    if df is None or df.empty:
        return None
    
    fig = go.Figure()
    
    # Add performance line
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df[stat_type],
        mode='lines+markers',
        name=stat_type.title(),
        line=dict(color='#00d662', width=3),
        marker=dict(size=10, color='#00ff73')
    ))
    
    # Add average line
    avg = df[stat_type].mean()
    fig.add_hline(
        y=avg,
        line_dash="dash",
        line_color="#8b949e",
        annotation_text=f"Average: {avg:.1f}",
        annotation_position="right"
    )
    
    fig.update_layout(
        title=f"{stat_type.title()} - Last {len(df)} Games",
        xaxis_title="Date",
        yaxis_title=stat_type.title(),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=14),
        hovermode='x unified',
        height=400
    )
    
    return fig

def analyze_betting_line(player_name, stat_type, line_value, lookback_games):
    """Analyze a betting line for a player"""
    predictor = SimplePredictor(stat_type=stat_type, lookback_games=lookback_games)
    
    # Get predictions
    weighted_pred, weighted_std, recent_stats = predictor.predict_weighted_average(player_name)
    
    if weighted_pred is None:
        predictor.close()
        return None, None
    
    # Evaluate against line
    eval_result = predictor.evaluate_against_line(weighted_pred, weighted_std, line_value)
    predictor.close()
    
    return eval_result, recent_stats

# Header
st.markdown("<h1 style='text-align: center;'>PRIZEPICKS BETTING ANALYZER </h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: white;'>Data-Driven Sports Betting Analysis</h3>", unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.title("⚙️ Controls")
    
    # Player selection
    st.subheader("Select Player")
    players = get_all_players()
    
    if not players:
        st.error("No players in database! Run data_collector.py first.")
        st.stop()
    
    selected_player = st.selectbox(
        "Choose a player to analyze:",
        players,
        index=0
    )
    
    st.markdown("---")
    
    # Stat type selection
    st.subheader("Stat Type")
    stat_type = st.selectbox(
        "What stat to predict:",
        ['points', 'rebounds', 'assists', 'steals', 'blocks']
    )
    
    # Line value
    st.subheader("Betting Line")
    line_value = st.number_input(
        "Over/Under Line:",
        min_value=0.0,
        max_value=100.0,
        value=25.0,
        step=0.5
    )
    
    # Lookback games
    lookback_games = st.slider(
        "Games to analyze:",
        min_value=5,
        max_value=30,
        value=10,
        step=1
    )
    
    st.markdown("---")
    
    # Analyze button
    analyze_button = st.button("🔍 ANALYZE", use_container_width=True)
    
    st.markdown("---")
    st.caption("Built with Streamlit • Data from NBA API")

# Main content area
if analyze_button or st.session_state.selected_player:
    st.session_state.selected_player = selected_player
    
    # Player header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h2 style='text-align: center;'>{selected_player}</h2>", unsafe_allow_html=True)
    
    # Get analysis
    with st.spinner('🏀 Analyzing player performance...'):
        eval_result, recent_stats = analyze_betting_line(
            selected_player, stat_type, line_value, lookback_games
        )
    
    if eval_result is None:
        st.error(f"No data available for {selected_player}")
        st.stop()
    
    # Key metrics row
    st.markdown("### 📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Prediction",
            value=f"{eval_result['prediction']:.1f}",
            delta=f"{eval_result['prediction'] - line_value:.1f} vs line"
        )
    
    with col2:
        st.metric(
            label="Over Probability",
            value=f"{eval_result['prob_over']*100:.1f}%",
            delta=f"{(eval_result['prob_over']-0.5)*100:.1f}%"
        )
    
    with col3:
        st.metric(
            label="Expected Value",
            value=f"${eval_result['ev_over']:.3f}" if eval_result['ev_over'] > 0 else f"-${abs(eval_result['ev_over']):.3f}",
            delta="OVER" if eval_result['ev_over'] > 0 else "UNDER"
        )
    
    with col4:
        recommendation = eval_result['recommendation']
        rec_color = "#00d662" if recommendation == "OVER" else "#ff4757" if recommendation == "UNDER" else "#ffa502"
        st.markdown(f"""
            <div style='background-color: {rec_color}; padding: 15px; border-radius: 10px; text-align: center;'>
                <h3 style='color: white; margin: 0; font-weight: bold;'>{recommendation}</h3>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Recent Performance")
        if recent_stats is not None:
            chart = create_performance_chart(recent_stats, stat_type)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
    
    with col2:
        st.markdown("### 📊 Probability Distribution")
        
        # Create probability distribution chart
        import numpy as np
        from scipy.stats import norm
        
        x = np.linspace(
            eval_result['prediction'] - 3*eval_result['std_dev'],
            eval_result['prediction'] + 3*eval_result['std_dev'],
            100
        )
        y = norm.pdf(x, eval_result['prediction'], eval_result['std_dev'])
        
        fig = go.Figure()
        
        # Add distribution curve
        fig.add_trace(go.Scatter(
            x=x, y=y,
            fill='tozeroy',
            name='Probability',
            line=dict(color='#00d662', width=2),
            fillcolor='rgba(0, 214, 98, 0.3)'
        ))
        
        # Add line marker
        fig.add_vline(
            x=line_value,
            line_dash="dash",
            line_color="#8b949e",
            annotation_text=f"Line: {line_value}",
            annotation_position="top"
        )
        
        # Add prediction marker
        fig.add_vline(
            x=eval_result['prediction'],
            line_dash="dot",
            line_color="#00ff73",
            annotation_text=f"Prediction: {eval_result['prediction']:.1f}",
            annotation_position="top"
        )
        
        fig.update_layout(
            title="Statistical Distribution",
            xaxis_title=stat_type.title(),
            yaxis_title="Probability Density",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=14),
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Detailed analysis
    st.markdown("### 📋 Detailed Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Recent Games")
        if recent_stats is not None:
            display_df = recent_stats[['date', 'opponent', 'is_home', stat_type]].head(10)
            display_df['is_home'] = display_df['is_home'].map({True: '🏠 Home', False: '✈️ Away'})
            display_df.columns = ['Date', 'Opponent', 'Location', stat_type.title()]
            st.dataframe(display_df, use_container_width=True, height=400)
    
    with col2:
        st.markdown("#### Betting Breakdown")
        st.markdown(f"""
        **Line:** {line_value} {stat_type}
        
        **Prediction:** {eval_result['prediction']:.2f} ± {eval_result['std_dev']:.2f}
        
        **Z-Score:** {eval_result['z_score']:.2f} standard deviations
        
        **Probabilities:**
        - OVER {line_value}: **{eval_result['prob_over']*100:.1f}%**
        - UNDER {line_value}: **{eval_result['prob_under']*100:.1f}%**
        
        **Expected Values (at -110 odds):**
        - OVER: **${eval_result['ev_over']:.3f}** per $1 bet
        - UNDER: **${eval_result['ev_under']:.3f}** per $1 bet
        
        **Confidence:** {eval_result['confidence']:.2f} σ
        
        ---
        
        **Interpretation:**
        {"✅ This looks like a **strong OVER** bet!" if eval_result['ev_over'] > 0.1 else ""}
        {"✅ This looks like a **strong UNDER** bet!" if eval_result['ev_under'] > 0.1 else ""}
        {"⚠️ Close call - small edge either way" if abs(eval_result['ev_over']) < 0.05 else ""}
        {"❌ Skip this bet - no edge" if eval_result['recommendation'] == 'SKIP' else ""}
        """)

else:
    # Welcome screen
    st.markdown("""
        <div style='text-align: center; padding: 50px;'>
            <h2 style='color: #00d662;'>Welcome to the NBA Betting Analyzer!</h2>
            <p style='color: #c9d1d9; font-size: 18px;'>
                Select a player and betting line from the sidebar to begin your analysis.
            </p>
            <p style='color: #00d662; font-size: 16px;'>
                📊 Real-time NBA data • 🎯 Statistical predictions • 💰 Expected value calculations
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Show some stats
    st.markdown("### 📈 Database Stats")
    session = get_session()
    player_count = session.query(Player).count()
    game_count = session.query(GameStats).count()
    session.close()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Players Tracked", player_count)
    with col2:
        st.metric("Games Analyzed", game_count)
    with col3:
        st.metric("Stat Types", "5")