"""
Multi-pick parlay analyzer for sports betting
Analyzes combinations of picks and calculates optimal bet sizing
"""

from dataclasses import dataclass
from typing import List, Optional
from scipy.stats import norm
from simple_model import SimplePredictor
import numpy as np


@dataclass
class Pick:
    """Represents a single pick in a parlay"""
    player_name: str
    stat_type: str  # 'points', 'rebounds', 'assists', etc.
    line: float  # The over/under line
    direction: str  # 'OVER' or 'UNDER'
    prediction: Optional[float] = None  # Model's prediction
    probability: Optional[float] = None  # Probability of winning


@dataclass
class Parlay:
    """Represents a parlay bet with multiple picks"""
    picks: List[Pick]
    payout_multiplier: float  # e.g., 3.0 for 3x payout on 2-pick parlay
    stake: float = 1.0  # Amount to bet
    parlay_probability: Optional[float] = None  # Probability all picks hit
    expected_value: Optional[float] = None  # Expected value of the bet
    roi: Optional[float] = None  # Return on investment percentage
    recommendation: Optional[str] = None  # 'BET', 'SKIP', etc.


class MultiPickAnalyzer:
    """
    Analyzes multi-pick parlays using a prediction model
    Calculates probabilities, expected value, and optimal bet sizing
    """

    def __init__(self, prediction_model: SimplePredictor):
        """
        Args:
            prediction_model: A SimplePredictor instance for evaluating picks
        """
        self.model = prediction_model

    def evaluate_pick(self, pick: Pick, opponent: Optional[str] = None,
                     days_rest: Optional[int] = None) -> Pick:
        """
        Evaluate a single pick using the prediction model

        Args:
            pick: Pick object to evaluate
            opponent: Opponent team name for defensive adjustment
            days_rest: Days of rest before the game

        Returns:
            Updated Pick object with prediction and probability filled in
        """
        # Create a predictor for this stat type if needed
        if self.model.stat_type != pick.stat_type:
            # Create temporary predictor with correct stat type
            temp_predictor = SimplePredictor(
                stat_type=pick.stat_type,
                lookback_games=self.model.lookback_games
            )
            predictor = temp_predictor
        else:
            predictor = self.model

        # Get base prediction using weighted average
        prediction, std_dev, _ = predictor.predict_weighted_average(pick.player_name)

        if prediction is None or std_dev is None:
            print(f"Warning: No data available for {pick.player_name} - {pick.stat_type}")
            return pick

        # Apply opponent adjustment if provided
        if opponent:
            prediction = predictor.apply_opponent_adjustment(prediction, opponent)

        # Apply rest adjustment if provided
        if days_rest is not None:
            prediction = predictor.apply_rest_adjustment(prediction, days_rest)

        # Calculate probability based on direction
        if pick.direction.upper() == 'OVER':
            probability = 1 - norm.cdf(pick.line, prediction, std_dev)
        elif pick.direction.upper() == 'UNDER':
            probability = norm.cdf(pick.line, prediction, std_dev)
        else:
            raise ValueError(f"Invalid direction: {pick.direction}. Must be 'OVER' or 'UNDER'")

        # Update pick with prediction and probability
        pick.prediction = prediction
        pick.probability = probability

        # Close temp predictor session if we created one
        if predictor != self.model:
            predictor.close()

        return pick

    def analyze_parlay(self, parlay: Parlay, opponent_map: Optional[dict] = None,
                      rest_map: Optional[dict] = None) -> Parlay:
        """
        Analyze a parlay bet with multiple picks

        Args:
            parlay: Parlay object with picks to analyze
            opponent_map: Dict mapping player_name -> opponent_team
            rest_map: Dict mapping player_name -> days_rest

        Returns:
            Updated Parlay object with analysis results
        """
        print(f"\n{'='*70}")
        print(f"PARLAY ANALYSIS - {len(parlay.picks)} picks")
        print(f"{'='*70}")

        opponent_map = opponent_map or {}
        rest_map = rest_map or {}

        # Evaluate each pick
        evaluated_picks = []
        for i, pick in enumerate(parlay.picks, 1):
            print(f"\n--- Pick {i}: {pick.player_name} {pick.stat_type.upper()} {pick.direction} {pick.line} ---")

            opponent = opponent_map.get(pick.player_name)
            days_rest = rest_map.get(pick.player_name)

            evaluated_pick = self.evaluate_pick(pick, opponent, days_rest)
            evaluated_picks.append(evaluated_pick)

            if evaluated_pick.prediction is not None:
                print(f"Prediction: {evaluated_pick.prediction:.2f}")
                print(f"Probability: {evaluated_pick.probability*100:.1f}%")
            else:
                print("Could not evaluate this pick (insufficient data)")

        # Update parlay with evaluated picks
        parlay.picks = evaluated_picks

        # Calculate parlay probability (all picks must hit)
        pick_probabilities = [p.probability for p in parlay.picks if p.probability is not None]

        if len(pick_probabilities) != len(parlay.picks):
            print("\nWarning: Could not evaluate all picks. Cannot calculate parlay probability.")
            parlay.recommendation = "SKIP - Insufficient data"
            return parlay

        parlay.parlay_probability = np.prod(pick_probabilities)

        # Calculate expected value
        # EV = (probability × payout) - (1 - probability) × stake
        potential_payout = parlay.stake * parlay.payout_multiplier
        parlay.expected_value = (parlay.parlay_probability * potential_payout) - \
                               ((1 - parlay.parlay_probability) * parlay.stake)

        # Calculate ROI
        parlay.roi = (parlay.expected_value / parlay.stake) * 100

        # Apply Kelly Criterion for bet sizing (using quarter Kelly for safety)
        # Kelly fraction = (probability × payout - 1) / (payout - 1)
        if parlay.payout_multiplier > 1:
            kelly_fraction = (parlay.parlay_probability * parlay.payout_multiplier - 1) / \
                           (parlay.payout_multiplier - 1)
            quarter_kelly = kelly_fraction * 0.25
        else:
            quarter_kelly = 0

        # Determine recommendation
        if parlay.expected_value > 0 and parlay.parlay_probability > 0.05:  # Min 5% chance
            parlay.recommendation = f"BET (Quarter Kelly: {quarter_kelly*100:.1f}% of bankroll)"
        elif parlay.expected_value > 0:
            parlay.recommendation = "SKIP - Positive EV but probability too low"
        else:
            parlay.recommendation = "SKIP - Negative expected value"

        # Print summary
        print(f"\n{'='*70}")
        print(f"PARLAY SUMMARY")
        print(f"{'='*70}")
        print(f"Number of picks: {len(parlay.picks)}")
        print(f"Individual probabilities: {[f'{p*100:.1f}%' for p in pick_probabilities]}")
        print(f"Parlay probability: {parlay.parlay_probability*100:.1f}%")
        print(f"Payout multiplier: {parlay.payout_multiplier}x")
        print(f"Stake: ${parlay.stake:.2f}")
        print(f"Potential payout: ${potential_payout:.2f}")
        print(f"Expected value: ${parlay.expected_value:.2f}")
        print(f"ROI: {parlay.roi:.1f}%")
        print(f"Quarter Kelly bet size: {quarter_kelly*100:.1f}% of bankroll")
        print(f"\nRECOMMENDATION: {parlay.recommendation}")
        print(f"{'='*70}\n")

        return parlay

    def compare_parlays(self, parlays: List[Parlay], opponent_map: Optional[dict] = None,
                       rest_map: Optional[dict] = None) -> List[Parlay]:
        """
        Compare multiple parlay options and rank them

        Args:
            parlays: List of Parlay objects to compare
            opponent_map: Dict mapping player_name -> opponent_team
            rest_map: Dict mapping player_name -> days_rest

        Returns:
            List of analyzed parlays sorted by expected value
        """
        analyzed_parlays = []

        for i, parlay in enumerate(parlays, 1):
            print(f"\n{'#'*70}")
            print(f"OPTION {i}")
            print(f"{'#'*70}")
            analyzed = self.analyze_parlay(parlay, opponent_map, rest_map)
            analyzed_parlays.append(analyzed)

        # Sort by expected value (descending)
        analyzed_parlays.sort(key=lambda p: p.expected_value if p.expected_value else -float('inf'),
                            reverse=True)

        # Print comparison
        print(f"\n{'='*70}")
        print(f"PARLAY COMPARISON (Ranked by Expected Value)")
        print(f"{'='*70}")

        for i, parlay in enumerate(analyzed_parlays, 1):
            print(f"\nRank {i}:")
            print(f"  Picks: {len(parlay.picks)}")
            print(f"  Parlay Probability: {parlay.parlay_probability*100:.1f}%" if parlay.parlay_probability else "  N/A")
            print(f"  Expected Value: ${parlay.expected_value:.2f}" if parlay.expected_value else "  N/A")
            print(f"  ROI: {parlay.roi:.1f}%" if parlay.roi else "  N/A")
            print(f"  Recommendation: {parlay.recommendation}")

        return analyzed_parlays


if __name__ == "__main__":
    # Example usage
    from simple_model import SimplePredictor

    # Create predictor
    predictor = SimplePredictor(stat_type='points', lookback_games=10)

    # Create analyzer
    analyzer = MultiPickAnalyzer(predictor)

    # Example: 2-pick parlay
    picks = [
        Pick(
            player_name='LeBron James',
            stat_type='points',
            line=24.5,
            direction='OVER'
        ),
        Pick(
            player_name='Stephen Curry',
            stat_type='points',
            line=26.5,
            direction='OVER'
        )
    ]

    parlay = Parlay(
        picks=picks,
        payout_multiplier=3.0,  # 3x payout for 2-pick parlay
        stake=10.0
    )

    # Analyze with opponent and rest adjustments
    opponent_map = {
        'LeBron James': 'GSW',
        'Stephen Curry': 'LAL'
    }
    rest_map = {
        'LeBron James': 1,  # 1 day rest
        'Stephen Curry': 2   # 2 days rest (optimal)
    }

    result = analyzer.analyze_parlay(parlay, opponent_map, rest_map)

    predictor.close()
