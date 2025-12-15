#!/usr/bin/env python3
"""
Create all database tables
Run this to set up the database schema
"""

from database import create_database, get_session, Player, Team, TeamDefensiveStats, GameStats
import os

def create_all_tables():
    """Create all tables in the database"""
    print("Creating database tables...")
    print("-" * 60)

    try:
        # Get database URL from environment
        db_url = os.getenv('DATABASE_URL', 'postgresql://postgres@localhost/sports_betting')
        print(f"Database: {db_url}")
        print()

        # Create all tables
        engine = create_database(db_url)

        print("\nTables created successfully!")
        print("-" * 60)

        # Verify tables exist
        print("\nVerifying tables...")
        session = get_session()

        try:
            # Check each table
            tables_to_check = [
                ('players', Player),
                ('teams', Team),
                ('team_defensive_stats', TeamDefensiveStats),
                ('game_stats', GameStats)
            ]

            for table_name, model in tables_to_check:
                try:
                    count = session.query(model).count()
                    print(f"✓ {table_name}: {count} records")
                except Exception as e:
                    print(f"✗ {table_name}: Error - {e}")

        finally:
            session.close()

        print("\n" + "=" * 60)
        print("Database setup complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError creating tables: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_all_tables()
