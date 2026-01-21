#!/usr/bin/env python3
"""
CanPL SDP API Client

Client for the discovered CanPL.ca Sports Data Platform API.
Provides clean, typed access to CPL match, standings, and team data.

API Base: https://api-sdp.canpl.ca/v1/cpl/football

Discovered via TASK 1.2A (reverse-engineering canpl.ca API)
"""

import requests
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CanPLAPIClient:
    """Client for the CanPL Sports Data Platform API."""

    BASE_URL = "https://api-sdp.canpl.ca/v1/cpl/football"

    # Known season IDs (discovered via API discovery)
    SEASONS = {
        2019: "cpl::Football_Season::c8c9bdc288f34aa89073a8bd89d2da3e",
        2020: "cpl::Football_Season::11aa5cc094d0481fa8e73d326763584f",
        2021: "cpl::Football_Season::2f07c39671b84933ad7bb1e1958a7427",
        2022: "cpl::Football_Season::046f0ab31ba641c7b7bf27eb0dda4b9d",
        2023: "cpl::Football_Season::fc0855108c9044218a84fc5d2bee0000",
        2024: "cpl::Football_Season::6fb9e6fae4f24ce9bf4fa3172616a762",
        2025: "cpl::Football_Season::fd43e1d61dfe4396a7356bc432de0007",
        2026: "cpl::Football_Season::c479ab0916a24c3390f1ce2c021ace54",
    }

    # CPL Competition ID
    COMPETITION_ID = "cpl::Football_Competition::85e0d583bc894bb592558598d36c1328"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Origin': 'https://canpl.ca',
            'Referer': 'https://canpl.ca/'
        })
        self._rate_limit_delay = 1.0  # seconds between requests

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a request to the API."""
        url = f"{self.BASE_URL}/{endpoint}"

        # Add default locale if not specified
        if params is None:
            params = {}
        if 'locale' not in params:
            params['locale'] = 'en-US'

        try:
            time.sleep(self._rate_limit_delay)  # Rate limiting
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def get_season_id(self, year: int) -> Optional[str]:
        """Get the internal season ID for a given year."""
        return self.SEASONS.get(year)

    def get_matches(self, season_id: str, start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> List[Dict]:
        """
        Get all matches for a season.

        Args:
            season_id: Internal season ID (e.g., "cpl::Football_Season::...")
            start_date: Optional filter (YYYY-MM-DD)
            end_date: Optional filter (YYYY-MM-DD)

        Returns:
            List of match dictionaries
        """
        params = {}
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date

        data = self._request(f"seasons/{season_id}/matches", params)
        return data.get('matches', [])

    def get_standings(self, season_id: str, order_by: str = 'rank',
                      direction: str = 'asc') -> List[Dict]:
        """
        Get league standings for a season.

        Args:
            season_id: Internal season ID
            order_by: Sort field (rank, points, goal_difference)
            direction: Sort direction (asc, desc)

        Returns:
            List of team standings
        """
        params = {
            'orderBy': order_by,
            'direction': direction
        }
        data = self._request(f"seasons/{season_id}/standings/overall", params)

        standings = data.get('standings', [])
        if standings:
            return standings[0].get('teams', [])
        return []

    def get_teams(self, season_id: str) -> List[Dict]:
        """
        Get all teams for a season.

        Args:
            season_id: Internal season ID

        Returns:
            List of team dictionaries
        """
        data = self._request(f"seasons/{season_id}/teams")
        return data.get('teams', [])

    def get_player_stats(self, season_id: str, category: str = 'general',
                         order_by: str = 'goals', page: int = 1,
                         per_page: int = 50) -> List[Dict]:
        """
        Get player statistics for a season.

        Args:
            season_id: Internal season ID
            category: Stats category (general, passing, goalkeeping)
            order_by: Sort field (goals, assists, etc.)
            page: Page number
            per_page: Results per page

        Returns:
            List of player stat dictionaries
        """
        params = {
            'category': category,
            'orderBy': order_by,
            'role': 'All',
            'direction': 'desc',
            'page': page,
            'pageNumElement': per_page
        }
        data = self._request(f"seasons/{season_id}/stats/players", params)
        return data.get('players', [])

    def get_team_stats(self, season_id: str, category: str = 'general',
                       order_by: str = 'goals') -> List[Dict]:
        """
        Get team statistics for a season.

        Args:
            season_id: Internal season ID
            category: Stats category (general, attacking, defending)
            order_by: Sort field

        Returns:
            List of team stat dictionaries
        """
        params = {
            'category': category,
            'orderBy': order_by,
            'direction': 'desc',
            'pageNumElement': 20
        }
        data = self._request(f"seasons/{season_id}/stats/teams", params)
        return data.get('teams', [])

    def matches_to_dataframe(self, matches: List[Dict]) -> pd.DataFrame:
        """Convert matches to a clean pandas DataFrame."""
        rows = []
        for match in matches:
            if match.get('status') != 'FINISHED':
                continue  # Only include finished matches

            row = {
                'match_id': match.get('matchId'),
                'date': match.get('matchDateUtc', '')[:10],  # YYYY-MM-DD
                'season': int(match.get('matchDateUtc', '2025')[:4]),
                'matchday': match.get('matchSet', {}).get('name', ''),
                'home_team': match.get('home', {}).get('officialName', ''),
                'away_team': match.get('away', {}).get('officialName', ''),
                'home_goals': match.get('providerHomeScore', 0),
                'away_goals': match.get('providerAwayScore', 0),
                'venue': match.get('stadiumName', ''),
                'status': match.get('status'),
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values('date')
        return df

    def standings_to_dataframe(self, standings: List[Dict]) -> pd.DataFrame:
        """Convert standings to a clean pandas DataFrame."""
        rows = []
        for team in standings:
            stats = {}
            for stat in team.get('stats', []):
                stats[stat.get('statsId')] = stat.get('statsValue')

            def safe_int(val, default=0):
                if val is None:
                    return default
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return default

            row = {
                'position': safe_int(stats.get('rank')),
                'team': team.get('officialName', ''),  # Team name is directly on team object
                'played': safe_int(stats.get('matches-played')),
                'wins': safe_int(stats.get('win')),
                'draws': safe_int(stats.get('draw')),
                'losses': safe_int(stats.get('lose')),
                'goals_for': safe_int(stats.get('goals-for')),
                'goals_against': safe_int(stats.get('goals-against')),
                'goal_difference': safe_int(stats.get('goal-difference')),
                'points': safe_int(stats.get('points')),
            }
            rows.append(row)

        return pd.DataFrame(rows)


def fetch_season_data(year: int = 2025) -> Dict[str, pd.DataFrame]:
    """
    Fetch all data for a season.

    Returns dict with 'matches', 'standings', 'teams' DataFrames.
    """
    client = CanPLAPIClient()
    season_id = client.get_season_id(year)

    if not season_id:
        raise ValueError(f"Unknown season: {year}")

    logger.info(f"Fetching {year} CPL data from official API...")

    # Get matches
    matches = client.get_matches(season_id)
    matches_df = client.matches_to_dataframe(matches)
    logger.info(f"  Matches: {len(matches_df)} finished games")

    # Get standings
    standings = client.get_standings(season_id)
    standings_df = client.standings_to_dataframe(standings)
    logger.info(f"  Standings: {len(standings_df)} teams")

    # Get teams
    teams = client.get_teams(season_id)
    teams_df = pd.DataFrame([{
        'team_id': t.get('teamId'),
        'name': t.get('officialName'),
        'short_name': t.get('shortName'),
        'acronym': t.get('acronymName'),
    } for t in teams])
    logger.info(f"  Teams: {len(teams_df)} teams")

    return {
        'matches': matches_df,
        'standings': standings_df,
        'teams': teams_df
    }


if __name__ == '__main__':
    # Test the API client
    print("Testing CanPL SDP API Client...\n")

    data = fetch_season_data(2025)

    print("\n=== 2025 CPL Matches ===")
    print(data['matches'].head(20).to_string())

    print("\n=== 2025 CPL Standings ===")
    print(data['standings'].to_string())

    print("\n=== 2025 CPL Teams ===")
    print(data['teams'].to_string())

    # Save to CSV
    data['matches'].to_csv('data/matches/cpl_2025_api.csv', index=False)
    data['standings'].to_csv('data/standings_2025_api.csv', index=False)
    print("\nSaved to data/matches/cpl_2025_api.csv and data/standings_2025_api.csv")
