#!/usr/bin/env python3
"""
Debug script to see what team stats are available from NBA API
"""

from nba_api.stats.endpoints import leaguedashteamstats
import pandas as pd
import time

def check_available_stats():
    """Check what stats are available from the NBA API"""

    print("Checking NBA API for team statistics...")
    print("="*80)

    season = '2025-26'

    try:
        # Try to get team stats
        print(f"\nFetching team stats for {season} season...")
        team_stats = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type='Base',
            per_mode='PerGame'
        )

        time.sleep(0.6)

        stats_df = team_stats.get_data_frames()[0]

        print(f"✓ Found data for {len(stats_df)} teams")
        print(f"\nAvailable columns ({len(stats_df.columns)} total):")
        print("-"*80)

        for i, col in enumerate(stats_df.columns, 1):
            print(f"{i:3d}. {col}")

        # Show sample data for first 3 teams
        print("\n" + "="*80)
        print("Sample data (first 3 teams):")
        print("="*80)

        # Select relevant columns if they exist
        display_cols = ['TEAM_NAME']
        potential_cols = ['DEF_RATING', 'OPP_PTS', 'W', 'L', 'W_PCT']

        for col in potential_cols:
            if col in stats_df.columns:
                display_cols.append(col)

        print(stats_df[display_cols].head(3).to_string(index=False))

        # Check if DEF_RATING exists
        print("\n" + "="*80)
        if 'DEF_RATING' in stats_df.columns:
            print("✓ DEF_RATING column found!")
            print(f"  Sample values: {stats_df['DEF_RATING'].head().tolist()}")
        else:
            print("✗ DEF_RATING column NOT found")
            print("  Will need to use alternative metric")

        # Try different parameter combinations
        print("\n" + "="*80)
        print("Trying advanced defensive stats...")
        print("="*80)

        try:
            advanced_stats = leaguedashteamstats.LeagueDashTeamStats(
                season=season,
                measure_type='Advanced',
                per_mode='PerGame'
            )
            time.sleep(0.6)
            adv_df = advanced_stats.get_data_frames()[0]

            print(f"✓ Found advanced stats with {len(adv_df.columns)} columns")

            # Check for defensive columns
            def_cols = [col for col in adv_df.columns if 'DEF' in col or 'OPP' in col]
            if def_cols:
                print(f"\nDefensive-related columns found:")
                for col in def_cols:
                    print(f"  - {col}")
                    if 'RATING' in col:
                        print(f"    Sample: {adv_df[col].head(3).tolist()}")
            else:
                print("No defensive columns in advanced stats")

        except Exception as e:
            print(f"✗ Error fetching advanced stats: {e}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_available_stats()
