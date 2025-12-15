"""
Paper Trading UI Components
Streamlit interface for paper trading mode
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from paper_trading import PaperTradingManager
from bet_resolver import BetResolver
from datetime import datetime, timedelta

def render_paper_trading_mode():
    """Main entry point for Paper Trading mode"""

    # Initialize manager
    manager = PaperTradingManager()
    resolver = BetResolver()

    # Sidebar controls
    st.sidebar.markdown("---")
    st.sidebar.header("Paper Trading Controls")

    # Auto-resolve button
    if st.sidebar.button("🤖 Auto-Resolve Bets", use_container_width=True):
        with st.spinner("Resolving bets with game data..."):
            num_resolved, num_failed = resolver.resolve_all_pending()
            if num_resolved > 0:
                st.sidebar.success(f"✅ Resolved {num_resolved} bets")
            if num_failed > 0:
                st.sidebar.warning(f"⚠️ Failed to resolve {num_failed} bets")
            if num_resolved == 0 and num_failed == 0:
                st.sidebar.info("No bets ready to resolve")
            st.rerun()

    # Reset account (danger zone)
    with st.sidebar.expander("⚠️ Danger Zone"):
        st.warning("Resetting will clear all bet history and start fresh with $1000")
        if st.button("Reset Account", use_container_width=True):
            manager.reset_account()
            st.sidebar.success("Account reset to $1000")
            st.rerun()

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "⏳ Pending Bets", "📜 History"])

    with tab1:
        render_portfolio_overview(manager)

    with tab2:
        render_pending_bets(manager, resolver)

    with tab3:
        render_bet_history(manager)

    # Cleanup
    manager.close()
    resolver.close()

def render_portfolio_overview(manager):
    """Render portfolio overview dashboard"""

    # Get account summary
    summary = manager.get_account_summary()

    # Metric cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Current Bankroll",
            value=f"${summary['current_bankroll']:.2f}",
            delta=f"${summary['total_profit']:.2f}",
            help="Current balance vs starting $1000"
        )

    with col2:
        st.metric(
            label="ROI",
            value=f"{summary['roi']:.1f}%",
            help="Return on Investment"
        )

    with col3:
        st.metric(
            label="Win Rate",
            value=f"{summary['win_rate']:.1f}%",
            help="Percentage of winning bets"
        )

    with col4:
        st.metric(
            label="Total Bets",
            value=f"{summary['total_bets']}",
            delta=f"{summary['pending_bets']} pending",
            help="Total bets placed"
        )

    # Bankroll chart
    st.markdown("---")
    st.subheader("💰 Bankroll Over Time")
    render_bankroll_chart(manager)

    # Metrics by stat type
    st.markdown("---")
    st.subheader("📈 Performance by Stat Type")
    render_metrics_by_stat(manager)

    # Confidence correlation
    st.markdown("---")
    st.subheader("🎯 Confidence Correlation")
    render_confidence_correlation(manager)

def render_bankroll_chart(manager):
    """Render bankroll progression chart"""

    history = manager.get_bankroll_history(days=30)

    if not history:
        st.info("No bankroll history yet. Place some bets to see your progression!")
        return

    # Prepare data
    timestamps = [h[0] for h in history]
    bankrolls = [h[1] for h in history]
    profits = [h[2] for h in history]

    # Create figure
    fig = go.Figure()

    # Add bankroll line
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=bankrolls,
        mode='lines+markers',
        name='Bankroll',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)'
    ))

    # Add starting bankroll reference line
    fig.add_hline(
        y=1000,
        line_dash="dash",
        line_color="gray",
        annotation_text="Starting Bankroll ($1000)",
        annotation_position="right"
    )

    # Update layout
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Bankroll ($)",
        hovermode='x unified',
        showlegend=True,
        height=400,
        yaxis=dict(tickprefix="$")
    )

    st.plotly_chart(fig, use_container_width=True)

def render_metrics_by_stat(manager):
    """Render performance breakdown by stat type"""

    metrics = manager.calculate_metrics_by_stat_type()

    if not metrics:
        st.info("No completed bets yet. Resolve some bets to see performance metrics!")
        return

    # Create DataFrame
    data = []
    for stat_type, stats in metrics.items():
        data.append({
            'Stat Type': stat_type.upper(),
            'Win Rate': f"{stats['win_rate']:.1f}%",
            'Total Bets': stats['total_bets'],
            'Profit': f"${stats['total_profit']:.2f}",
            'ROI': f"{stats['roi']:.1f}%"
        })

    if data:
        df = pd.DataFrame(data)

        # Display table
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Create bar chart for win rate
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=[d['Stat Type'] for d in data],
            y=[float(d['Win Rate'].rstrip('%')) for d in data],
            marker_color=['#28a745' if float(d['Win Rate'].rstrip('%')) >= 50 else '#dc3545' for d in data],
            text=[d['Win Rate'] for d in data],
            textposition='outside'
        ))

        fig.update_layout(
            xaxis_title="Stat Type",
            yaxis_title="Win Rate (%)",
            showlegend=False,
            height=300,
            yaxis=dict(range=[0, 100])
        )

        st.plotly_chart(fig, use_container_width=True)

def render_confidence_correlation(manager):
    """Render win rate by confidence level"""

    correlation = manager.calculate_confidence_correlation()

    if not correlation:
        st.info("No completed bets yet. Resolve some bets to see confidence correlation!")
        return

    # Create DataFrame
    data = []
    for confidence_level, stats in correlation.items():
        data.append({
            'Confidence Level': confidence_level.upper(),
            'Win Rate': f"{stats['win_rate']:.1f}%",
            'Total Bets': stats['total_bets']
        })

    if data:
        df = pd.DataFrame(data)

        # Display table
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Create bar chart
        fig = go.Figure()

        colors = {'LOW': '#ffc107', 'MEDIUM': '#17a2b8', 'HIGH': '#28a745'}

        fig.add_trace(go.Bar(
            x=[d['Confidence Level'] for d in data],
            y=[float(d['Win Rate'].rstrip('%')) for d in data],
            marker_color=[colors.get(d['Confidence Level'], '#6c757d') for d in data],
            text=[d['Win Rate'] for d in data],
            textposition='outside'
        ))

        fig.update_layout(
            xaxis_title="Confidence Level",
            yaxis_title="Win Rate (%)",
            showlegend=False,
            height=300,
            yaxis=dict(range=[0, 100])
        )

        st.plotly_chart(fig, use_container_width=True)

def render_pending_bets(manager, resolver):
    """Render pending bets with resolution interface"""

    # Sub-tabs for singles and parlays
    sub_tab1, sub_tab2 = st.tabs(["Single Bets", "Parlays"])

    with sub_tab1:
        render_pending_singles(manager, resolver)

    with sub_tab2:
        render_pending_parlays(manager, resolver)

def render_pending_singles(manager, resolver):
    """Render pending single bets"""

    pending = manager.get_pending_single_bets()

    if not pending:
        st.info("No pending single bets")
        return

    for bet in pending:
        with st.expander(
            f"#{bet.id} - {bet.player_name} | {bet.stat_type.upper()} {bet.direction} {bet.line} (${bet.stake})",
            expanded=False
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Bet Details**")
                st.write(f"Player: {bet.player_name}")
                st.write(f"Stat: {bet.stat_type.upper()}")
                st.write(f"Line: {bet.line}")
                st.write(f"Direction: {bet.direction}")
                st.write(f"Stake: ${bet.stake:.2f}")
                st.write(f"Potential Payout: ${bet.potential_payout:.2f}")
                if bet.opponent:
                    st.write(f"Opponent: {bet.opponent}")
                if bet.game_date:
                    st.write(f"Game Date: {bet.game_date}")

            with col2:
                st.markdown("**Prediction Data**")
                st.write(f"Model Prediction: {bet.prediction:.2f}")
                st.write(f"Win Probability: {bet.probability*100:.1f}%")
                st.write(f"Expected Value: ${bet.expected_value:.2f}")
                st.write(f"Confidence: {bet.confidence:.2f}σ")
                st.write(f"Placed: {bet.placed_at.strftime('%Y-%m-%d %H:%M')}")

            st.markdown("---")
            st.markdown("**Manual Resolution**")

            col_resolve1, col_resolve2, col_resolve3 = st.columns([2, 1, 1])

            with col_resolve1:
                actual_result = st.number_input(
                    f"Actual {bet.stat_type} value",
                    min_value=0.0,
                    step=0.5,
                    key=f"resolve_single_{bet.id}"
                )

            with col_resolve2:
                if st.button("✅ Resolve", key=f"btn_resolve_{bet.id}", use_container_width=True):
                    success, result = resolver.manual_resolve_single_bet(bet.id, actual_result)
                    if success:
                        st.success(f"Bet resolved! P/L: ${result:.2f}")
                        st.rerun()
                    else:
                        st.error(f"Error: {result}")

            with col_resolve3:
                if st.button("🚫 Void", key=f"btn_void_{bet.id}", use_container_width=True):
                    success, message = resolver.void_bet(bet.id, 'single', reason="Manual void")
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

def render_pending_parlays(manager, resolver):
    """Render pending parlay bets"""

    pending = manager.get_pending_parlay_bets()

    if not pending:
        st.info("No pending parlays")
        return

    for parlay in pending:
        with st.expander(
            f"#{parlay.id} - {parlay.num_picks}-leg Parlay | ${parlay.stake} for ${parlay.potential_payout:.2f} ({parlay.payout_multiplier}x)",
            expanded=False
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Parlay Details**")
                st.write(f"Number of Picks: {parlay.num_picks}")
                st.write(f"Stake: ${parlay.stake:.2f}")
                st.write(f"Multiplier: {parlay.payout_multiplier}x")
                st.write(f"Potential Payout: ${parlay.potential_payout:.2f}")
                st.write(f"Parlay Probability: {parlay.parlay_probability*100:.1f}%")
                st.write(f"Expected Value: ${parlay.expected_value:.2f}")
                st.write(f"Placed: {parlay.placed_at.strftime('%Y-%m-%d %H:%M')}")

            with col2:
                st.markdown("**Legs**")
                for i, leg in enumerate(parlay.legs, 1):
                    st.write(f"{i}. {leg.player_name} | {leg.stat_type.upper()} {leg.direction} {leg.line}")
                    st.caption(f"   Prediction: {leg.prediction:.2f} | Prob: {leg.probability*100:.1f}%")

            st.markdown("---")
            st.markdown("**Manual Resolution**")

            # Input for each leg
            leg_results = {}
            cols = st.columns(min(len(parlay.legs), 3))

            for i, leg in enumerate(parlay.legs):
                col_idx = i % 3
                with cols[col_idx]:
                    actual = st.number_input(
                        f"{leg.player_name} {leg.stat_type}",
                        min_value=0.0,
                        step=0.5,
                        key=f"resolve_parlay_{parlay.id}_leg_{leg.id}"
                    )
                    leg_results[leg.id] = actual

            col_resolve1, col_resolve2 = st.columns([1, 1])

            with col_resolve1:
                if st.button("✅ Resolve Parlay", key=f"btn_resolve_parlay_{parlay.id}", use_container_width=True):
                    success, result = resolver.manual_resolve_parlay_bet(parlay.id, leg_results)
                    if success:
                        st.success(f"Parlay resolved! P/L: ${result:.2f}")
                        st.rerun()
                    else:
                        st.error(f"Error: {result}")

            with col_resolve2:
                if st.button("🚫 Void Parlay", key=f"btn_void_parlay_{parlay.id}", use_container_width=True):
                    success, message = resolver.void_bet(parlay.id, 'parlay', reason="Manual void")
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

def render_bet_history(manager):
    """Render bet history with filters"""

    st.markdown("### Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        bet_type_filter = st.selectbox(
            "Bet Type",
            options=["All", "Singles", "Parlays"],
            index=0
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            options=["All", "Won", "Lost", "Void"],
            index=0
        )

    with col3:
        limit = st.number_input(
            "Show last N bets",
            min_value=10,
            max_value=200,
            value=50,
            step=10
        )

    # Map filter values
    status_map = {"All": None, "Won": "won", "Lost": "lost", "Void": "void"}
    status = status_map[status_filter]

    # Fetch history
    if bet_type_filter == "All" or bet_type_filter == "Singles":
        st.markdown("---")
        st.subheader("Single Bets")

        singles = manager.get_single_bet_history(limit=limit, status_filter=status)

        if singles:
            data = []
            for bet in singles:
                data.append({
                    'ID': bet.id,
                    'Date': bet.placed_at.strftime('%Y-%m-%d'),
                    'Player': bet.player_name,
                    'Stat': bet.stat_type.upper(),
                    'Line': bet.line,
                    'Direction': bet.direction,
                    'Prediction': f"{bet.prediction:.2f}",
                    'Actual': f"{bet.actual_result:.2f}" if bet.actual_result else "-",
                    'Stake': f"${bet.stake:.2f}",
                    'P/L': f"${bet.profit_loss:.2f}",
                    'Status': bet.status.upper()
                })

            df = pd.DataFrame(data)

            # Color code by status
            def color_status(val):
                if val == 'WON':
                    return 'background-color: #d4edda'
                elif val == 'LOST':
                    return 'background-color: #f8d7da'
                elif val == 'VOID':
                    return 'background-color: #fff3cd'
                return ''

            styled_df = df.style.applymap(color_status, subset=['Status'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("No single bet history")

    if bet_type_filter == "All" or bet_type_filter == "Parlays":
        st.markdown("---")
        st.subheader("Parlays")

        parlays = manager.get_parlay_bet_history(limit=limit, status_filter=status)

        if parlays:
            data = []
            for parlay in parlays:
                legs_summary = ", ".join([f"{leg.player_name} {leg.stat_type.upper()}" for leg in parlay.legs])

                data.append({
                    'ID': parlay.id,
                    'Date': parlay.placed_at.strftime('%Y-%m-%d'),
                    'Legs': f"{parlay.num_picks}-leg",
                    'Picks': legs_summary[:50] + "..." if len(legs_summary) > 50 else legs_summary,
                    'Multiplier': f"{parlay.payout_multiplier}x",
                    'Stake': f"${parlay.stake:.2f}",
                    'P/L': f"${parlay.profit_loss:.2f}",
                    'Status': parlay.status.upper()
                })

            df = pd.DataFrame(data)

            def color_status(val):
                if val == 'WON':
                    return 'background-color: #d4edda'
                elif val == 'LOST':
                    return 'background-color: #f8d7da'
                elif val == 'VOID':
                    return 'background-color: #fff3cd'
                return ''

            styled_df = df.style.applymap(color_status, subset=['Status'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("No parlay history")
