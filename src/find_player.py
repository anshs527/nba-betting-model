"""
Helper script to find player names in the database
Useful for players with special characters
"""

from database import get_session, Player

def find_player(search_term):
    """Find players matching a search term"""
    session = get_session()

    try:
        # Search for players whose name contains the search term (case-insensitive)
        players = session.query(Player).filter(
            Player.name.ilike(f'%{search_term}%')
        ).all()

        if not players:
            print(f"No players found matching '{search_term}'")
            return None

        print(f"\nFound {len(players)} player(s):\n")
        for i, player in enumerate(players, 1):
            print(f"{i}. {player.name}")

        return [p.name for p in players]

    finally:
        session.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        search_term = ' '.join(sys.argv[1:])
        find_player(search_term)
    else:
        print("Usage: python find_player.py <search term>")
        print("Example: python find_player.py Luka")
