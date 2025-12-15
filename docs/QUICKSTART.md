# Quick Start - 5 Minute Setup

**Goal:** Get the system running as fast as possible

## Step 1: Install PostgreSQL (if not installed)

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Ubuntu/Linux:**
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

## Step 2: Create Database
```bash
createdb sports_betting
```

## Step 3: Setup Python Environment
```bash
cd sports_betting_model
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 4: Configure Database Connection
Create `.env` file:
```bash
echo "DATABASE_URL=postgresql://localhost/sports_betting" > .env
```

## Step 5: Run the System
```bash
python test_system.py
```

That's it! If all goes well, you should see "✅ ALL TESTS PASSED!"

## Troubleshooting

**If Step 2 fails:**
```bash
psql postgres
CREATE DATABASE sports_betting;
\q
```

**If Step 5 fails with database error:**
- Make sure PostgreSQL is running: `brew services list` (macOS) or `sudo systemctl status postgresql` (Linux)
- Check your DATABASE_URL in `.env` file

**If Step 5 fails with module error:**
- Make sure virtual environment is activated (you should see `(venv)` in terminal)
- Run: `pip install -r requirements.txt` again

## What to do after setup

1. **Analyze a player:**
```bash
python -c "from simple_model import SimplePredictor; p = SimplePredictor('points'); p.analyze_player('LeBron James', 25.5)"
```

2. **Add more players:**
Edit `data_collector.py` and add names to the `example_players` list, then run:
```bash
python data_collector.py
```

3. **Setup GitHub:**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/sports-betting-model.git
git push -u origin main
```

## Next Steps

- Read TUTORIAL.md for detailed explanations
- Read CHECKLIST.md for comprehensive setup verification
- Start customizing the model for your needs

## File Overview

- `database.py` - Database schema (tables for players, games, etc.)
- `data_collector.py` - Fetches NBA data from API
- `simple_model.py` - Makes predictions
- `test_system.py` - Tests everything works
- `TUTORIAL.md` - Learn how it all works
- `CHECKLIST.md` - Detailed setup checklist
- `README.md` - For your GitHub repository
