#!/usr/bin/env python3
"""
Add parlay mode to streamlit_app.py
This script reads the original file and creates a new version with parlay support
"""

# Parlay mode UI to insert
PARLAY_MODE_UI = '''
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
        st.warning("Add at least 1 more pick to create a parlay. Single picks should use Single Prediction mode.")
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
                        kelly_fraction = (result.parlay_probability * result.payout_multiplier - 1) / \
                                       (result.payout_multiplier - 1)
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

# Read original file
with open('streamlit_app.py', 'r') as f:
    content = f.read()

# Insert imports
import_insert = "from multi_pick_analyzer import Pick, Parlay, MultiPickAnalyzer\n"
content = content.replace(
    "from data_collector import NBADataCollector\n",
    f"from data_collector import NBADataCollector\n{import_insert}"
)

# Insert session state initialization
session_state_init = '''
# Initialize session state for parlay mode
if 'parlay_mode' not in st.session_state:
    st.session_state.parlay_mode = False

if 'parlay_picks' not in st.session_state:
    st.session_state.parlay_picks = []

if 'current_pick_config' not in st.session_state:
    st.session_state.current_pick_config = {
        'player': None,
        'opponent': None,
        'stat_type': 'points',
        'line': None,
        'direction': 'OVER',
        'days_rest': None,
        'lookback_games': 10,
        'decay_factor': 0.9
    }

'''

content = content.replace(
    "# Title\n",
    f"{session_state_init}# Title\n"
)

# Insert mode toggle
mode_toggle = '''
# Mode toggle
mode = st.sidebar.radio(
    "Select Mode",
    ["Single Prediction", "Parlay Builder"],
    index=0 if not st.session_state.parlay_mode else 1,
    help="Single: Analyze one player | Parlay: Build multi-player parlay"
)

if mode == "Parlay Builder":
    st.session_state.parlay_mode = True
else:
    st.session_state.parlay_mode = False

st.sidebar.markdown("---")

'''

content = content.replace(
    "# Sidebar for inputs\nst.sidebar.header(\"Prediction Settings\")\n",
    f"# Sidebar for inputs\nst.sidebar.header(\"Prediction Settings\")\n{mode_toggle}"
)

# Wrap single prediction in conditional
content = content.replace(
    "# Player selection\nplayer_name = st.sidebar.selectbox(",
    "# ========================\n# SINGLE PREDICTION MODE\n# ========================\nif not st.session_state.parlay_mode:\n    # Player selection\n    player_name = st.sidebar.selectbox("
)

# Indent single prediction content (this is tricky, need to be careful)
# Find where to close the if block (just before footer)
footer_marker = "# Footer\nst.markdown(\"---\")"
parlay_mode_insertion = f"\n{PARLAY_MODE_UI}\n\n{footer_marker}"
content = content.replace(footer_marker, parlay_mode_insertion)

# Indent all lines after "if not st.session_state.parlay_mode:" until "# Footer"
lines = content.split('\n')
new_lines = []
indent_section = False
indent_level = 0

for i, line in enumerate(lines):
    if 'if not st.session_state.parlay_mode:' in line and 'SINGLE PREDICTION MODE' in lines[max(0, i-2):i+1]:
        indent_section = True
        indent_level = 1
        new_lines.append(line)
    elif indent_section and ('# PARLAY BUILDER MODE' in line or (line.strip().startswith('else:') and '# PARLAY BUILDER MODE' in lines[min(i+1, len(lines)-1):min(i+4, len(lines))])):
        indent_section = False
        new_lines.append(line)
    elif indent_section:
        if line.strip() and not line.startswith(' '):
            # Line needs indenting
            new_lines.append('    ' + line)
        elif line.strip():
            # Already has some indentation
            new_lines.append('    ' + line)
        else:
            # Empty line
            new_lines.append(line)
    else:
        new_lines.append(line)

# Write new file
with open('streamlit_app.py', 'w') as f:
    f.write('\n'.join(new_lines))

print("✓ Added parlay mode to streamlit_app.py")
print(f"✓ Total lines: {len(new_lines)}")
