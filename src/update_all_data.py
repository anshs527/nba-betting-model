"""
Script to update game stats for all players in the database
Run this periodically to keep data fresh
"""

from data_collector import NBADataCollector
from database import get_session, Player
import time

def update_all_players(season='2025-26', max_games=30):
    """
    Update game stats for all players in the database

    Args:
        season: NBA season (e.g., '2025-26')
        max_games: Maximum number of recent games to fetch per player
    """
    session = get_session()
    collector = NBADataCollector()

    try:
        # Get all players from database
        all_players = session.query(Player).all()
        total_players = len(all_players)

        print(f"Updating data for {total_players} players...")
        print(f"Season: {season}, Max games per player: {max_games}")
        print("-" * 60)

        successful = 0
        failed = 0

        for i, player in enumerate(all_players, 1):
            try:
                print(f"[{i}/{total_players}] Updating {player.name}...", end=" ")
                collector.fetch_player_game_stats(player.name, season=season, max_games=max_games)
                print("✓")
                successful += 1
                time.sleep(0.7)  # Respect API rate limits
            except Exception as e:
                print(f"✗ Error: {e}")
                failed += 1
                time.sleep(1)  # Wait a bit longer after errors

        print("-" * 60)
        print(f"\nUpdate complete!")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")

    finally:
        session.close()
        collector.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Update NBA player game stats')
    parser.add_argument('--season', type=str, default='2025-26',
                        help='NBA season (e.g., 2025-26)')
    parser.add_argument('--max-games', type=int, default=30,
                        help='Maximum number of recent games to fetch per player')
    parser.add_argument('--players', type=str, nargs='+',
                        help='Specific player names to update (optional)')

    args = parser.parse_args()

    if args.players:
        # Update only specific players
        collector = NBADataCollector()
        print(f"Updating {len(args.players)} specific players...")
        for player_name in args.players:
            try:
                print(f"Updating {player_name}...", end=" ")
                collector.fetch_player_game_stats(player_name, season=args.season, max_games=args.max_games)
                print("✓")
                time.sleep(0.7)
            except Exception as e:
                print(f"✗ Error: {e}")
        collector.close()
    else:
        # Update all players
        update_all_players(season=args.season, max_games=args.max_games)
