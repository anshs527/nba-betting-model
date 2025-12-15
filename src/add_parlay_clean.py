#!/usr/bin/env python3
"""
Clean integration of parlay mode into streamlit_app.py
"""

# Read original file
with open('streamlit_app.py', 'r') as f:
    lines = f.readlines()

# Find key markers
imports_end = None
sidebar_start = None
player_selection_start = None
footer_start = None

for i, line in enumerate(lines):
    if 'from sqlalchemy import desc' in line:
        imports_end = i
    if '# Sidebar for inputs' in line:
        sidebar_start = i
    if '# Player selection' in line and player_selection_start is None:
        player_selection_start = i
    if '# Footer' in line:
        footer_start = i

print(f"Found markers:")
print(f"  imports_end: {imports_end}")
print(f"  sidebar_start: {sidebar_start}")
print(f"  player_selection_start: {player_selection_start}")
print(f"  footer_start: {footer_start}")

# Build new file
new_lines = []

# Part 1: Keep everything up to imports
new_lines.extend(lines[:imports_end+1])

# Add new import
new_lines.append("from multi_pick_analyzer import Pick, Parlay, MultiPickAnalyzer\n")
new_lines.append("\n")

# Part 2: Keep page config and functions up to sidebar start
for i in range(imports_end+1, sidebar_start):
    new_lines.append(lines[i])

# Add session state initialization before sidebar
new_lines.append("# Initialize session state for parlay mode\n")
new_lines.append("if 'parlay_mode' not in st.session_state:\n")
new_lines.append("    st.session_state.parlay_mode = False\n")
new_lines.append("\n")
new_lines.append("if 'parlay_picks' not in st.session_state:\n")
new_lines.append("    st.session_state.parlay_picks = []\n")
new_lines.append("\n")

# Part 3: Sidebar header and mode toggle
new_lines.extend(lines[sidebar_start:sidebar_start+2])  # Sidebar header
new_lines.append("\n")
new_lines.append("# Mode selection\n")
new_lines.append("mode = st.sidebar.radio(\n")
new_lines.append("    \"Select Mode\",\n")
new_lines.append("    [\"Player Analyzer\", \"Parlay Builder\"],\n")
new_lines.append("    index=0 if not st.session_state.parlay_mode else 1\n")
new_lines.append(")\n")
new_lines.append("\n")
new_lines.append("st.session_state.parlay_mode = (mode == \"Parlay Builder\")\n")
new_lines.append("\n")
new_lines.append("st.sidebar.markdown(\"---\")\n")
new_lines.append("\n")

# Continue with data status and helper functions (skip sidebar header line)
# Find where player_names are defined
player_names_line = None
for i in range(sidebar_start+2, player_selection_start):
    if 'player_names = get_players_list()' in lines[i]:
        player_names_line = i
        break

# Add everything up to player_names
for i in range(sidebar_start+2, player_names_line+3):  # +3 to include teams_dict and league_avg_def
    new_lines.append(lines[i])

# Part 4: Wrap single prediction mode
new_lines.append("\n")
new_lines.append("# ========================\n")
new_lines.append("# PLAYER ANALYZER MODE\n")
new_lines.append("# ========================\n")
new_lines.append("if not st.session_state.parlay_mode:\n")

# Indent all single prediction code
for i in range(player_selection_start, footer_start):
    line = lines[i]
    if line.strip():  # Not empty
        new_lines.append("    " + line)
    else:
        new_lines.append(line)

