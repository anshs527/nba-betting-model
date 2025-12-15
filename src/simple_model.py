"""
Simple baseline model for predicting player performance
Starts with basic moving averages, will expand to Bayesian models
"""

import pandas as pd
import numpy as np
from database import get_session, Player, GameStats, Team, TeamDefensiveStats
from datetime import datetime, timedelta
from sqlalchemy import desc

# Rest adjustment values based on days since last game
REST_ADJUSTMENTS = {
    0: -1.5,   # Back-to-back (B2B)
    1: -0.4,   # 1 day rest
    2: +1.1,   # 2 days rest (optimal)
    3: +0.5,   # 3 days rest
    4: 0.0     # 4+ days rest (normal)
}

class SimplePredictor:
    """
    Baseline predictor using moving averages
    This is our starting point - we'll make it more sophisticated later
    """
    
    def __init__(self, stat_type='points', lookback_games=10):
        """
        Args:
            stat_type: Which stat to predict ('points', 'rebounds', 'assists')
            lookback_games: How many recent games to average
        """
        self.stat_type = stat_type
        self.lookback_games = lookback_games
        self.session = get_session()
    
    def get_player_recent_stats(self, player_name, n_games=None):
        """Get recent game stats for a player"""
        if n_games is None:
            n_games = self.lookback_games
        
        player = self.session.query(Player).filter_by(name=player_name).first()
        
        if not player:
            return None
        
        # Get most recent games
        recent_games = self.session.query(GameStats)\
            .filter_by(player_id=player.id)\
            .order_by(desc(GameStats.game_date))\
            .limit(n_games)\
            .all()
        
        if not recent_games:
            return None
        
        # Convert to DataFrame for easy analysis
        data = []
        for game in recent_games:
            data.append({
                'date': game.game_date,
                'opponent': game.opponent,
                'is_home': game.is_home,
                'days_rest': game.days_rest,
                'is_b2b': game.is_back_to_back,
                'points': game.points,
                'rebounds': game.rebounds,
                'assists': game.assists,
                'minutes': game.minutes
            })

        return pd.DataFrame(data)
    
    def predict_simple_average(self, player_name, decay=0.9):
        """
        Simple arithmetic mean of recent games
        All games are weighted equally

        Args:
            player_name: Name of the player
            decay: (unused, kept for compatibility)

        Returns: (prediction, std_dev, recent_stats_df)
        """
        recent_stats = self.get_player_recent_stats(player_name)

        if recent_stats is None or recent_stats.empty:
            return None, None, None

        # Get the stat we're predicting
        stat_values = recent_stats[self.stat_type].dropna().values

        if len(stat_values) == 0:
            return None, None, None

        # Simple average - all games weighted equally
        prediction = np.mean(stat_values)

        # Standard deviation (unweighted)
        std_dev = np.std(stat_values, ddof=1) if len(stat_values) > 1 else 0.0

        return prediction, std_dev, recent_stats
    
    def predict_weighted_average(self, player_name, decay_factor=0.9):
        """
        Weighted average giving more weight to recent games
        decay_factor: How much to decay older games (0.9 = 10% decay per game back)
        """
        recent_stats = self.get_player_recent_stats(player_name)
        
        if recent_stats is None or recent_stats.empty:
            return None, None, None
        
        stat_values = recent_stats[self.stat_type].dropna().values
        
        if len(stat_values) == 0:
            return None, None, None
        
        # Create weights (most recent game gets weight 1.0, then decay)
        weights = np.array([decay_factor ** i for i in range(len(stat_values))])
        weights = weights / weights.sum()  # Normalize
        
        prediction = np.sum(stat_values * weights)
        
        # Weighted standard deviation
        variance = np.sum(weights * (stat_values - prediction) ** 2)
        std_dev = np.sqrt(variance)
        
        return prediction, std_dev, recent_stats

    def apply_opponent_adjustment(self, base_prediction, opponent_name, league_avg=112.0):
        """
        Adjust prediction based on opponent's defensive rating

        Args:
            base_prediction: The unadjusted prediction
            opponent_name: Name or abbreviation of the opponent team
            league_avg: League average defensive rating (points allowed per 100 possessions)

        Returns:
            Adjusted prediction, or base_prediction if no defensive data available
        """
        if base_prediction is None:
            return None

        # Try to find the opponent team
        team = self.session.query(Team).filter(
            (Team.name.like(f"%{opponent_name}%")) |
            (Team.abbreviation == opponent_name)
        ).first()

        if not team:
            print(f"Warning: Opponent team '{opponent_name}' not found. Using unadjusted prediction.")
            return base_prediction

        # Get defensive stats for this team
        def_stats = self.session.query(TeamDefensiveStats).filter_by(team_id=team.id).first()

        if not def_stats or def_stats.def_rating is None:
            print(f"Warning: No defensive rating for {team.name}. Using unadjusted prediction.")
            return base_prediction

        # Apply adjustment: if opponent allows more points than average, player should score more
        # Formula: if opponent allows MORE points = weaker defense = player scores MORE
        adjustment_factor = def_stats.def_rating / league_avg
        adjusted_prediction = base_prediction * adjustment_factor

        print(f"Opponent: {team.name}")
        print(f"Defensive Rating: {def_stats.def_rating:.1f} pts/game (League avg: {league_avg})")
        print(f"Adjustment Factor: {adjustment_factor:.3f}")
        print(f"Base Prediction: {base_prediction:.2f} → Adjusted: {adjusted_prediction:.2f}")

        return adjusted_prediction

    def apply_rest_adjustment(self, base_prediction, days_rest):
        """
        Adjust prediction based on rest days since last game

        Args:
            base_prediction: The unadjusted prediction
            days_rest: Number of days since last game (0 = back-to-back)

        Returns:
            Adjusted prediction
        """
        if base_prediction is None:
            return None

        if days_rest is None:
            print("Warning: Days rest unknown. Using unadjusted prediction.")
            return base_prediction

        # Cap at 4+ days
        capped_rest = min(days_rest, 4)
        adjustment = REST_ADJUSTMENTS.get(capped_rest, 0.0)
        adjusted_prediction = base_prediction + adjustment

        rest_description = {
            0: "Back-to-back",
            1: "1 day rest",
            2: "2 days rest (optimal)",
            3: "3 days rest",
            4: "4+ days rest"
        }.get(capped_rest, f"{days_rest} days rest")

        print(f"Rest: {rest_description}")
        print(f"Rest Adjustment: {adjustment:+.1f}")
        print(f"Base Prediction: {base_prediction:.2f} → Adjusted: {adjusted_prediction:.2f}")

        return adjusted_prediction

    def predict_with_opponent_adjustment(self, player_name, opponent_name, league_avg=112.0, use_weighted=True, decay=0.9):
        """
        Make a prediction with opponent defensive adjustment

        Args:
            player_name: Name of the player
            opponent_name: Name or abbreviation of the opponent team
            league_avg: League average defensive rating
            use_weighted: If True, use weighted average; otherwise simple average
            decay: Decay factor for weighted average

        Returns:
            (adjusted_prediction, std_dev, recent_stats)
        """
        # Get base prediction
        if use_weighted:
            base_pred, std_dev, recent_stats = self.predict_weighted_average(player_name, decay_factor=decay)
        else:
            base_pred, std_dev, recent_stats = self.predict_simple_average(player_name, decay=decay)

        if base_pred is None:
            return None, None, None

        # Apply opponent adjustment
        adjusted_pred = self.apply_opponent_adjustment(base_pred, opponent_name, league_avg)

        return adjusted_pred, std_dev, recent_stats

    def evaluate_against_line(self, prediction, std_dev, line):
        """
        Evaluate if a bet is worth taking
        
        Args:
            prediction: Our predicted value
            std_dev: Standard deviation of prediction
            line: PrizePicks line (over/under value)
        
        Returns:
            dict with recommendation
        """
        if prediction is None or std_dev is None:
            return None
        
        # Calculate how many standard deviations away the line is
        z_score = (prediction - line) / std_dev if std_dev > 0 else 0
        
        # Simple probability estimate (assuming normal distribution)
        from scipy.stats import norm
        prob_over = 1 - norm.cdf(line, prediction, std_dev)
        prob_under = norm.cdf(line, prediction, std_dev)
        
        # Expected value (assuming -110 odds, need to win 52.4% to break even)
        ev_over = prob_over * 0.909 - prob_under * 1.0  # Win $0.909 per $1, lose $1
        ev_under = prob_under * 0.909 - prob_over * 1.0
        
        return {
            'prediction': prediction,
            'line': line,
            'std_dev': std_dev,
            'z_score': z_score,
            'prob_over': prob_over,
            'prob_under': prob_under,
            'ev_over': ev_over,
            'ev_under': ev_under,
            'recommendation': 'OVER' if ev_over > 0 else ('UNDER' if ev_under > 0 else 'SKIP'),
            'confidence': abs(z_score)
        }
    
    def analyze_player(self, player_name, line=None, opponent=None, days_rest=None, league_avg=112.0):
        """
        Complete analysis for a player

        Args:
            player_name: Name of the player
            line: PrizePicks line (optional)
            opponent: Opponent team name for defensive adjustment (optional)
            days_rest: Days of rest before the game (optional)
            league_avg: League average defensive rating
        """
        print(f"\n{'='*60}")
        print(f"Analysis for {player_name} - {self.stat_type.upper()}")
        print(f"{'='*60}")

        # Get predictions
        simple_pred, simple_std, recent_stats = self.predict_simple_average(player_name)
        weighted_pred, weighted_std, _ = self.predict_weighted_average(player_name)

        if simple_pred is None:
            print(f"No data available for {player_name}")
            return

        print(f"\nRecent {len(recent_stats)} games:")
        print(recent_stats[['date', 'opponent', self.stat_type]].to_string(index=False))

        print(f"\nSimple Average Prediction: {simple_pred:.2f} ± {simple_std:.2f}")
        print(f"Weighted Average Prediction: {weighted_pred:.2f} ± {weighted_std:.2f}")

        # Apply adjustments
        final_pred = weighted_pred

        # Apply opponent adjustment if opponent is provided
        if opponent:
            print(f"\n--- Opponent Adjustment ---")
            final_pred = self.apply_opponent_adjustment(final_pred, opponent, league_avg)
            print(f"---------------------------")

        # Apply rest adjustment if days_rest is provided
        if days_rest is not None:
            print(f"\n--- Rest Adjustment ---")
            final_pred = self.apply_rest_adjustment(final_pred, days_rest)
            print(f"-----------------------")

        if line is not None:
            print(f"\nPrizePicks Line: {line}")
            eval_result = self.evaluate_against_line(final_pred, weighted_std, line)

            print(f"\nBetting Analysis:")
            print(f"  Probability OVER: {eval_result['prob_over']*100:.1f}%")
            print(f"  Probability UNDER: {eval_result['prob_under']*100:.1f}%")
            print(f"  Expected Value (OVER): {eval_result['ev_over']:.3f}")
            print(f"  Expected Value (UNDER): {eval_result['ev_under']:.3f}")
            print(f"  RECOMMENDATION: {eval_result['recommendation']}")
            print(f"  Confidence: {eval_result['confidence']:.2f} standard deviations")

        return eval_result if line else None
    
    def close(self):
        self.session.close()

if __name__ == "__main__":
    # Need scipy for probability calculations
    try:
        from scipy.stats import norm
    except ImportError:
        print("Installing scipy for probability calculations...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'scipy'])
        from scipy.stats import norm
    
    # Example usage
    predictor = SimplePredictor(stat_type='points', lookback_games=10)
    
    # Analyze a player with a hypothetical PrizePicks line
    # You can change these values
    predictor.analyze_player('LeBron James', line=24.5)
    predictor.analyze_player('Stephen Curry', line=26.5)
    
    predictor.close()
