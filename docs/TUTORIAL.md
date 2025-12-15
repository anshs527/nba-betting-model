# Building the Sports Betting Model - Tutorial

This tutorial walks you through how the system works and how to extend it.

## Part 1: Understanding the Database (database.py)

### What's happening here?

We're using SQLAlchemy, which is an ORM (Object-Relational Mapping). This means you can work with database tables as if they were Python objects.

```python
class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    # ... more fields
```

This creates a table called 'players' with columns for id, name, etc.

### The Relationships

Notice this line:
```python
game_stats = relationship("GameStats", back_populates="player")
```

This creates a connection between Player and GameStats tables. So when you have a player object, you can access all their games like:
```python
player = session.query(Player).filter_by(name='LeBron James').first()
all_lebron_games = player.game_stats  # This gives you all his games!
```

### Try it yourself:

1. Run `python database.py` - this creates all the tables
2. Open PostgreSQL:
   ```bash
   psql sports_betting
   \dt  # Lists all tables
   \d players  # Shows the players table structure
   ```

## Part 2: Collecting Data (data_collector.py)

### How the NBA API works

The `nba_api` library wraps the official NBA stats API. Here's what happens:

```python
game_log = playergamelog.PlayerGameLog(
    player_id=player.nba_id,
    season='2024-25'
)
```

This hits the NBA API and gets all games for that player this season.

### Rate Limiting

Notice these lines:
```python
time.sleep(0.6)  # Wait 600ms between requests
```

This prevents you from hitting the API too fast and getting blocked. NBA's API has rate limits.

### The Data Flow

1. `fetch_all_players()` gets all active NBA players → stores in database
2. `fetch_player_game_stats()` gets game-by-game stats for one player
3. For each game, we parse the data and create a GameStats object
4. Store it in the database

### Try it yourself:

1. Run `python data_collector.py`
2. Check your database:
   ```bash
   psql sports_betting
   SELECT COUNT(*) FROM players;
   SELECT name FROM players LIMIT 10;
   SELECT * FROM game_stats WHERE player_id = 1 LIMIT 5;
   ```

3. Modify the example_players list to add your favorite players:
   ```python
   example_players = [
       'Anthony Edwards',
       'Jayson Tatum',
       # Add more here
   ]
   ```

## Part 3: The Prediction Model (simple_model.py)

### How predictions work

The basic idea: "How did this player perform recently? Probably similar next game."

#### Simple Average Method:
```python
prediction = recent_stats['points'].mean()
```

Just takes the mean of last N games. Easy but doesn't account for trends.

#### Weighted Average Method:
```python
weights = [0.9^0, 0.9^1, 0.9^2, ...]  # Most recent game = 1.0
prediction = sum(stat_values * weights)
```

Recent games count more. If a player is on a hot streak, this captures it better.

### The Statistics Behind It

We're assuming player performance follows a **normal distribution** (bell curve).

```python
from scipy.stats import norm
prob_over = 1 - norm.cdf(line, prediction, std_dev)
```

This calculates: "What's the probability they score OVER the line?"

Example:
- Prediction: 25 points, std_dev: 5
- Line: 24.5
- Z-score: (25 - 24.5) / 5 = 0.1
- Probability over: ~54%

### Expected Value (EV)

This is THE key metric in betting:
```python
ev_over = prob_over * 0.909 - prob_under * 1.0
```

Why 0.909? Standard betting odds are -110, meaning:
- Bet $1.10 to win $1.00
- So if you win, you get back $2.10 (your $1.10 + $1.00 profit)
- Net profit per $1 risked: $1 / $1.10 = 0.909

**Positive EV = good bet in theory**
**Negative EV = bad bet in theory**

### Try it yourself:

1. Run `python simple_model.py`
2. Try different players and lines:
   ```python
   predictor = SimplePredictor(stat_type='points', lookback_games=10)
   predictor.analyze_player('Anthony Edwards', line=28.5)
   ```

3. Experiment with different stat types:
   ```python
   # Rebounds
   rebound_predictor = SimplePredictor(stat_type='rebounds', lookback_games=10)
   rebound_predictor.analyze_player('Domantas Sabonis', line=12.5)
   
   # Assists
   assist_predictor = SimplePredictor(stat_type='assists', lookback_games=10)
   assist_predictor.analyze_player('Trae Young', line=11.5)
   ```

## Part 4: Extending the Model

### Next Steps to Improve

#### 1. Add Opponent Adjustments

Right now we ignore who they're playing. But defense matters!

Create a new file `advanced_model.py`:
```python
def get_opponent_defensive_rating(opponent):
    """Get how good this team's defense is"""
    # Lower = better defense
    # You could scrape this from NBA.com or basketball-reference
    pass

def adjust_for_opponent(base_prediction, opponent):
    """Adjust prediction based on opponent"""
    opp_rating = get_opponent_defensive_rating(opponent)
    league_avg = 112.0  # points per 100 possessions
    adjustment_factor = opp_rating / league_avg
    return base_prediction * adjustment_factor
```

#### 2. Add Home/Away Splits

Players perform differently at home vs away.

```python
def get_home_away_split(player_name):
    """Calculate how much better/worse at home"""
    home_games = session.query(GameStats).filter_by(
        player_id=player.id,
        is_home=True
    ).all()
    
    away_games = session.query(GameStats).filter_by(
        player_id=player.id,
        is_home=False
    ).all()
    
    home_avg = np.mean([g.points for g in home_games])
    away_avg = np.mean([g.points for g in away_games])
    
    return home_avg - away_avg  # Difference
```

