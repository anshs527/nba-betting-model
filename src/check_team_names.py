#!/usr/bin/env python3
"""
Check team name mismatches between database and NBA API
"""

from database import get_session, Team
from nba_api.stats.endpoints import leaguedashteamstats
import time

def check_team_names():
    """Compare team names in database vs NBA API"""

    session = get_session()

    print("Comparing team names...")
    print("="*80)

    # Get teams from database
    db_teams = session.query(Team).order_by(Team.abbreviation).all()
    print(f"\nTeams in database: {len(db_teams)}")

    db_team_names = {t.name: t.abbreviation for t in db_teams}
    db_abbrevs = {t.abbreviation: t.name for t in db_teams}

    # Get teams from NBA API
    try:
        team_stats = leaguedashteamstats.LeagueDashTeamStats(
            season='2025-26',
            measure_type_detailed_defense='Opponent',
            per_mode_detailed='PerGame'
        )
        time.sleep(0.6)
        stats_df = team_stats.get_data_frames()[0]

        api_team_names = set(stats_df['TEAM_NAME'].tolist())
        print(f"Teams from NBA API: {len(api_team_names)}")

        # Find mismatches
        print("\n" + "="*80)
        print("TEAM NAME COMPARISON")
        print("="*80)

        print("\nTeams in API but NOT in database:")
        print("-"*80)
        for api_name in sorted(api_team_names):
            if api_name not in db_team_names:
                print(f"  ✗ {api_name}")

        print("\nTeams in database but NOT in API:")
        print("-"*80)
        for db_name in sorted(db_team_names.keys()):
            if db_name not in api_team_names:
                print(f"  ✗ {db_name}")
                # Try to find similar names
                for api_name in api_team_names:
                    if db_team_names[db_name] in api_name or any(word in api_name for word in db_name.split()):
                        print(f"     → Possible match: {api_name}")

        print("\n" + "="*80)
        print("EXACT MATCHES")
        print("="*80)
        matches = 0
        for db_name in sorted(db_team_names.keys()):
            if db_name in api_team_names:
                matches += 1
                print(f"  ✓ {db_team_names[db_name]}: {db_name}")

        print(f"\nTotal exact matches: {matches}/{len(db_teams)}")

        # Show all API names for reference
        print("\n" + "="*80)
        print("ALL API TEAM NAMES (for reference)")
        print("="*80)
        for name in sorted(api_team_names):
            print(f"  {name}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()

if __name__ == "__main__":
    check_team_names()
