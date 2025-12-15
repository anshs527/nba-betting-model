#!/usr/bin/env python3
"""
Script to set up teams and their defensive statistics
Run this to populate team data in the database
"""

from data_collector import NBADataCollector
from database import get_session, Team, TeamDefensiveStats

def check_teams():
    """Check which teams are in the database"""
    session = get_session()

    try:
        teams = session.query(Team).all()
        print(f"\nTeams in database: {len(teams)}")

        if teams:
            print("\nTeam List:")
            print("-" * 60)
            for team in teams:
                # Check if defensive stats exist
                def_stats = session.query(TeamDefensiveStats).filter_by(team_id=team.id).first()
                def_rating = f"{def_stats.def_rating:.1f}" if def_stats and def_stats.def_rating else "No data"
                print(f"{team.abbreviation:5s} | {team.name:30s} | Def Rating: {def_rating}")
        else:
            print("No teams in database!")

    finally:
        session.close()

def setup_all_teams():
    """Fetch and populate all teams and their defensive stats"""
    collector = NBADataCollector()

    try:
        print("\n" + "="*60)
        print("Setting up NBA teams and defensive statistics")
        print("="*60 + "\n")

        # Step 1: Fetch all teams
        print("Step 1: Fetching all NBA teams...")
        collector.fetch_all_teams()

        # Step 2: Fetch defensive stats for current season
        print("\nStep 2: Fetching team defensive statistics for 2025-26 season...")
        collector.fetch_team_defensive_stats(season='2025-26')

        print("\n" + "="*60)
        print("Setup complete!")
        print("="*60 + "\n")

        # Show results
        check_teams()

    except Exception as e:
        print(f"\nError during setup: {e}")
        import traceback
        traceback.print_exc()

    finally:
        collector.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # Just check what's in the database
        check_teams()
    else:
        # Full setup
        setup_all_teams()