#### 3. Bayesian Model (Advanced)

Install PyMC3:
```bash
pip install pymc3
```

Basic Bayesian approach:
```python
import pymc3 as pm

with pm.Model() as model:
    # Prior: We think player averages around 25 points
    mu = pm.Normal('mu', mu=25, sigma=10)
    sigma = pm.HalfNormal('sigma', sigma=5)
    
    # Likelihood: Observed data
    points = pm.Normal('points', mu=mu, sigma=sigma, observed=recent_games)
    
    # Posterior: Updated belief after seeing data
    trace = pm.sample(1000)
    
    # Predict next game
    prediction = pm.sample_posterior_predictive(trace)
```

This is more sophisticated because it:
- Updates beliefs with new data
- Accounts for uncertainty properly
- Can incorporate prior knowledge (like career averages)

## Part 5: Adding Real PrizePicks Lines

Right now we're manually entering lines. Let's automate it!

### Option 1: Manual Entry Helper

Create `prizepicks_manager.py`:
```python
from database import get_session, PrizePicks, Player
from datetime import date

def add_prizepicks_line(player_name, stat_type, line_value):
    """Add a PrizePicks line to database"""
    session = get_session()
    player = session.query(Player).filter_by(name=player_name).first()
    
    if not player:
        print(f"Player {player_name} not found")
        return
    
    pp_line = PrizePicks(
        player_id=player.id,
        date=date.today(),
        stat_type=stat_type,
        line=line_value
    )
    session.add(pp_line)
    session.commit()
    print(f"Added {player_name} {stat_type} line: {line_value}")

# Usage
add_prizepicks_line('LeBron James', 'points', 24.5)
add_prizepicks_line('Stephen Curry', 'points', 26.5)
```

### Option 2: Web Scraping (Advanced)

This is tricky because PrizePicks has anti-scraping measures. But here's the concept:

```python
import requests
from bs4 import BeautifulSoup

def scrape_prizepicks():
    """Scrape current PrizePicks lines"""
    # You'd need to:
    # 1. Inspect PrizePicks website
    # 2. Find the API endpoints they use
    # 3. Make requests to get JSON data
    # 4. Parse and store in database
    pass
```

## Part 6: Backtesting Your Model

Critical for knowing if your model actually works!

Create `backtest.py`:
```python
def backtest_predictions(player_name, start_date, end_date):
    """
    Test how well predictions would have done historically
    """
    session = get_session()
    player = session.query(Player).filter_by(name=player_name).first()
    
    games = session.query(GameStats).filter(
        GameStats.player_id == player.id,
        GameStats.game_date >= start_date,
        GameStats.game_date <= end_date
    ).order_by(GameStats.game_date).all()
    
    correct_predictions = 0
    total_predictions = 0
    
    for i in range(10, len(games)):  # Need 10 games of history
        # Use games [i-10:i] to predict game i
        historical = games[i-10:i]
        actual_game = games[i]
        
        # Make prediction
        predicted = np.mean([g.points for g in historical])
        actual = actual_game.points
        
        # Check accuracy (using a hypothetical line)
        line = predicted  # Pretend line equals our prediction
        
        if actual > line:
            actual_result = 'OVER'
        else:
            actual_result = 'UNDER'
        
        # Our model would recommend OVER if prediction > line
        # But since line = prediction, this is 50/50
        # You'd adjust this based on real lines
        
        total_predictions += 1
    
    accuracy = correct_predictions / total_predictions
    print(f"Backtest accuracy: {accuracy*100:.1f}%")
```

## Part 7: Creating a Dashboard

Want to visualize your predictions? Let's use Streamlit (super easy):

```bash
pip install streamlit plotly
```

Create `dashboard.py`:
```python
import streamlit as st
import plotly.graph_objects as go
from simple_model import SimplePredictor

st.title("NBA Betting Model Dashboard")

player_name = st.text_input("Enter player name:", "LeBron James")
stat_type = st.selectbox("Stat type:", ["points", "rebounds", "assists"])
line = st.number_input("PrizePicks line:", value=25.0)

if st.button("Analyze"):
    predictor = SimplePredictor(stat_type=stat_type)
    result = predictor.analyze_player(player_name, line)
    
    if result:
        st.metric("Prediction", f"{result['prediction']:.1f}")
        st.metric("Probability OVER", f"{result['prob_over']*100:.1f}%")
        st.metric("Recommendation", result['recommendation'])
```

Run it:
```bash
streamlit run dashboard.py
```

## Tips for Your Resume

When talking about this project:

1. **Technical Skills**: "Built ETL pipeline using NBA API, PostgreSQL, and SQLAlchemy"
2. **Statistical Modeling**: "Implemented Bayesian inference for probabilistic predictions"
3. **Problem Solving**: "Designed expected value framework to evaluate betting opportunities"
4. **Real-world Application**: "Created system processing 1000+ games to generate actionable insights"

## Questions to Expect in Interviews

- "How did you handle missing data?" (Players sitting out, DNP, etc.)
- "How do you validate your model?" (Backtesting, cross-validation)
- "What assumptions does your model make?" (Normal distribution, independence of games)
- "How would you scale this?" (Batch processing, caching, async API calls)

Good luck building! Let me know if you get stuck on any part.
