# Sports Betting Model - Complete Setup Guide

## Prerequisites
- Python 3.9 or higher
- PostgreSQL installed on your system
- VSCodium (or VS Code)
- Git installed

## Step 1: Install PostgreSQL

### On macOS:
```bash
brew install postgresql
brew services start postgresql
```

### On Ubuntu/Linux:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### On Windows:
Download from: https://www.postgresql.org/download/windows/

## Step 2: Create PostgreSQL Database

Open terminal and run:
```bash
# Access PostgreSQL
psql postgres

# In PostgreSQL prompt, run:
CREATE DATABASE sports_betting;
CREATE USER your_username WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE sports_betting TO your_username;
\q
```

## Step 3: Set Up GitHub Repository

### Create a new repository on GitHub:
1. Go to github.com and log in
2. Click the '+' icon → 'New repository'
3. Name it: `sports-betting-model`
4. Keep it Public (for resume visibility) or Private
5. Don't initialize with README (we'll do it locally)
6. Click 'Create repository'

### Initialize Git locally:
```bash
cd /path/to/your/project/folder
git init
git add .
git commit -m "Initial commit: Setup project structure"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/sports-betting-model.git
git push -u origin main
```

## Step 4: Set Up Python Virtual Environment

### Create and activate virtual environment:
```bash
# Navigate to your project folder
cd sports_betting_model

# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt now.

### Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 5: Configure Environment Variables

Create a `.env` file in your project root:
```bash
touch .env
```

Add this to `.env`:
```
DATABASE_URL=postgresql://your_username:your_password@localhost/sports_betting
```

**IMPORTANT**: Add `.env` to `.gitignore` so you don't commit passwords!

## Step 6: VSCodium Setup

### Install VSCodium Extensions:
1. Open VSCodium
2. Go to Extensions (Ctrl+Shift+X or Cmd+Shift+X)
3. Install these extensions:
   - Python (by Microsoft)
   - Pylance
   - Python Debugger
   - GitLens
   - PostgreSQL (by Chris Kolkman)
   - autoDocstring

### Configure Python Interpreter:
1. Open Command Palette (Ctrl+Shift+P or Cmd+Shift+P)
2. Type: "Python: Select Interpreter"
3. Choose the one in your `venv` folder: `./venv/bin/python`

### Set up debugging:
Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true,
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

## Step 7: Test Your Setup

Run the database setup:
```bash
python database.py
```

You should see: "Database tables created successfully!"

## Step 8: Collect Initial Data

Run the data collector:
```bash
python data_collector.py
```

This will take a few minutes and populate your database with player data.

## Step 9: Test the Model

Run the simple predictor:
```bash
python simple_model.py
```

You should see predictions and analysis output!

## Common Issues & Solutions

### Issue: "ModuleNotFoundError"
Solution: Make sure your virtual environment is activated (`source venv/bin/activate`)

### Issue: "psycopg2 won't install"
Solution: 
```bash
# On macOS:
brew install postgresql
export LDFLAGS="-L/opt/homebrew/opt/postgresql/lib"
pip install psycopg2-binary

# On Ubuntu:
sudo apt-get install libpq-dev python3-dev
pip install psycopg2-binary
```

### Issue: "Can't connect to PostgreSQL"
Solution: Check that PostgreSQL is running:
```bash
# macOS:
brew services list

# Linux:
sudo systemctl status postgresql
```

## Next Steps

Once everything is working:
1. Commit your changes: `git add . && git commit -m "Setup complete"`
2. Push to GitHub: `git push`
3. Start experimenting with the model!

## Project Structure
```
sports_betting_model/
├── .env                    # Database credentials (DON'T COMMIT)
├── .gitignore             # Git ignore file
├── requirements.txt       # Python dependencies
├── database.py           # Database schema
├── data_collector.py     # Fetch NBA data
├── simple_model.py       # Baseline prediction model
├── README.md             # Project documentation
└── venv/                 # Virtual environment (DON'T COMMIT)
```
