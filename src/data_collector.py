"""
Fetch NBA player statistics using the nba_api library
"""

from nba_api.stats.endpoints import playergamelog, commonplayerinfo, leaguedashteamstats
from nba_api.stats.static import players, teams
from database import get_session, Player, GameStats, Team, TeamDefensiveStats
from datetime import datetime
import time
import pandas as pd

class NBADataCollector:
    """Collect NBA player and game data"""
    
    def __init__(self):
        self.session = get_session()
        
    def fetch_all_players(self):
        """Fetch all active NBA players and store in database"""
        print("Fetching all NBA players...")
        all_players = players.get_active_players()
        
        for player_data in all_players:
            # Check if player already exists
            existing = self.session.query(Player).filter_by(nba_id=player_data['id']).first()
            
            if not existing:
                player = Player(
                    nba_id=player_data['id'],
                    name=player_data['full_name']
                )
                self.session.add(player)
        
        self.session.commit()
        print(f"Added {len(all_players)} players to database")
    
    def fetch_all_teams(self):
        """Fetch all NBA teams and store in database"""
        print("Fetching all NBA teams...")
        all_teams = teams.get_teams()
        
        for team_data in all_teams:
            existing = self.session.query(Team).filter_by(nba_id=team_data['id']).first()
            
            if not existing:
                team = Team(
                    nba_id=team_data['id'],
                    name=team_data['full_name'],
                    abbreviation=team_data['abbreviation']
                )
                self.session.add(team)
        
        self.session.commit()
        print(f"Added {len(all_teams)} teams to database")

    def fetch_team_defensive_stats(self, season='2025-26'):
        """
        Fetch defensive statistics for all NBA teams

        Args:
            season: NBA season (e.g., '2025-26')
        """
        print(f"Fetching team defensive stats for {season}...")

        try:
            # Fetch opponent stats which gives us defensive metrics
            team_stats = leaguedashteamstats.LeagueDashTeamStats(
                season=season,
                measure_type_detailed_defense='Opponent',
                per_mode_detailed='PerGame'
            )

            # Small delay to respect API rate limits
            time.sleep(0.6)

            stats_df = team_stats.get_data_frames()[0]

            print(f"Found defensive stats for {len(stats_df)} teams")

            # Process each team
            for _, team_row in stats_df.iterrows():
                team_name = team_row['TEAM_NAME']

                # Find team in database
                team = self.session.query(Team).filter_by(name=team_name).first()

                if not team:
                    print(f"Warning: Team {team_name} not found in database. Skipping...")
                    continue

                # Check if defensive stats already exist
                existing = self.session.query(TeamDefensiveStats).filter_by(
                    team_id=team.id
                ).first()

                # Use OPP_PTS (opponent points per game) as defensive rating
                # Lower is better (team allows fewer points)
                def_rating = float(team_row['OPP_PTS']) if pd.notna(team_row['OPP_PTS']) else None

                print(f"  {team.abbreviation}: Def Rating (OPP_PTS) = {def_rating:.1f}" if def_rating else f"  {team.abbreviation}: No data")

                if existing:
                    # Update existing record
                    existing.def_rating = def_rating
                    existing.last_updated = datetime.utcnow()
                else:
                    # Create new record
                    defensive_stat = TeamDefensiveStats(
                        team_id=team.id,
                        team_name=team_name,
                        def_rating=def_rating,
                        last_updated=datetime.utcnow()
                    )
                    self.session.add(defensive_stat)

            self.session.commit()
            print("Successfully stored team defensive stats")

        except Exception as e:
            print(f"Error fetching team defensive stats: {e}")
            import traceback
            traceback.print_exc()
            self.session.rollback()

    def fetch_player_game_stats(self, player_name, season='2025-26', max_games=None):
        """
        Fetch game-by-game stats for a specific player

        Args:
            player_name: Name of the player (e.g., 'LeBron James')
            season: NBA season (e.g., '2025-26')
            max_games: Maximum number of games to fetch (None = all)
        """
        print(f"Fetching stats for {player_name}...")
        
        # Find player in database
        player = self.session.query(Player).filter_by(name=player_name).first()
        
        if not player:
            print(f"Player {player_name} not found in database. Run fetch_all_players() first.")
            return
        
        try:
            # Fetch game log from NBA API
            game_log = playergamelog.PlayerGameLog(
                player_id=player.nba_id,
                season=season
            )
            
            # Small delay to respect API rate limits
            time.sleep(0.6)
            
            games_df = game_log.get_data_frames()[0]
            
            if max_games:
                games_df = games_df.head(max_games)
            
            print(f"Found {len(games_df)} games for {player_name}")

            # Sort by date (oldest first) to calculate rest days correctly
            games_df = games_df.sort_values('GAME_DATE', ascending=True)

            # Store each game in database
            prev_game_date = None
            for idx, game in games_df.iterrows():
                # Check if this game already exists
                game_date = pd.to_datetime(game['GAME_DATE'])
                existing = self.session.query(GameStats).filter_by(
                    player_id=player.id,
                    game_date=game_date
                ).first()

                # Calculate days of rest (days since previous game)
                if prev_game_date is not None:
                    days_rest = (game_date - prev_game_date).days - 1
                    is_back_to_back = days_rest == 0
                else:
                    # First game chronologically - no previous game to compare
                    days_rest = None
                    is_back_to_back = False

                if existing:
                    # Update the existing record with correct rest information
                    existing.days_rest = days_rest
                    existing.is_back_to_back = is_back_to_back
                    prev_game_date = game_date
                    continue

                # Determine if home game
                matchup = game['MATCHUP']
                is_home = 'vs.' in matchup
                opponent = matchup.split('vs.' if is_home else '@')[1].strip()

                game_stat = GameStats(
                    player_id=player.id,
                    game_date=game_date,
                    opponent=opponent,
                    is_home=is_home,
                    days_rest=days_rest,
                    is_back_to_back=is_back_to_back,
                    points=float(game['PTS']) if pd.notna(game['PTS']) else None,
                    rebounds=float(game['REB']) if pd.notna(game['REB']) else None,
                    assists=float(game['AST']) if pd.notna(game['AST']) else None,
                    minutes=float(game['MIN']) if pd.notna(game['MIN']) else None,
                    field_goals_made=int(game['FGM']) if pd.notna(game['FGM']) else None,
                    field_goals_attempted=int(game['FGA']) if pd.notna(game['FGA']) else None,
                    three_pointers_made=int(game['FG3M']) if pd.notna(game['FG3M']) else None,
                    three_pointers_attempted=int(game['FG3A']) if pd.notna(game['FG3A']) else None,
                    free_throws_made=int(game['FTM']) if pd.notna(game['FTM']) else None,
                    free_throws_attempted=int(game['FTA']) if pd.notna(game['FTA']) else None,
                    steals=float(game['STL']) if pd.notna(game['STL']) else None,
                    blocks=float(game['BLK']) if pd.notna(game['BLK']) else None,
                    turnovers=float(game['TOV']) if pd.notna(game['TOV']) else None
                )
                self.session.add(game_stat)

                prev_game_date = game_date
            
            self.session.commit()
            print(f"Successfully stored stats for {player_name}")
            
        except Exception as e:
            print(f"Error fetching stats for {player_name}: {e}")
            self.session.rollback()
    
    def fetch_multiple_players(self, player_names, season='2025-26'):
        """Fetch stats for multiple players"""
        for name in player_names:
            self.fetch_player_game_stats(name, season)
            time.sleep(1)  # Respect API rate limits
    
    def close(self):
        """Close database session"""
        self.session.close()

if __name__ == "__main__":
    collector = NBADataCollector()
    
    # First, populate players and teams
    collector.fetch_all_players()
    collector.fetch_all_teams()
    
    # Example: Fetch stats for some popular players
    # You can modify this list
    example_players = [
        'LeBron James',
        'Stephen Curry',
        'Giannis Antetokounmpo',
        'Kevin Durant',
        'Luka Doncic'
    ]
    
    print("\nFetching game stats for example players...")
    collector.fetch_multiple_players(example_players)
    
    collector.close()
    print("\nData collection complete!")
