"""
Migration script to add days_rest and is_back_to_back columns to game_stats table
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime

load_dotenv()

def add_rest_columns():
    """Add days_rest and is_back_to_back columns to game_stats table"""

    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/sports_betting')
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Check if columns already exist
        check_query = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='game_stats'
            AND column_name IN ('days_rest', 'is_back_to_back')
        """)

        existing_columns = [row[0] for row in conn.execute(check_query)]

        # Add days_rest column if it doesn't exist
        if 'days_rest' not in existing_columns:
            print("Adding days_rest column...")
            conn.execute(text("""
                ALTER TABLE game_stats
                ADD COLUMN days_rest INTEGER
            """))
            conn.commit()
            print("✓ days_rest column added")
        else:
            print("days_rest column already exists")

        # Add is_back_to_back column if it doesn't exist
        if 'is_back_to_back' not in existing_columns:
            print("Adding is_back_to_back column...")
            conn.execute(text("""
                ALTER TABLE game_stats
                ADD COLUMN is_back_to_back BOOLEAN
            """))
            conn.commit()
            print("✓ is_back_to_back column added")
        else:
            print("is_back_to_back column already exists")

        # Now calculate and populate the values for existing records
        print("\nCalculating rest days for existing game records...")

        # Get all players
        players_query = text("SELECT DISTINCT player_id FROM game_stats ORDER BY player_id")
        players = [row[0] for row in conn.execute(players_query)]

        for player_id in players:
            # Get all games for this player, ordered by date
            games_query = text("""
                SELECT id, game_date
                FROM game_stats
                WHERE player_id = :player_id
                ORDER BY game_date
            """)

            games = list(conn.execute(games_query, {"player_id": player_id}))

            for i, (game_id, game_date) in enumerate(games):
                if i == 0:
                    # First game - no previous game to compare
                    days_rest = None
                    is_b2b = False
                else:
                    # Calculate days since last game
                    prev_date = games[i-1][1]
                    days_rest = (game_date - prev_date).days - 1  # Subtract 1 to get rest days
                    is_b2b = (days_rest == 0)

                # Update the record
                update_query = text("""
                    UPDATE game_stats
                    SET days_rest = :days_rest, is_back_to_back = :is_b2b
                    WHERE id = :game_id
                """)

                conn.execute(update_query, {
                    "days_rest": days_rest,
                    "is_b2b": is_b2b,
                    "game_id": game_id
                })

            conn.commit()

        print(f"✓ Updated rest information for {len(players)} players")
        print("\nMigration completed successfully!")

if __name__ == "__main__":
    add_rest_columns()
