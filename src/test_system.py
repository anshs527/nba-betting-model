"""
Quick Start Script - Test the entire system
Run this after setup to verify everything works
"""

import sys
from database import create_database, get_session, Player, GameStats
from data_collector import NBADataCollector
from simple_model import SimplePredictor

def test_database():
    """Test database connection and setup"""
    print("\n" + "="*60)
    print("STEP 1: Testing Database Connection")
    print("="*60)
    
    try:
        create_database()
        session = get_session()
        player_count = session.query(Player).count()
        print(f"✓ Database connected successfully!")
        print(f"✓ Found {player_count} players in database")
        session.close()
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database 'sports_betting' exists")
        print("3. .env file has correct DATABASE_URL")
        return False

def collect_sample_data():
    """Collect data for a few test players"""
    print("\n" + "="*60)
    print("STEP 2: Collecting Sample Data")
    print("="*60)
    
    try:
        collector = NBADataCollector()
        
        # Check if we already have data
        session = get_session()
        game_count = session.query(GameStats).count()
        
        if game_count > 0:
            print(f"✓ Database already has {game_count} games")
            print("  Skipping data collection...")
            collector.close()
            session.close()
            return True
        
        print("Fetching all NBA players... (this takes ~30 seconds)")
        collector.fetch_all_players()
        
        print("\nFetching game stats for 3 test players...")
        test_players = [
            'LeBron James',
            'Stephen Curry',
            'Giannis Antetokounmpo'
        ]
        
        for player in test_players:
            print(f"  → Fetching {player}...")
            collector.fetch_player_game_stats(player, season='2024-25')
        
        collector.close()
        session.close()
        print("✓ Data collection complete!")
        return True
        
    except Exception as e:
        print(f"✗ Data collection error: {e}")
        print("\nThis might be due to:")
        print("1. NBA API rate limiting (wait a minute and try again)")
        print("2. Network connectivity issues")
        print("3. NBA API changes")
        return False

def test_predictions():
    """Test the prediction model"""
    print("\n" + "="*60)
    print("STEP 3: Testing Prediction Model")
    print("="*60)
    
    try:
        # Install scipy if needed
        try:
            from scipy.stats import norm
        except ImportError:
            print("Installing scipy...")
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'scipy'])
        
        predictor = SimplePredictor(stat_type='points', lookback_games=10)
        
        # Test with LeBron James
        print("\nTesting with LeBron James (Points, Line: 24.5)")
        result = predictor.analyze_player('LeBron James', line=24.5)
        
        if result:
            print("\n✓ Prediction model working!")
            print(f"  Recommendation: {result['recommendation']}")
            print(f"  Confidence: {result['confidence']:.2f} std devs")
        else:
            print("✗ No data available for predictions")
            print("  Make sure you ran data collection first")
            return False
        
        predictor.close()
        return True
        
    except Exception as e:
        print(f"✗ Prediction error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "🏀"*30)
    print("NBA SPORTS BETTING MODEL - SYSTEM TEST")
    print("🏀"*30)
    
    # Run tests in sequence
    if not test_database():
        print("\n❌ Database test failed. Fix database issues before continuing.")
        return
    
    if not collect_sample_data():
        print("\n❌ Data collection failed. Check error messages above.")
        return
    
    if not test_predictions():
        print("\n❌ Prediction test failed. Check error messages above.")
        return
    
    # All tests passed!
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED! System is ready to use.")
    print("="*60)
    
    print("\n📊 Quick Usage Examples:")
    print("\n1. Analyze a player:")
    print("   python -c \"from simple_model import SimplePredictor; p = SimplePredictor('points'); p.analyze_player('LeBron James', 25.5)\"")
    
    print("\n2. Collect more player data:")
    print("   python -c \"from data_collector import NBADataCollector; c = NBADataCollector(); c.fetch_player_game_stats('Luka Doncic')\"")
    
    print("\n3. Check database:")
    print("   psql sports_betting -c 'SELECT name, COUNT(*) as games FROM players JOIN game_stats ON players.id = game_stats.player_id GROUP BY name ORDER BY games DESC LIMIT 10;'")
    
    print("\n📚 Next Steps:")
    print("  • Read TUTORIAL.md for detailed explanations")
    print("  • Add more players to track")
    print("  • Experiment with different prediction parameters")
    print("  • Build a dashboard with Streamlit")
    
    print("\n🎯 For Your Resume:")
    print("  • Built statistical model using Bayesian inference")
    print("  • Automated data pipeline with NBA API integration")
    print("  • Implemented expected value framework for decision making")
    print("  • Used PostgreSQL for efficient data storage and querying")
    
    print("\n")

if __name__ == "__main__":
    main()
