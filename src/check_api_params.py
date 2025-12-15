#!/usr/bin/env python3
"""
Check what parameters LeagueDashTeamStats accepts
"""

from nba_api.stats.endpoints import leaguedashteamstats
import inspect

print("LeagueDashTeamStats parameters:")
print("="*80)

# Get the signature
sig = inspect.signature(leaguedashteamstats.LeagueDashTeamStats.__init__)
print("\nParameters:")
for param_name, param in sig.parameters.items():
    if param_name != 'self':
        default = param.default if param.default != inspect.Parameter.empty else "Required"
        print(f"  {param_name}: {default}")

print("\n" + "="*80)
print("\nTrying basic call with minimal parameters...")

try:
    team_stats = leaguedashteamstats.LeagueDashTeamStats(
        season='2025-26'
    )
    print("✓ Success with just season parameter")

    import time
    time.sleep(0.6)

    stats_df = team_stats.get_data_frames()[0]
    print(f"✓ Got data for {len(stats_df)} teams")
    print(f"\nColumns available ({len(stats_df.columns)} total):")
    for i, col in enumerate(stats_df.columns, 1):
        print(f"  {i:3d}. {col}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
