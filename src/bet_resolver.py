"""
Bet Resolution Logic
Handles automatic and manual resolution of bets
"""

from database import get_session, SingleBet, ParlayBet, Player, GameStats
from paper_trading import PaperTradingManager
from datetime import datetime, timedelta

class BetResolver:
    """Handles bet resolution using GameStats data"""

    def __init__(self):
        self.session = get_session()
        self.manager = PaperTradingManager()

    def close(self):
        """Close database sessions"""
        self.session.close()
        self.manager.close()

    # ==================== AUTOMATIC RESOLUTION ====================

    def check_resolvable_bets(self):
        """
        Find bets that can be auto-resolved

        Returns: List of (bet_id, bet_type, player_name, game_date)
        """
        resolvable = []

        # Check single bets
        pending_singles = self.session.query(SingleBet).filter_by(
            status='pending'
        ).all()

        for bet in pending_singles:
            game_stats = self._find_matching_game_stats(bet)
            if game_stats:
                resolvable.append((bet.id, 'single', bet.player_name, game_stats.game_date))

        # Check parlay bets
        pending_parlays = self.session.query(ParlayBet).filter_by(
            status='pending'
        ).all()

        for parlay in pending_parlays:
            # Check if ALL legs can be resolved
            all_resolvable = True
            for leg in parlay.legs:
                game_stats = self._find_matching_game_stats_for_leg(leg)
                if not game_stats:
                    all_resolvable = False
                    break

            if all_resolvable:
                parlay_date = parlay.legs[0].game_date if parlay.legs else None
                resolvable.append((parlay.id, 'parlay', f"{parlay.num_picks}-leg parlay", parlay_date))

        return resolvable

    def auto_resolve_single_bet(self, bet_id):
        """
        Automatically resolve using GameStats data

        Returns: (success, profit_loss or error_message)
        """
        try:
            bet = self.session.query(SingleBet).get(bet_id)

            if not bet or bet.status != 'pending':
                return False, "Bet not found or already resolved"

            # Find matching game
            game_stats = self._find_matching_game_stats(bet)

            if not game_stats:
                return False, "No matching game found"

            # Check if player DNP (Did Not Play)
            if game_stats.minutes == 0 or game_stats.minutes is None:
                # Void the bet
                self.manager.void_bet(bet.id, bet_type='single')
                return True, f"Bet voided - {bet.player_name} DNP"

            # Extract actual stat value
            actual_result = getattr(game_stats, bet.stat_type, None)

            if actual_result is None:
                return False, f"Stat type '{bet.stat_type}' not found in game data"

            # Resolve the bet
            profit_loss = self.manager.resolve_single_bet(bet.id, actual_result)

            if profit_loss is not None:
                return True, profit_loss
            else:
                return False, "Failed to resolve bet"

        except Exception as e:
            return False, str(e)

    def auto_resolve_parlay_bet(self, parlay_id):
        """
        Auto-resolve all legs of a parlay

        Returns: (success, profit_loss or error_message)
        """
        try:
            parlay = self.session.query(ParlayBet).get(parlay_id)

            if not parlay or parlay.status != 'pending':
                return False, "Parlay not found or already resolved"

            # Collect results for all legs
            leg_results = {}

            for leg in parlay.legs:
                game_stats = self._find_matching_game_stats_for_leg(leg)

                if not game_stats:
                    return False, f"No matching game for {leg.player_name}"

                # Check DNP
                if game_stats.minutes == 0 or game_stats.minutes is None:
                    # Void entire parlay
                    self.manager.void_bet(parlay.id, bet_type='parlay')
                    return True, f"Parlay voided - {leg.player_name} DNP"

                # Extract actual result
                actual_result = getattr(game_stats, leg.stat_type, None)

                if actual_result is None:
                    return False, f"Stat '{leg.stat_type}' not found for {leg.player_name}"

                leg_results[leg.id] = actual_result

            # Resolve parlay
            profit_loss = self.manager.resolve_parlay_bet(parlay.id, leg_results)

            if profit_loss is not None:
                return True, profit_loss
            else:
                return False, "Failed to resolve parlay"

        except Exception as e:
            return False, str(e)

    def resolve_all_pending(self):
        """
        Batch auto-resolve all resolvable bets

        Returns: (num_resolved, num_failed)
        """
        resolvable = self.check_resolvable_bets()

        num_resolved = 0
        num_failed = 0

        for bet_id, bet_type, player_name, game_date in resolvable:
            if bet_type == 'single':
                success, result = self.auto_resolve_single_bet(bet_id)
            else:
                success, result = self.auto_resolve_parlay_bet(bet_id)

            if success:
                num_resolved += 1
                print(f"Resolved {bet_type} bet {bet_id}: {result}")
            else:
                num_failed += 1
                print(f"Failed to resolve {bet_type} bet {bet_id}: {result}")

        return num_resolved, num_failed

    # ==================== MANUAL RESOLUTION ====================

    def manual_resolve_single_bet(self, bet_id, actual_result):
        """
        Manually input result for resolution

        Returns: (success, profit_loss or error_message)
        """
        try:
            profit_loss = self.manager.resolve_single_bet(bet_id, actual_result)

            if profit_loss is not None:
                return True, profit_loss
            else:
                return False, "Failed to resolve bet"

        except Exception as e:
            return False, str(e)

    def manual_resolve_parlay_bet(self, parlay_id, leg_results):
        """
        Manually input results for all legs

        leg_results: Dict mapping leg_id -> actual_result

        Returns: (success, profit_loss or error_message)
        """
        try:
            profit_loss = self.manager.resolve_parlay_bet(parlay_id, leg_results)

            if profit_loss is not None:
                return True, profit_loss
            else:
                return False, "Failed to resolve parlay"

        except Exception as e:
            return False, str(e)

    def void_bet(self, bet_id, bet_type='single', reason="manual"):
        """
        Mark bet as void (refund stake)

        Use cases:
        - Game postponed/cancelled
        - Player didn't play
        - Error in bet entry
        """
        try:
            success = self.manager.void_bet(bet_id, bet_type)

            if success:
                return True, f"Bet voided: {reason}"
            else:
                return False, "Failed to void bet"

        except Exception as e:
            return False, str(e)

    # ==================== HELPER METHODS ====================

    def _find_matching_game_stats(self, bet):
        """
        Find GameStats record matching a single bet

        Matching criteria:
        1. player_id matches
        2. game_date matches (if provided)
        3. If no game_date, find most recent game after bet placement
        4. Opponent matches (if provided)

        Returns: GameStats record or None
        """
        query = self.session.query(GameStats).filter(
            GameStats.player_id == bet.player_id
        )

        if bet.game_date:
            # Exact date match
            query = query.filter(GameStats.game_date == bet.game_date)
        else:
            # Find first game after bet was placed
            query = query.filter(GameStats.game_date >= bet.placed_at.date())

        if bet.opponent:
            query = query.filter(GameStats.opponent == bet.opponent)

        # Get first matching game
        return query.order_by(GameStats.game_date).first()

    def _find_matching_game_stats_for_leg(self, leg):
        """Find GameStats for a parlay leg"""
        query = self.session.query(GameStats).filter(
            GameStats.player_id == leg.player_id
        )

        if leg.game_date:
            query = query.filter(GameStats.game_date == leg.game_date)
        else:
            # Find first game after parlay was placed
            parlay = leg.parlay
            query = query.filter(GameStats.game_date >= parlay.placed_at.date())

        if leg.opponent:
            query = query.filter(GameStats.opponent == leg.opponent)

        return query.order_by(GameStats.game_date).first()
