"""
Load CPL CSV data into PostgreSQL database.
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection settings
DB_CONFIG = {
    'dbname': 'cpl_analytics',
    'user': os.getenv('USER'),  # Uses current system user
    'host': 'localhost',
    'port': 5432
}

# Team name to ID mapping (from schema.sql INSERT order)
TEAM_IDS = {
    'Forge FC': 1,
    'Cavalry FC': 2,
    'Pacific FC': 3,
    'York United FC': 4,
    'Valour FC': 5,
    'HFX Wanderers FC': 6,
    'FC Edmonton': 7,
    'Vancouver FC': 8,
    'Atletico Ottawa': 9,
}


def get_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def load_matches(data_dir: str):
    """Load match data from CSVs into PostgreSQL."""
    conn = get_connection()
    cur = conn.cursor()

    matches_dir = Path(data_dir) / "matches"

    # Clear existing match data
    cur.execute("DELETE FROM match_stats")
    cur.execute("DELETE FROM contextual_data")
    cur.execute("DELETE FROM historical_odds")
    cur.execute("DELETE FROM lineups")
    cur.execute("DELETE FROM matches")
    conn.commit()

    total_loaded = 0

    for csv_file in sorted(matches_dir.glob("cpl_*.csv")):
        if 'sample' in csv_file.name or 'all' in csv_file.name:
            continue

        logger.info(f"Loading {csv_file.name}...")
        df = pd.read_csv(csv_file)

        for _, row in df.iterrows():
            home_team_id = TEAM_IDS.get(row['home_team'])
            away_team_id = TEAM_IDS.get(row['away_team'])

            if not home_team_id or not away_team_id:
                logger.warning(f"Unknown team: {row['home_team']} or {row['away_team']}")
                continue

            cur.execute("""
                INSERT INTO matches (
                    season, date, home_team_id, away_team_id,
                    home_goals, away_goals, venue
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                row['season'],
                row['date'],
                home_team_id,
                away_team_id,
                row['home_goals'],
                row['away_goals'],
                row.get('venue', None)
            ))
            total_loaded += 1

        conn.commit()

    cur.close()
    conn.close()

    logger.info(f"Loaded {total_loaded} matches into PostgreSQL")
    return total_loaded


def verify_data():
    """Verify data was loaded correctly."""
    conn = get_connection()
    cur = conn.cursor()

    # Count matches
    cur.execute("SELECT COUNT(*) FROM matches")
    match_count = cur.fetchone()[0]

    # Count by season
    cur.execute("""
        SELECT season, COUNT(*) as matches
        FROM matches
        GROUP BY season
        ORDER BY season
    """)
    seasons = cur.fetchall()

    # Get sample match with team names
    cur.execute("""
        SELECT m.date, ht.name as home_team, at.name as away_team,
               m.home_goals, m.away_goals
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        ORDER BY m.date DESC
        LIMIT 5
    """)
    recent = cur.fetchall()

    cur.close()
    conn.close()

    print(f"\n{'='*50}")
    print("DATABASE VERIFICATION")
    print('='*50)
    print(f"\nTotal matches: {match_count}")
    print("\nMatches by season:")
    for season, count in seasons:
        print(f"  {season}: {count} matches")

    print("\nMost recent matches:")
    for date, home, away, hg, ag in recent:
        print(f"  {date}: {home} {hg}-{ag} {away}")


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"

    print("Loading CPL data into PostgreSQL...")
    load_matches(data_dir)
    verify_data()


if __name__ == "__main__":
    main()
