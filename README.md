# NBA Sports Betting Prediction Model

Statistical modeling system for NBA player performance prediction and betting analysis.

## Quick Start
```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure database
createdb sports_betting
echo "DATABASE_URL=postgresql://ansh@localhost/sports_betting" > .env

# Run
python src/test_system.py
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed instructions.

## Project Structure

- `src/` - Source code
- `docs/` - Documentation
- `tests/` - Test files (coming soon)
- `.vscode/` - Editor configuration

## Documentation

- [Quick Start Guide](docs/QUICKSTART.md)
- [Setup Guide](docs/SETUP_GUIDE.md)
- [Tutorial](docs/TUTORIAL.md)
- [Architecture](docs/ARCHITECTURE.md)

Built with Python, PostgreSQL, and NBA API.