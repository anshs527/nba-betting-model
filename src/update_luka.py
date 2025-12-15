#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update script specifically for Luka Dončić
Handles special characters properly
"""

from data_collector import NBADataCollector
import time

def update_luka():
    """Update data for Luka Dončić"""
    collector = NBADataCollector()

    try:
        # Luka's full name with proper Unicode character
        player_name = "Luka Dončić"

        print(f"Updating data for {player_name}...")
        collector.fetch_player_game_stats(player_name, season='2025-26', max_games=30)
        print(f"✓ Successfully updated data for {player_name}")

    except Exception as e:
        print(f"✗ Error updating {player_name}: {e}")

    finally:
        collector.close()

if __name__ == "__main__":
    update_luka()
