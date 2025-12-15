"""
Quick script to view player data from the database
"""

from database import get_session, Player, GameStats
from sqlalchemy import desc
import pandas as pd

def view_player_games(player_name, limit=20):
    """View recent games for a player"""
    session = get_session()

    try:
        # Find player
        player = session.query(Player).filter_by(name=player_name).first()

        if not player:
            print(f"Player '{player_name}' not found in database.")
            return

        # Get recent games
        games = session.query(GameStats)\
            .filter_by(player_id=player.id)\
            .order_by(desc(GameStats.game_date))\
            .limit(limit)\
            .all()

        if not games:
            print(f"No games found for {player_name}")
            return

        # Convert to DataFrame for nice display
        data = []
        for game in games:
            data.append({
                'Date': game.game_date,
                'Opponent': game.opponent,
                'Home/Away': 'Home' if game.is_home else 'Away',
                'Days Rest': game.days_rest,
                'B2B': 'Yes' if game.is_back_to_back else 'No',
                'Points': game.points,
                'Rebounds': game.rebounds,
                'Assists': game.assists,
                'Minutes': game.minutes
            })

        df = pd.DataFrame(data)

        print(f"\n{'='*80}")
        print(f"Recent Games for {player_name} ({len(games)} games)")
        print(f"{'='*80}")
        print(df.to_string(index=False))
        print(f"{'='*80}\n")

        return df

    finally:
        session.close()

def list_all_players():
    """List all players in database"""
    session = get_session()

    try:
        players = session.query(Player).order_by(Player.name).all()

        print(f"\nTotal players in database: {len(players)}\n")

        for i, player in enumerate(players, 1):
            # Count games for each player
            game_count = session.query(GameStats).filter_by(player_id=player.id).count()
            print(f"{i:3d}. {player.name:30s} - {game_count} games")

    finally:
        session.close()

def view_player_stats_summary(player_name):
    """View statistical summary for a player"""
    session = get_session()

    try:
        player = session.query(Player).filter_by(name=player_name).first()

        if not player:
            print(f"Player '{player_name}' not found in database.")
            return

        games = session.query(GameStats)\
            .filter_by(player_id=player.id)\
            .order_by(desc(GameStats.game_date))\
            .all()

        if not games:
            print(f"No games found for {player_name}")
            return

        # Convert to DataFrame for statistics
        data = {
            'points': [g.points for g in games if g.points is not None],
            'rebounds': [g.rebounds for g in games if g.rebounds is not None],
            'assists': [g.assists for g in games if g.assists is not None],
            'minutes': [g.minutes for g in games if g.minutes is not None],
        }

        df = pd.DataFrame(data)

        print(f"\n{'='*60}")
        print(f"Statistical Summary for {player_name}")
        print(f"{'='*60}")
        print(f"Total games: {len(games)}")
        print(f"\nMost recent game: {games[0].game_date}")
        print(f"Oldest game: {games[-1].game_date}")
        print(f"\n{df.describe()}")
        print(f"{'='*60}\n")

    finally:
        session.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Player name provided as argument
        player_name = ' '.join(sys.argv[1:])
        view_player_games(player_name)
        view_player_stats_summary(player_name)
    else:
        # Interactive mode
        print("\nNBA Player Data Viewer")
        print("="*60)
        print("1. View specific player's games")
        print("2. List all players")
        print("3. Exit")

        while True:
            choice = input("\nEnter choice (1-3): ").strip()

            if choice == '1':
                player_name = input("Enter player name: ").strip()
                view_player_games(player_name)
                view_player_stats_summary(player_name)
            elif choice == '2':
                list_all_players()
            elif choice == '3':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
