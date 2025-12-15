#!/usr/bin/env python3
"""
Script to refactor streamlit_app.py to add parlay mode
"""

# Read the backup file
with open('streamlit_app.py.backup', 'r') as f:
    lines = f.readlines()

# Find key line numbers
player_selection_line = None
generate_button_line = None
predictor_close_line = None

for i, line in enumerate(lines):
    if '# Player selection' in line and player_selection_line is None:
        player_selection_line = i
    if 'Generate Prediction' in line and generate_button_line is None:
        generate_button_line = i
    if 'predictor.close()' in line:
        predictor_close_line = i

print(f"Player selection starts at line: {player_selection_line}")
print(f"Generate button at line: {generate_button_line}")
print(f"Predictor close at line: {predictor_close_line}")

# Now we know:
# - Lines before player_selection_line stay the same
# - Lines from player_selection_line to predictor_close_line need to be indented and wrapped in if not parlay_mode
# - After predictor_close_line, add else clause with parlay mode

# Build new file
new_lines = []

# Part 1: Keep everything up to player selection
new_lines.extend(lines[:player_selection_line])

# Part 2: Add conditional for single mode
new_lines.append("\n# ========================\n")
new_lines.append("# SINGLE PREDICTION MODE\n")
new_lines.append("# ========================\n")
new_lines.append("if not st.session_state.parlay_mode:\n")

# Part 3: Indent single prediction content
for line in lines[player_selection_line:predictor_close_line + 1]:
    if line.strip():  # Not empty line
        new_lines.append("    " + line)
    else:
        new_lines.append(line)

# Part 4: Add parlay mode
new_lines.append("\n# ========================\n")
new_lines.append("# PARLAY BUILDER MODE\n")
new_lines.append("# ========================\n")
new_lines.append("else:\n")
new_lines.append("    st.sidebar.info('Parlay Mode - Add multiple picks')\n")
new_lines.append("    # TODO: Add parlay UI here\n")
new_lines.append("    st.write('Parlay builder coming soon!')\n")

# Part 5: Add footer
new_lines.extend(lines[predictor_close_line + 1:])

# Write new file
with open('streamlit_app.py', 'w') as f:
    f.writelines(new_lines)

print("Refactoring complete!")
