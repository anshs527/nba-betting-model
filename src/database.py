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
