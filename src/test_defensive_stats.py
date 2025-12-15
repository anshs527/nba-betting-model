#!/usr/bin/env python3
"""
Test different ways to get defensive stats
"""

from nba_api.stats.endpoints import leaguedashteamstats
import time

season = '2025-26'

print("Testing different parameter combinations for defensive stats...")
print("="*80)

# Test 1: Default stats with per_mode_detailed='Per100Possessions'
print("\nTest 1: Per100Possessions")
try:
    stats = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        per_mode_detailed='Per100Possessions'
    )
    time.sleep(0.6)
    df = stats.get_data_frames()[0]
    print(f"✓ Got {len(df.columns)} columns")

    # Check for defensive columns
    def_cols = [col for col in df.columns if 'DEF' in col or 'RATING' in col or 'OPP' in col]
    if def_cols:
        print(f"  Defensive columns: {def_cols}")
        # Show sample data
        if 'TEAM_NAME' in df.columns:
            sample = df[['TEAM_NAME'] + def_cols].head(3)
            print(sample.to_string(index=False))
    else:
        print("  No defensive columns found")
        print(f"  All columns: {list(df.columns)}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Try with opponent stats
print("\n" + "="*80)
print("\nTest 2: Checking for opponent/defensive measure types")
try:
    # The API has measure_type_detailed_defense parameter
    stats = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        measure_type_detailed_defense='Opponent'
    )
    time.sleep(0.6)
    df = stats.get_data_frames()[0]
    print(f"✓ Got {len(df.columns)} columns with Opponent measure")

    # Show all columns
    print(f"  Columns: {list(df.columns)}")

    # Show sample
    if 'TEAM_NAME' in df.columns and 'PTS' in df.columns:
        print(f"\n  Sample data (these are opponent/defensive stats):")
        sample = df[['TEAM_NAME', 'PTS', 'FG_PCT']].head(5)
        print(sample.to_string(index=False))

except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "="*80)
