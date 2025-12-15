# Setup Checklist

Use this checklist to make sure you've completed all setup steps correctly.

## Prerequisites Installation

- [ ] Python 3.9+ installed
  - Check: `python3 --version`
  
- [ ] PostgreSQL installed and running
  - macOS: `brew services list | grep postgresql`
  - Linux: `sudo systemctl status postgresql`
  - Windows: Check Services app
  
- [ ] Git installed
  - Check: `git --version`
  
- [ ] VSCodium (or VS Code) installed

## Project Setup

- [ ] Created project folder
  ```bash
  mkdir sports_betting_model
  cd sports_betting_model
  ```

- [ ] Downloaded all project files to the folder
  - database.py
  - data_collector.py
  - simple_model.py
  - requirements.txt
  - .gitignore
  - README.md
  - SETUP_GUIDE.md
  - TUTORIAL.md
  - test_system.py

## Database Configuration

- [ ] Created PostgreSQL database
  ```bash
  createdb sports_betting
  # OR
  psql postgres
  CREATE DATABASE sports_betting;
  \q
  ```

- [ ] Created PostgreSQL user (optional, can use default)
  ```sql
  CREATE USER your_username WITH PASSWORD 'your_password';
  GRANT ALL PRIVILEGES ON DATABASE sports_betting TO your_username;
  ```

- [ ] Created `.env` file with database credentials
  ```
  DATABASE_URL=postgresql://username:password@localhost/sports_betting
  ```

- [ ] Verified `.env` is in `.gitignore` (it should be!)

## Python Environment

- [ ] Created virtual environment
  ```bash
  python3 -m venv venv
  ```

- [ ] Activated virtual environment
  ```bash
  source venv/bin/activate  # macOS/Linux
  venv\Scripts\activate      # Windows
  ```

- [ ] Installed dependencies
  ```bash
  pip install -r requirements.txt
  ```

- [ ] Verified installation
  ```bash
  pip list
  # Should see: pandas, numpy, sqlalchemy, psycopg2-binary, nba_api, etc.
  ```

## VSCodium Configuration

- [ ] Opened project in VSCodium
  ```bash
  codium .  # or code . for VS Code
  ```

- [ ] Installed Python extension
  - Extensions → Search "Python" → Install

- [ ] Selected Python interpreter
  - Cmd/Ctrl + Shift + P
  - "Python: Select Interpreter"
  - Choose `./venv/bin/python`

- [ ] Verified .vscode/settings.json exists

- [ ] Verified .vscode/launch.json exists

## Testing the System

- [ ] Created database tables
  ```bash
  python database.py
  # Should see: "Database tables created successfully!"
  ```

- [ ] Verified tables in PostgreSQL
  ```bash
  psql sports_betting
  \dt
  # Should see: players, teams, game_stats, prizepicks_lines
  ```

- [ ] Ran system test
  ```bash
  python test_system.py
  # Should see: "✅ ALL TESTS PASSED!"
  ```

- [ ] Collected initial data (if not done by test script)
  ```bash
  python data_collector.py
  ```

- [ ] Tested predictions
  ```bash
  python simple_model.py
  ```

## GitHub Setup

- [ ] Created GitHub account (if needed)

- [ ] Created new repository on GitHub
  - Name: `sports-betting-model`
  - Public or Private

- [ ] Initialized Git locally
  ```bash
  git init
  git add .
  git commit -m "Initial commit: NBA betting prediction model"
  ```

- [ ] Connected to GitHub
  ```bash
  git branch -M main
  git remote add origin https://github.com/YOUR_USERNAME/sports-betting-model.git
  git push -u origin main
  ```

- [ ] Verified files on GitHub
  - Should see README.md, code files, etc.
  - Should NOT see .env, venv/, __pycache__/

## Verification

Run these commands to verify everything:

```bash
# 1. Check Python environment
which python
# Should be: /path/to/sports_betting_model/venv/bin/python

# 2. Check database connection
python -c "from database import get_session; print('DB connected!')"

# 3. Check data exists
python -c "from database import get_session, Player; s = get_session(); print(f'Players: {s.query(Player).count()}')"

# 4. Quick prediction test
python -c "from simple_model import SimplePredictor; p = SimplePredictor('points'); print(p.get_player_recent_stats('LeBron James'))"
```

## Common Issues

### Issue: Can't connect to database
**Solution:**
```bash
# Check PostgreSQL is running
brew services list | grep postgresql  # macOS
sudo systemctl status postgresql      # Linux

# Restart if needed
brew services restart postgresql      # macOS
sudo systemctl restart postgresql     # Linux
```

### Issue: ModuleNotFoundError
**Solution:**
```bash
# Make sure venv is activated (you should see (venv) in terminal)
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

### Issue: psycopg2 installation fails
**Solution:**
```bash
# macOS
brew install postgresql
pip install psycopg2-binary

# Ubuntu/Linux
sudo apt-get install libpq-dev python3-dev
pip install psycopg2-binary
```

### Issue: NBA API rate limiting
**Solution:**
```bash
# Just wait 1-2 minutes and try again
# The API has rate limits to prevent abuse
```

## Next Steps After Setup

Once everything is checked off:

1. Read through TUTORIAL.md to understand how everything works
2. Experiment with different players and prediction parameters
3. Start thinking about improvements (Bayesian models, opponent adjustments, etc.)
4. Consider building a dashboard with Streamlit
5. Add this project to your resume with bullet points about:
   - Data pipeline development
   - Statistical modeling
   - Database design
   - API integration

## Questions?

If you get stuck:
1. Check the error message carefully
2. Look in SETUP_GUIDE.md for detailed instructions
3. Search the error on Google/Stack Overflow
4. Check if PostgreSQL is actually running
5. Make sure virtual environment is activated

Good luck! 🏀📊
