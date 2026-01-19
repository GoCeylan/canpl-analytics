"""
CPL Data Loader
Helper functions for loading and working with CPL Analytics data.
"""

import pandas as pd
import os
from typing import Optional, List, Union
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default data directory
DATA_DIR = Path(__file__).parent.parent / "data"


class CPLDataLoader:
    """Load and query CPL Analytics data."""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize data loader.

        Args:
            data_dir: Path to data directory. Defaults to ../data relative to this file.
        """
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR

    def load_matches(self, seasons: Optional[List[int]] = None) -> pd.DataFrame:
        """
        Load match data for specified seasons.

        Args:
            seasons: List of seasons to load (e.g., [2023, 2024]).
                    If None, loads all available seasons.

        Returns:
            DataFrame with all match data
        """
        matches_dir = self.data_dir / "matches"

        if not matches_dir.exists():
            logger.warning(f"Matches directory not found: {matches_dir}")
            return pd.DataFrame()

        dfs = []

        for file in matches_dir.glob("cpl_*.csv"):
            # Extract year from filename
            try:
                year = int(file.stem.split('_')[1])
            except (IndexError, ValueError):
                continue

            if seasons is None or year in seasons:
                df = pd.read_csv(file)
                dfs.append(df)
                logger.info(f"Loaded {len(df)} matches from {file.name}")

        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            combined['date'] = pd.to_datetime(combined['date'])
            return combined.sort_values('date').reset_index(drop=True)

        return pd.DataFrame()

    def load_team_stats(self) -> pd.DataFrame:
        """Load team season statistics."""
        stats_file = self.data_dir / "team_stats" / "team_season_stats.csv"

        if stats_file.exists():
            return pd.read_csv(stats_file)

        logger.warning(f"Team stats file not found: {stats_file}")
        return pd.DataFrame()

    def load_historical_odds(self, seasons: Optional[List[int]] = None) -> pd.DataFrame:
        """
        Load historical betting odds.

        Args:
            seasons: Seasons to load odds for

        Returns:
            DataFrame with odds history
        """
        odds_dir = self.data_dir / "historical_odds"

        if not odds_dir.exists():
            return pd.DataFrame()

        dfs = []

        for file in odds_dir.glob("odds_*.csv"):
            try:
                year = int(file.stem.split('_')[1])
            except (IndexError, ValueError):
                continue

            if seasons is None or year in seasons:
                df = pd.read_csv(file)
                dfs.append(df)

        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            if 'timestamp' in combined.columns:
                combined['timestamp'] = pd.to_datetime(combined['timestamp'])
            return combined

        return pd.DataFrame()

    def get_team_matches(self, team: str,
                         home_only: bool = False,
                         away_only: bool = False) -> pd.DataFrame:
        """
        Get all matches for a specific team.

        Args:
            team: Team name
            home_only: Only return home matches
            away_only: Only return away matches

        Returns:
            DataFrame of team's matches
        """
        matches = self.load_matches()

        if matches.empty:
            return matches

        if home_only:
            return matches[matches['home_team'] == team]
        elif away_only:
            return matches[matches['away_team'] == team]
        else:
            return matches[
                (matches['home_team'] == team) |
                (matches['away_team'] == team)
            ]

    def get_head_to_head(self, team1: str, team2: str) -> pd.DataFrame:
        """
        Get head-to-head record between two teams.

        Args:
            team1: First team
            team2: Second team

        Returns:
            DataFrame of matches between the teams
        """
        matches = self.load_matches()

        if matches.empty:
            return matches

        h2h = matches[
            ((matches['home_team'] == team1) & (matches['away_team'] == team2)) |
            ((matches['home_team'] == team2) & (matches['away_team'] == team1))
        ]

        return h2h.sort_values('date')

    def get_recent_form(self, team: str, n_matches: int = 5) -> str:
        """
        Get recent form string for a team (e.g., "WWDLW").

        Args:
            team: Team name
            n_matches: Number of recent matches to consider

        Returns:
            Form string (W=Win, D=Draw, L=Loss)
        """
        matches = self.get_team_matches(team).tail(n_matches)

        if matches.empty:
            return ""

        form = []
        for _, match in matches.iterrows():
            is_home = match['home_team'] == team
            team_goals = match['home_goals'] if is_home else match['away_goals']
            opp_goals = match['away_goals'] if is_home else match['home_goals']

            if pd.isna(team_goals) or pd.isna(opp_goals):
                continue

            if team_goals > opp_goals:
                form.append('W')
            elif team_goals < opp_goals:
                form.append('L')
            else:
                form.append('D')

        return ''.join(form)

    def calculate_team_stats(self, team: str,
                             season: Optional[int] = None) -> dict:
        """
        Calculate aggregate statistics for a team.

        Args:
            team: Team name
            season: Season to filter by (optional)

        Returns:
            Dictionary of statistics
        """
        matches = self.load_matches(seasons=[season] if season else None)
        team_matches = matches[
            (matches['home_team'] == team) |
            (matches['away_team'] == team)
        ]

        if team_matches.empty:
            return {}

        # Calculate stats
        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0

        for _, m in team_matches.iterrows():
            is_home = m['home_team'] == team
            gf = m['home_goals'] if is_home else m['away_goals']
            ga = m['away_goals'] if is_home else m['home_goals']

            if pd.isna(gf) or pd.isna(ga):
                continue

            goals_for += gf
            goals_against += ga

            if gf > ga:
                wins += 1
            elif gf < ga:
                losses += 1
            else:
                draws += 1

        played = wins + draws + losses

        return {
            'team': team,
            'season': season,
            'played': played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goals_for - goals_against,
            'points': wins * 3 + draws,
            'win_rate': wins / played if played > 0 else 0,
            'ppg': (wins * 3 + draws) / played if played > 0 else 0,
        }

    def get_standings(self, season: int) -> pd.DataFrame:
        """
        Calculate league standings for a season.

        Args:
            season: Season year

        Returns:
            DataFrame with standings
        """
        matches = self.load_matches(seasons=[season])

        if matches.empty:
            return pd.DataFrame()

        teams = set(matches['home_team'].unique()) | set(matches['away_team'].unique())

        standings = []
        for team in teams:
            stats = self.calculate_team_stats(team, season)
            if stats:
                standings.append(stats)

        if not standings:
            return pd.DataFrame()

        df = pd.DataFrame(standings)
        df = df.sort_values(
            ['points', 'goal_difference', 'goals_for'],
            ascending=[False, False, False]
        ).reset_index(drop=True)

        df['position'] = range(1, len(df) + 1)

        return df[['position', 'team', 'played', 'wins', 'draws', 'losses',
                   'goals_for', 'goals_against', 'goal_difference', 'points']]


# Convenience functions for quick access

def load_cpl_matches(seasons: Optional[List[int]] = None) -> pd.DataFrame:
    """Quick function to load CPL matches."""
    return CPLDataLoader().load_matches(seasons)


def load_cpl_odds(seasons: Optional[List[int]] = None) -> pd.DataFrame:
    """Quick function to load CPL odds."""
    return CPLDataLoader().load_historical_odds(seasons)


def get_standings(season: int) -> pd.DataFrame:
    """Quick function to get standings."""
    return CPLDataLoader().get_standings(season)


if __name__ == "__main__":
    # Demo usage
    loader = CPLDataLoader()

    print("CPL Data Loader Demo")
    print("=" * 50)

    # Load all matches
    matches = loader.load_matches()
    print(f"\nTotal matches loaded: {len(matches)}")

    if not matches.empty:
        print(f"Seasons available: {sorted(matches['season'].unique())}")
        print(f"Teams: {sorted(matches['home_team'].unique())}")

        # Get Forge FC stats
        forge_stats = loader.calculate_team_stats('Forge FC')
        print(f"\nForge FC overall stats: {forge_stats}")

        # Get recent form
        form = loader.get_recent_form('Forge FC', 5)
        print(f"Forge FC recent form: {form}")
