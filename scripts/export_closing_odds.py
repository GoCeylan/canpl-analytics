"""
Export closing odds from private database to public CSV.

This script pulls closing odds from your PRIVATE odds database and exports
them to the PUBLIC repo (run weekly after matches complete).

Usage:
    python scripts/export_closing_odds.py

Environment Variables:
    PRIVATE_ODDS_DB_PATH: Path to private SQLite odds database
    PUBLIC_REPO_PATH: Path to public canpl-analytics repo (optional)

Example:
    export PRIVATE_ODDS_DB_PATH=../cpl-betting-system/data/odds_history.db
    python scripts/export_closing_odds.py
"""

import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path


def export_closing_odds_to_public(private_db_path: str, public_csv_path: str, season: int) -> pd.DataFrame:
    """
    Export closing odds from private database to public CSV.

    Args:
        private_db_path: Path to private odds database (SQLite)
        public_csv_path: Path to public closing_odds CSV
        season: Season year (e.g., 2024, 2025)

    Returns:
        DataFrame with exported odds
    """
    # Validate inputs
    if not os.path.exists(private_db_path):
        print(f"Error: Private database not found at {private_db_path}")
        print("Set PRIVATE_ODDS_DB_PATH environment variable to your odds database location.")
        sys.exit(1)

    # Connect to private database
    conn = sqlite3.connect(private_db_path)

    # Get last week's matches (only export after matches complete)
    last_week = datetime.now() - timedelta(days=7)

    # Query closing odds from private database
    # Adjust column names based on your actual schema
    query = """
    SELECT
        match_id,
        date,
        home_team,
        away_team,
        bookmaker,
        closing_home_odds AS closing_home,
        closing_draw_odds AS closing_draw,
        closing_away_odds AS closing_away,
        closing_over_2_5 AS "closing_over_2.5",
        closing_under_2_5 AS "closing_under_2.5",
        scraped_at
    FROM odds_history
    WHERE season = ?
      AND date >= ?
      AND is_closing = 1
    ORDER BY date, match_id, bookmaker
    """

    try:
        df = pd.read_sql_query(query, conn, params=(season, last_week.date().isoformat()))
    except Exception as e:
        print(f"Warning: Could not query with expected schema: {e}")
        print("Attempting alternative query...")

        # Alternative query for different schema
        alt_query = """
        SELECT
            match_id,
            date,
            home_team,
            away_team,
            bookmaker,
            home_odds AS closing_home,
            draw_odds AS closing_draw,
            away_odds AS closing_away,
            over_2_5_odds AS "closing_over_2.5",
            under_2_5_odds AS "closing_under_2.5",
            scraped_at
        FROM odds_history
        WHERE season = ?
          AND date >= ?
        ORDER BY date, match_id, bookmaker
        """
        df = pd.read_sql_query(alt_query, conn, params=(season, last_week.date().isoformat()))

    conn.close()

    if df.empty:
        print(f"No new closing odds found for season {season} in the last 7 days.")
        return df

    # Ensure output directory exists
    output_dir = Path(public_csv_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load existing public data (if any)
    if os.path.exists(public_csv_path):
        try:
            existing = pd.read_csv(public_csv_path)
            if not existing.empty:
                # Append new data, remove duplicates
                df = pd.concat([existing, df], ignore_index=True).drop_duplicates(
                    subset=['match_id', 'bookmaker'],
                    keep='last'
                )
                # Sort by date and match
                df = df.sort_values(['date', 'match_id', 'bookmaker'])
        except Exception as e:
            print(f"Warning: Could not read existing file: {e}")

    # Save to public CSV
    df.to_csv(public_csv_path, index=False)

    print(f"Exported {len(df)} closing odds records to {public_csv_path}")

    return df


def generate_match_id(home_team: str, away_team: str, date: str) -> str:
    """
    Generate a consistent match_id from team names and date.

    Args:
        home_team: Home team name
        away_team: Away team name
        date: Match date (YYYY-MM-DD format)

    Returns:
        Match ID in format: home_vs_away_YYYYMMDD
    """
    # Clean team names
    home_clean = home_team.lower().replace(' fc', '').replace(' ', '_').strip()
    away_clean = away_team.lower().replace(' fc', '').replace(' ', '_').strip()
    date_clean = date.replace('-', '')

    return f"{home_clean}_vs_{away_clean}_{date_clean}"


def validate_odds(df: pd.DataFrame) -> bool:
    """
    Validate odds data before export.

    Args:
        df: DataFrame with odds data

    Returns:
        True if valid, False otherwise
    """
    # Check required columns
    required_cols = ['match_id', 'date', 'home_team', 'away_team', 'bookmaker',
                     'closing_home', 'closing_draw', 'closing_away']

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"Error: Missing required columns: {missing}")
        return False

    # Validate odds ranges (decimal odds should be >= 1.0)
    odds_cols = ['closing_home', 'closing_draw', 'closing_away']
    for col in odds_cols:
        if (df[col] < 1.0).any():
            print(f"Warning: Found odds < 1.0 in {col}")
            return False

    # Check for valid bookmakers
    valid_bookmakers = {'bet365', 'sportsinteraction'}
    invalid = set(df['bookmaker'].unique()) - valid_bookmakers
    if invalid:
        print(f"Warning: Unknown bookmakers found: {invalid}")

    return True


def main():
    """Main entry point for the export script."""
    # Configuration - override with environment variables
    PRIVATE_DB = os.getenv('PRIVATE_ODDS_DB_PATH', '../cpl-betting-system/data/odds_history.db')
    SCRIPT_DIR = Path(__file__).parent.parent
    PUBLIC_CSV_DIR = SCRIPT_DIR / 'data' / 'closing_odds'

    # Default to current year's season
    current_year = datetime.now().year
    SEASON = int(os.getenv('EXPORT_SEASON', current_year))

    # Construct output path
    PUBLIC_CSV = PUBLIC_CSV_DIR / f'cpl_{SEASON}_closing_odds.csv'

    print(f"CPL Closing Odds Export")
    print(f"=======================")
    print(f"Private DB: {PRIVATE_DB}")
    print(f"Public CSV: {PUBLIC_CSV}")
    print(f"Season: {SEASON}")
    print()

    # Export odds
    df = export_closing_odds_to_public(
        private_db_path=PRIVATE_DB,
        public_csv_path=str(PUBLIC_CSV),
        season=SEASON
    )

    if not df.empty:
        # Validate exported data
        if validate_odds(df):
            print(f"\nValidation passed!")
        else:
            print(f"\nValidation warnings - please review data")

        # Print summary
        print(f"\nSummary:")
        print(f"  Total records: {len(df)}")
        print(f"  Unique matches: {df['match_id'].nunique()}")
        print(f"  Bookmakers: {', '.join(df['bookmaker'].unique())}")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")


if __name__ == '__main__':
    main()
