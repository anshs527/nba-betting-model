#!/usr/bin/env python3
"""
Fix the LA Clippers name mismatch in the database
"""

from database import get_session, Team

def fix_clippers_name():
    """Update Clippers name to match NBA API"""

    session = get_session()

    try:
        # Find the Clippers team
        clippers = session.query(Team).filter_by(abbreviation='LAC').first()

        if not clippers:
            print("Clippers team not found in database!")
            return

        print(f"Current name: {clippers.name}")
        print(f"Updating to: LA Clippers")

        # Update the name
        clippers.name = "LA Clippers"
        session.commit()

        print("✓ Successfully updated LA Clippers name")

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()

    finally:
        session.close()

if __name__ == "__main__":
    fix_clippers_name()
