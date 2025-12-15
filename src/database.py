"""
Database schema for sports betting prediction model
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

Base = declarative_base()

class Player(Base):
    """Store player information"""
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    nba_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    team = Column(String(50))
    position = Column(String(10))
    
    # Relationship to game stats
    game_stats = relationship("GameStats", back_populates="player")

class Team(Base):
    """Store team information"""
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True)
    nba_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    abbreviation = Column(String(10))

class TeamDefensiveStats(Base):
    """Store team defensive statistics"""
    __tablename__ = 'team_defensive_stats'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False)
    team_name = Column(String(100), nullable=False)

    # Overall defensive rating
    def_rating = Column(Float)  # Points allowed per 100 possessions

    # Position-specific defensive ratings
    def_rating_vs_guards = Column(Float)
    def_rating_vs_forwards = Column(Float)
    def_rating_vs_centers = Column(Float)

    # Timestamp for data freshness
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)

class GameStats(Base):
    """Store individual game statistics for players"""
    __tablename__ = 'game_stats'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    game_date = Column(Date, nullable=False)
    opponent = Column(String(50))
    is_home = Column(Boolean)

    # Rest tracking
    days_rest = Column(Integer)  # Number of days since last game
    is_back_to_back = Column(Boolean)  # True if this is a back-to-back game

    # Stats we care about for betting
    points = Column(Float)
    rebounds = Column(Float)
    assists = Column(Float)
    minutes = Column(Float)
    field_goals_made = Column(Integer)
    field_goals_attempted = Column(Integer)
    three_pointers_made = Column(Integer)
    three_pointers_attempted = Column(Integer)
    free_throws_made = Column(Integer)
    free_throws_attempted = Column(Integer)
    steals = Column(Float)
    blocks = Column(Float)
    turnovers = Column(Float)

    # Relationship
    player = relationship("Player", back_populates="game_stats")

class PrizePicks(Base):
    """Store PrizePicks lines for comparison"""
    __tablename__ = 'prizepicks_lines'

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    date = Column(Date, nullable=False)
    stat_type = Column(String(50))  # 'points', 'rebounds', 'assists', etc.
    line = Column(Float, nullable=False)  # The over/under line

class PaperTradingAccount(Base):
    """Tracks the paper trading account balance and metadata"""
    __tablename__ = 'paper_trading_account'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), default='default_user', nullable=False)
    starting_bankroll = Column(Float, default=1000.0, nullable=False)
    current_bankroll = Column(Float, default=1000.0, nullable=False)
    total_bets_placed = Column(Integer, default=0)
    total_bets_won = Column(Integer, default=0)
    total_bets_lost = Column(Integer, default=0)
    total_bets_void = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    single_bets = relationship("SingleBet", back_populates="account")
    parlay_bets = relationship("ParlayBet", back_populates="account")
    snapshots = relationship("BankrollSnapshot", back_populates="account")

class SingleBet(Base):
    """Tracks individual single player bets"""
    __tablename__ = 'single_bets'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('paper_trading_account.id'), nullable=False)

    # Bet identification
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    player_name = Column(String(100), nullable=False)
    stat_type = Column(String(50), nullable=False)  # 'points', 'rebounds', 'assists'
    line = Column(Float, nullable=False)  # The over/under line
    direction = Column(String(10), nullable=False)  # 'OVER' or 'UNDER'

    # Bet details
    stake = Column(Float, nullable=False)  # Amount wagered
    odds = Column(Float, default=-110)  # American odds format
    potential_payout = Column(Float, nullable=False)  # stake * multiplier

    # Prediction data (snapshot at time of bet)
    prediction = Column(Float, nullable=False)  # Model's prediction
    probability = Column(Float, nullable=False)  # Win probability
    expected_value = Column(Float, nullable=False)  # EV at time of bet
    confidence = Column(Float, nullable=False)  # Z-score/confidence level
    std_dev = Column(Float)  # Standard deviation

    # Context data
    opponent = Column(String(50))  # Opponent team
    days_rest = Column(Integer)  # Days rest before game
    game_date = Column(Date)  # Scheduled game date

    # Bet status
    status = Column(String(20), default='pending')  # 'pending', 'won', 'lost', 'void'
    actual_result = Column(Float)  # Actual stat value (when resolved)
    profit_loss = Column(Float, default=0.0)  # Actual P/L

    # Timestamps
    placed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime)

    # Relationships
    account = relationship("PaperTradingAccount", back_populates="single_bets")
    player = relationship("Player")

class ParlayBet(Base):
    """Tracks parlay bets (multiple picks combined)"""
    __tablename__ = 'parlay_bets'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('paper_trading_account.id'), nullable=False)

    # Bet details
    stake = Column(Float, nullable=False)
    payout_multiplier = Column(Float, nullable=False)  # e.g., 3.0 for 3x
    potential_payout = Column(Float, nullable=False)

    # Prediction data (overall parlay)
    parlay_probability = Column(Float, nullable=False)  # Combined probability
    expected_value = Column(Float, nullable=False)  # Overall EV
    num_picks = Column(Integer, nullable=False)  # Number of legs

    # Bet status
    status = Column(String(20), default='pending')  # 'pending', 'won', 'lost', 'void'
    profit_loss = Column(Float, default=0.0)

    # Timestamps
    placed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime)

    # Relationships
    account = relationship("PaperTradingAccount", back_populates="parlay_bets")
    legs = relationship("ParlayLeg", back_populates="parlay", cascade="all, delete-orphan")

class ParlayLeg(Base):
    """Individual legs (picks) within a parlay"""
    __tablename__ = 'parlay_legs'

    id = Column(Integer, primary_key=True)
    parlay_id = Column(Integer, ForeignKey('parlay_bets.id'), nullable=False)

    # Pick details
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False)
    player_name = Column(String(100), nullable=False)
    stat_type = Column(String(50), nullable=False)
    line = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False)

    # Prediction data
    prediction = Column(Float, nullable=False)
    probability = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)

    # Context
    opponent = Column(String(50))
    days_rest = Column(Integer)
    game_date = Column(Date)

    # Resolution
    status = Column(String(20), default='pending')  # 'pending', 'won', 'lost', 'void'
    actual_result = Column(Float)

    # Relationships
    parlay = relationship("ParlayBet", back_populates="legs")
    player = relationship("Player")

class BankrollSnapshot(Base):
    """Historical snapshots of bankroll for charting over time"""
    __tablename__ = 'bankroll_snapshots'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('paper_trading_account.id'), nullable=False)
    bankroll = Column(Float, nullable=False)
    total_profit = Column(Float, nullable=False)  # Cumulative profit
    total_bets = Column(Integer, nullable=False)
    win_rate = Column(Float)  # Percentage
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    account = relationship("PaperTradingAccount", back_populates="snapshots")

def create_database(db_url=None):
    """Create all tables in the database"""
    if db_url is None:
        db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/sports_betting')
    
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    print(f"Database tables created successfully!")
    return engine

def get_session(db_url=None):
    """Get a database session"""
    if db_url is None:
        db_url = os.getenv('DATABASE_URL', 'postgresql://localhost/sports_betting')
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == "__main__":
    create_database()
