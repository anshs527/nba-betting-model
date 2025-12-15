"""
Paper Trading Management System
Handles bet placement, resolution, and analytics for paper trading
"""

from database import (
    get_session, PaperTradingAccount, SingleBet, ParlayBet, ParlayLeg,
    BankrollSnapshot, Player
)
from datetime import datetime, timedelta
from sqlalchemy import desc, func

class PaperTradingManager:
    """Manages paper trading account and bet operations"""

    def __init__(self, user_id='default_user'):
        self.session = get_session()
        self.user_id = user_id
        self.account = self._get_or_create_account()

    def _get_or_create_account(self):
        """Get existing account or create new one with $1000"""
        account = self.session.query(PaperTradingAccount).filter_by(
            user_id=self.user_id
        ).first()

        if not account:
            account = PaperTradingAccount(
                user_id=self.user_id,
                starting_bankroll=1000.0,
                current_bankroll=1000.0
            )
            self.session.add(account)
            self.session.commit()

            # Create initial snapshot
            self._create_snapshot()

        return account

    def close(self):
        """Close database session"""
        self.session.close()

    # ==================== ACCOUNT MANAGEMENT ====================

    def get_account_summary(self):
        """Return current account metrics"""
        total_profit = self.account.current_bankroll - self.account.starting_bankroll

        # Calculate ROI
        if self.account.starting_bankroll > 0:
            roi = (total_profit / self.account.starting_bankroll) * 100
        else:
            roi = 0

        # Calculate win rate
        resolved_bets = self.account.total_bets_won + self.account.total_bets_lost
        if resolved_bets > 0:
            win_rate = (self.account.total_bets_won / resolved_bets) * 100
        else:
            win_rate = 0

        # Count pending bets
        pending_singles = self.session.query(SingleBet).filter_by(
            account_id=self.account.id,
            status='pending'
        ).count()

        pending_parlays = self.session.query(ParlayBet).filter_by(
            account_id=self.account.id,
            status='pending'
        ).count()

        return {
            'current_bankroll': self.account.current_bankroll,
            'starting_bankroll': self.account.starting_bankroll,
            'total_profit': total_profit,
            'roi': roi,
            'win_rate': win_rate,
            'total_bets': self.account.total_bets_placed,
            'total_won': self.account.total_bets_won,
            'total_lost': self.account.total_bets_lost,
            'total_void': self.account.total_bets_void,
            'pending_bets': pending_singles + pending_parlays
        }

    def check_sufficient_funds(self, stake):
        """Validate user has enough bankroll"""
        available = self.account.current_bankroll
        if stake > available:
            return False, available
        return True, available

    def reset_account(self, new_bankroll=1000.0):
        """Reset account to fresh state"""
        # Update all bets to archived status (optional - for now just reset counters)
        self.account.starting_bankroll = new_bankroll
        self.account.current_bankroll = new_bankroll
        self.account.total_bets_placed = 0
        self.account.total_bets_won = 0
        self.account.total_bets_lost = 0
        self.account.total_bets_void = 0
        self.account.last_updated = datetime.utcnow()

        self.session.commit()
        self._create_snapshot()

    # ==================== SINGLE BET OPERATIONS ====================

    def place_single_bet(self, player_name, stat_type, line, direction, stake,
                         prediction, probability, confidence, std_dev,
                         opponent=None, days_rest=None, game_date=None):
        """
        Place a single player bet

        Returns: bet_id if successful, None if error
        """
        try:
            # Validate funds
            sufficient, _ = self.check_sufficient_funds(stake)
            if not sufficient:
                return None

            # Get player_id
            player = self.session.query(Player).filter_by(name=player_name).first()
            if not player:
                print(f"Player {player_name} not found in database")
                return None

            # Calculate potential payout (at -110 odds)
            odds = -110
            potential_payout = stake + (stake * (100 / 110))  # Stake + profit

            # Calculate EV
            expected_value = (probability * (stake * (100 / 110))) - ((1 - probability) * stake)

            # Create bet
            bet = SingleBet(
                account_id=self.account.id,
                player_id=player.id,
                player_name=player_name,
                stat_type=stat_type,
                line=line,
                direction=direction,
                stake=stake,
                odds=odds,
                potential_payout=potential_payout,
                prediction=prediction,
                probability=probability,
                expected_value=expected_value,
                confidence=confidence,
                std_dev=std_dev,
                opponent=opponent,
                days_rest=days_rest,
                game_date=game_date
            )

            self.session.add(bet)

            # Deduct stake from bankroll
            self.account.current_bankroll -= stake
            self.account.total_bets_placed += 1
            self.account.last_updated = datetime.utcnow()

            self.session.commit()

            # Create snapshot
            self._create_snapshot()

            return bet.id

        except Exception as e:
            self.session.rollback()
            print(f"Error placing bet: {e}")
            return None

    def get_pending_single_bets(self):
        """Get all pending single bets"""
        return self.session.query(SingleBet).filter_by(
            account_id=self.account.id,
            status='pending'
        ).order_by(desc(SingleBet.placed_at)).all()

    def get_single_bet_history(self, limit=50, status_filter=None):
        """Get resolved single bets"""
        query = self.session.query(SingleBet).filter(
            SingleBet.account_id == self.account.id,
            SingleBet.status.in_(['won', 'lost', 'void'])
        )

        if status_filter and status_filter.lower() != 'all':
            query = query.filter_by(status=status_filter.lower())

        return query.order_by(desc(SingleBet.resolved_at)).limit(limit).all()

    # ==================== PARLAY BET OPERATIONS ====================

    def place_parlay_bet(self, picks_data, stake, payout_multiplier,
                         parlay_probability, expected_value):
        """
        Place a parlay bet

        picks_data: List of dicts with pick details
        Returns: parlay_bet_id if successful, None if error
        """
        try:
            # Validate funds
            sufficient, _ = self.check_sufficient_funds(stake)
            if not sufficient:
                return None

            # Calculate potential payout
            potential_payout = stake * payout_multiplier

            # Convert numpy types to Python native types
            parlay_probability = float(parlay_probability)
            expected_value = float(expected_value)

            # Create parlay bet
            parlay = ParlayBet(
                account_id=self.account.id,
                stake=stake,
                payout_multiplier=payout_multiplier,
                potential_payout=potential_payout,
                parlay_probability=parlay_probability,
                expected_value=expected_value,
                num_picks=len(picks_data)
            )

            self.session.add(parlay)
            self.session.flush()  # Get parlay.id

            # Create parlay legs
            for pick_data in picks_data:
                # Use player_id from picks_data if provided, otherwise look up
                if 'player_id' in pick_data and pick_data['player_id']:
                    player_id = pick_data['player_id']
                else:
                    player = self.session.query(Player).filter_by(
                        name=pick_data['player_name']
                    ).first()

                    if not player:
                        print(f"Player {pick_data['player_name']} not found")
                        continue
                    player_id = player.id

                # Convert numpy types to Python native types
                prediction = float(pick_data['prediction'])
                probability = float(pick_data['probability'])
                confidence = float(pick_data['confidence'])
                line = float(pick_data['line'])

                leg = ParlayLeg(
                    parlay_id=parlay.id,
                    player_id=player_id,
                    player_name=pick_data['player_name'],
                    stat_type=pick_data['stat_type'],
                    line=line,
                    direction=pick_data['direction'],
                    prediction=prediction,
                    probability=probability,
                    confidence=confidence,
                    opponent=pick_data.get('opponent'),
                    days_rest=pick_data.get('days_rest'),
                    game_date=pick_data.get('game_date')
                )

                self.session.add(leg)

            # Deduct stake from bankroll
            self.account.current_bankroll -= stake
            self.account.total_bets_placed += 1
            self.account.last_updated = datetime.utcnow()

            self.session.commit()

            # Create snapshot
            self._create_snapshot()

            return parlay.id

        except Exception as e:
            self.session.rollback()
            print(f"Error placing parlay bet: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_pending_parlay_bets(self):
        """Get all pending parlay bets with legs"""
        return self.session.query(ParlayBet).filter_by(
            account_id=self.account.id,
            status='pending'
        ).order_by(desc(ParlayBet.placed_at)).all()

    def get_parlay_bet_history(self, limit=50, status_filter=None):
        """Get resolved parlay bets"""
        query = self.session.query(ParlayBet).filter(
            ParlayBet.account_id == self.account.id,
            ParlayBet.status.in_(['won', 'lost', 'void'])
        )

        if status_filter and status_filter.lower() != 'all':
            query = query.filter_by(status=status_filter.lower())

        return query.order_by(desc(ParlayBet.resolved_at)).limit(limit).all()

    # ==================== BET RESOLUTION ====================

    def resolve_single_bet(self, bet_id, actual_result):
        """
        Resolve a single bet

        Returns: profit_loss amount
        """
        try:
            bet = self.session.query(SingleBet).get(bet_id)

            if not bet or bet.status != 'pending':
                return None

            # Update actual result
            bet.actual_result = actual_result

            # Determine outcome
            if bet.direction == "OVER":
                won = actual_result > bet.line
            else:  # UNDER
                won = actual_result < bet.line

            # Handle push (exactly on line)
            if actual_result == bet.line:
                bet.status = 'void'
                bet.profit_loss = 0
                self.account.current_bankroll += bet.stake  # Refund
                self.account.total_bets_void += 1
            elif won:
                bet.status = 'won'
                profit = bet.stake * (100 / 110)  # At -110 odds
                bet.profit_loss = profit
                self.account.current_bankroll += bet.potential_payout
                self.account.total_bets_won += 1
            else:
                bet.status = 'lost'
                bet.profit_loss = -bet.stake
                self.account.total_bets_lost += 1

            bet.resolved_at = datetime.utcnow()
            self.account.last_updated = datetime.utcnow()

            self.session.commit()

            # Create snapshot
            self._create_snapshot()

            return bet.profit_loss

        except Exception as e:
            self.session.rollback()
            print(f"Error resolving bet: {e}")
            return None

    def resolve_parlay_bet(self, parlay_id, leg_results):
        """
        Resolve a parlay bet

        leg_results: Dict mapping leg_id -> actual_result
        Returns: profit_loss amount
        """
        try:
            parlay = self.session.query(ParlayBet).get(parlay_id)

            if not parlay or parlay.status != 'pending':
                return None

            # Resolve each leg
            all_won = True
            any_void = False

            for leg in parlay.legs:
                if leg.id in leg_results:
                    actual = leg_results[leg.id]
                    leg.actual_result = actual

                    # Determine outcome for this leg
                    if leg.direction == "OVER":
                        won = actual > leg.line
                    else:
                        won = actual < leg.line

                    # Handle push
                    if actual == leg.line:
                        leg.status = 'void'
                        any_void = True
                    elif won:
                        leg.status = 'won'
                    else:
                        leg.status = 'lost'
                        all_won = False

            # Determine parlay outcome
            if any_void:
                # Conservative: void entire parlay
                parlay.status = 'void'
                parlay.profit_loss = 0
                self.account.current_bankroll += parlay.stake  # Refund
                self.account.total_bets_void += 1
            elif all_won:
                parlay.status = 'won'
                profit = parlay.potential_payout - parlay.stake
                parlay.profit_loss = profit
                self.account.current_bankroll += parlay.potential_payout
                self.account.total_bets_won += 1
            else:
                parlay.status = 'lost'
                parlay.profit_loss = -parlay.stake
                self.account.total_bets_lost += 1

            parlay.resolved_at = datetime.utcnow()
            self.account.last_updated = datetime.utcnow()

            self.session.commit()

            # Create snapshot
            self._create_snapshot()

            return parlay.profit_loss

        except Exception as e:
            self.session.rollback()
            print(f"Error resolving parlay: {e}")
            return None

    def void_bet(self, bet_id, bet_type='single'):
        """Mark bet as void and refund stake"""
        try:
            if bet_type == 'single':
                bet = self.session.query(SingleBet).get(bet_id)
                refund = bet.stake if bet else 0
            else:
                bet = self.session.query(ParlayBet).get(bet_id)
                refund = bet.stake if bet else 0

            if not bet or bet.status != 'pending':
                return False

            bet.status = 'void'
            bet.profit_loss = 0
            bet.resolved_at = datetime.utcnow()

            self.account.current_bankroll += refund
            self.account.total_bets_void += 1
            self.account.last_updated = datetime.utcnow()

            self.session.commit()

            # Create snapshot
            self._create_snapshot()

            return True

        except Exception as e:
            self.session.rollback()
            print(f"Error voiding bet: {e}")
            return False

    # ==================== ANALYTICS ====================

    def calculate_metrics_by_stat_type(self):
        """Calculate performance metrics by stat type"""
        metrics = {}

        for stat_type in ['points', 'rebounds', 'assists']:
            bets = self.session.query(SingleBet).filter(
                SingleBet.account_id == self.account.id,
                SingleBet.stat_type == stat_type,
                SingleBet.status.in_(['won', 'lost'])
            ).all()

            if not bets:
                metrics[stat_type] = {
                    'total_bets': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0,
                    'total_profit': 0,
                    'roi': 0,
                    'avg_confidence': 0
                }
                continue

            wins = sum(1 for b in bets if b.status == 'won')
            total = len(bets)
            win_rate = (wins / total) * 100

            total_profit = sum(b.profit_loss for b in bets)
            total_stake = sum(b.stake for b in bets)
            roi = (total_profit / total_stake * 100) if total_stake > 0 else 0

            avg_confidence = sum(b.confidence for b in bets) / total

            metrics[stat_type] = {
                'total_bets': total,
                'wins': wins,
                'losses': total - wins,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'roi': roi,
                'avg_confidence': avg_confidence
            }

        return metrics

    def calculate_confidence_correlation(self):
        """Analyze win rate by confidence level"""
        bets = self.session.query(SingleBet).filter(
            SingleBet.account_id == self.account.id,
            SingleBet.status.in_(['won', 'lost'])
        ).all()

        buckets = {
            'low': [],      # 0-1 σ
            'medium': [],   # 1-2 σ
            'high': []      # 2+ σ
        }

        for bet in bets:
            if bet.confidence < 1.0:
                buckets['low'].append(bet)
            elif bet.confidence < 2.0:
                buckets['medium'].append(bet)
            else:
                buckets['high'].append(bet)

        results = {}
        for level, bucket_bets in buckets.items():
            if not bucket_bets:
                results[level] = {
                    'total_bets': 0,
                    'win_rate': 0,
                    'avg_profit': 0
                }
            else:
                wins = sum(1 for b in bucket_bets if b.status == 'won')
                total = len(bucket_bets)
                win_rate = (wins / total) * 100
                avg_profit = sum(b.profit_loss for b in bucket_bets) / total

                results[level] = {
                    'total_bets': total,
                    'win_rate': win_rate,
                    'avg_profit': avg_profit
                }

        return results

    def get_bankroll_history(self, days=30):
        """Get bankroll snapshots for charting"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        snapshots = self.session.query(BankrollSnapshot).filter(
            BankrollSnapshot.account_id == self.account.id,
            BankrollSnapshot.timestamp >= cutoff
        ).order_by(BankrollSnapshot.timestamp).all()

        return [(s.timestamp, s.bankroll, s.total_profit) for s in snapshots]

    # ==================== HELPER METHODS ====================

    def _create_snapshot(self):
        """Create a bankroll snapshot"""
        try:
            total_profit = self.account.current_bankroll - self.account.starting_bankroll

            resolved_bets = self.account.total_bets_won + self.account.total_bets_lost
            if resolved_bets > 0:
                win_rate = (self.account.total_bets_won / resolved_bets) * 100
            else:
                win_rate = 0

            snapshot = BankrollSnapshot(
                account_id=self.account.id,
                bankroll=self.account.current_bankroll,
                total_profit=total_profit,
                total_bets=self.account.total_bets_placed,
                win_rate=win_rate
            )

            self.session.add(snapshot)
            self.session.commit()

        except Exception as e:
            print(f"Error creating snapshot: {e}")