# Part 5: Add parlay mode
parlay_code = '''
# ========================
# PARLAY BUILDER MODE
# ========================
else:
    st.sidebar.subheader("Build Your Parlay")

    # Show current picks count
    num_picks = len(st.session_state.parlay_picks)
    st.sidebar.metric("Current Picks", num_picks)

    # Player selection for new pick
    player_name = st.sidebar.selectbox(
        "Select Player",
        options=player_names,
        key="parlay_player_select"
    )

    # Opponent selection
    st.sidebar.subheader("🏀 Opponent Team")
    if teams_dict:
        opponent_selection = st.sidebar.selectbox(
            "Who are they playing against?",
            options=["None"] + list(teams_dict.keys()),
            index=0,
            key="parlay_opponent_select"
        )
        opponent_name = teams_dict[opponent_selection] if opponent_selection != "None" else None
    else:
        opponent_name = None

    # Stat type
    stat_type = st.sidebar.selectbox(
        "Stat Type",
        options=['points', 'rebounds', 'assists'],
        index=0,
        key="parlay_stat_select"
    )

    # Line
    line = st.sidebar.number_input(
        "Line (Over/Under)",
        min_value=0.0,
        value=20.0,
        step=0.5,
        key="parlay_line_input",
        help="The PrizePicks line for this stat"
    )

    # Direction
    direction = st.sidebar.radio(
        "Direction",
        ["OVER", "UNDER"],
        horizontal=True,
        key="parlay_direction_radio"
    )

    # Advanced options for this pick
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

        # Auto-calculate days of rest
        auto_days_rest = get_days_since_last_game(player_name)
        if auto_days_rest is not None:
            st.info(f"Auto-detected: {auto_days_rest} days since last game")
            override_rest = st.checkbox("Override days of rest", value=False, key="parlay_override_rest")
            if override_rest:
                days_rest = st.number_input(
                    "Custom Days of Rest",
                    min_value=0,
                    max_value=7,
                    value=auto_days_rest,
                    step=1,
                    key="parlay_custom_rest"
                )
            else:
                days_rest = auto_days_rest
        else:
            days_rest = None

    # Add to Parlay button
    st.sidebar.markdown("---")
    add_disabled = player_name is None or line is None or line == 0.0

    if st.sidebar.button("➕ Add to Parlay", disabled=add_disabled, use_container_width=True):
        # Check for duplicates
        duplicate = False
        for existing_pick in st.session_state.parlay_picks:
            if existing_pick['player'] == player_name and existing_pick['stat_type'] == stat_type:
                st.sidebar.error(f"{player_name} {stat_type} already in parlay!")
                duplicate = True
                break

        if not duplicate:
            # Auto-refresh player data
            with st.spinner(f"Refreshing data for {player_name}..."):
                update_player_data(player_name)

            # Add pick to parlay
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

                if st.button(f"❌ Remove", key=f"remove_pick_{i}", use_container_width=True):
                    st.session_state.parlay_picks.pop(i)
                    st.rerun()

        if st.sidebar.button("🗑️ Clear All Picks", use_container_width=True):
            st.session_state.parlay_picks = []
            st.rerun()
    else:
        st.sidebar.info("No picks added yet. Configure a pick above and click 'Add to Parlay'.")

    # Main area - Parlay configuration and results
    if len(st.session_state.parlay_picks) == 0:
        st.info("👈 Add at least 2 picks using the sidebar to create a parlay!")
    elif len(st.session_state.parlay_picks) == 1:
        st.warning("Add at least 1 more pick to create a parlay. Single picks should use Player Analyzer mode.")
    else:
        # Show parlay configuration
        st.markdown("## 🎯 Parlay Configuration")

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            # Auto-calculate standard multiplier
            num_picks = len(st.session_state.parlay_picks)
            standard_multipliers = {
                2: 3.0,
                3: 6.0,
                4: 10.0,
                5: 15.0,
                6: 25.0
            }
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

        # Calculate parlay when button clicked
        if calculate_button:
            with st.spinner("Calculating parlay probabilities..."):
                # Build picks list
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

                # Create parlay
                parlay = Parlay(
                    picks=picks,
                    payout_multiplier=payout_multiplier,
                    stake=stake
                )

                # Analyze parlay
                predictor = SimplePredictor(stat_type='points', lookback_games=10)
                analyzer = MultiPickAnalyzer(predictor)

                result = analyzer.analyze_parlay(
                    parlay,
                    opponent_map=opponent_map,
                    rest_map=rest_map
                )

                predictor.close()

                # Display results
                st.markdown("---")
                st.markdown("## 📊 Parlay Analysis Results")

                # Recommendation banner
                if result.recommendation and "BET" in result.recommendation:
                    st.success(f"✅ {result.recommendation}")
                else:
                    st.error(f"❌ {result.recommendation}")

                # Key metrics
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
                    # Calculate Kelly
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

                # Show adjustments if any
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

                # Probability explanation
                with st.expander("📖 How is Parlay Probability Calculated?"):
                    st.markdown(f"""
                    **Individual Probabilities:**
                    """)
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

'''

new_lines.append(parlay_code)
new_lines.append("\n")

# Part 6: Add footer
new_lines.extend(lines[footer_start:])

# Write new file
with open('streamlit_app.py', 'w') as f:
    f.writelines(new_lines)

print(f"✓ Successfully created new streamlit_app.py")
print(f"✓ Total lines: {len(new_lines)}")
