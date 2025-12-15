"""
Add ALL active NBA players to the database
This will take a while due to API rate limiting (~10-15 minutes for 450+ players)
"""

from data_collector import NBADataCollector
from nba_api.stats.static import players
import time
from datetime import datetime

def add_all_nba_players(season='2025-26', delay=1.0):
    """
    Fetch game stats for all active NBA players
    
    Args:
        season: NBA season (e.g., '2025-26')
        delay: Seconds to wait between API calls (default 1.0)
    """
    print("=" * 60)
    print("ADDING ALL NBA PLAYERS TO DATABASE")
    print("=" * 60)
    
    # Get all active players
    all_players = players.get_active_players()
    total_players = len(all_players)
    
    print(f"\nFound {total_players} active NBA players")
    print(f"Estimated time: ~{total_players * delay / 60:.1f} minutes")
    print("\nStarting data collection...\n")
    
    collector = NBADataCollector()
    
    # Track stats
    successful = 0
    failed = 0
    skipped = 0
    start_time = datetime.now()
    
    for i, player in enumerate(all_players, 1):
        player_name = player['full_name']
        
        # Progress indicator
        print(f"[{i}/{total_players}] {player_name}...", end=" ")
        
        try:
            # Fetch player stats
            collector.fetch_player_game_stats(
                player_name,
                season=season
            )
            successful += 1
            print("✓")
            
        except Exception as e:
            # Some players might not have games this season (injured, G-League, etc.)
            if "No games found" in str(e) or "empty" in str(e).lower():
                skipped += 1
                print("⊝ (no games)")
            else:
                failed += 1
                print(f"✗ ({str(e)[:50]})")
        
        # Respect API rate limits
        time.sleep(delay)
        
        # Progress summary every 50 players
        if i % 50 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            remaining = (total_players - i) * delay / 60
            print(f"\n--- Progress: {i}/{total_players} ({i/total_players*100:.1f}%) ---")
            print(f"    Successful: {successful} | Skipped: {skipped} | Failed: {failed}")
            print(f"    Time elapsed: {elapsed:.1f} min | Est. remaining: {remaining:.1f} min\n")
    
    collector.close()
    
    # Final summary
    total_time = (datetime.now() - start_time).total_seconds() / 60
    print("\n" + "=" * 60)
    print("COMPLETED!")
    print("=" * 60)
    print(f"Total players processed: {total_players}")
    print(f"✓ Successful: {successful}")
    print(f"⊝ Skipped (no games): {skipped}")
    print(f"✗ Failed: {failed}")
    print(f"⏱ Total time: {total_time:.1f} minutes")
    print("=" * 60)

if __name__ == "__main__":
    # Configuration
    SEASON = '2025-26'
    DELAY = 1.0  # Wait 1 second between requests (increase if you get rate limited)
    
    # Confirm before starting
    print("\n⚠️  WARNING: This will fetch data for ALL active NBA players!")
    print(f"   Season: {SEASON}")
    print(f"   Delay between requests: {DELAY} seconds")
    print(f"   Estimated time: ~10-15 minutes")
    
    response = input("\nProceed? (yes/no): ").strip().lower()
    
    if response == 'yes':
        add_all_nba_players(season=SEASON, delay=DELAY)
    else:
        print("Cancelled.")
