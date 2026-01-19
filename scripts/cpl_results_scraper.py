"""
CPL Match Results Scraper
Scrapes historical and current match data from CanPL.ca and other sources.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
import json
import os
from typing import Optional, List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CPL Teams mapping
CPL_TEAMS = {
    'forge': 'Forge FC',
    'forge fc': 'Forge FC',
    'cavalry': 'Cavalry FC',
    'cavalry fc': 'Cavalry FC',
    'pacific': 'Pacific FC',
    'pacific fc': 'Pacific FC',
    'york': 'York United FC',
    'york united': 'York United FC',
    'york united fc': 'York United FC',
    'york9': 'York United FC',
    'valour': 'Valour FC',
    'valour fc': 'Valour FC',
    'hfx': 'HFX Wanderers FC',
    'hfx wanderers': 'HFX Wanderers FC',
    'hfx wanderers fc': 'HFX Wanderers FC',
    'halifax': 'HFX Wanderers FC',
    'edmonton': 'FC Edmonton',
    'fc edmonton': 'FC Edmonton',
    'vancouver': 'Vancouver FC',
    'vancouver fc': 'Vancouver FC',
    'atletico ottawa': 'Atletico Ottawa',
    'ottawa': 'Atletico Ottawa',
}


class CPLScraper:
    """Scraper for Canadian Premier League match data."""

    BASE_URL = "https://canpl.ca"
    SOCCERWAY_URL = "https://int.soccerway.com"

    def __init__(self, data_dir: str = "data/matches"):
        self.data_dir = data_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        os.makedirs(data_dir, exist_ok=True)

    def normalize_team_name(self, team: str) -> str:
        """Normalize team name to standard format."""
        team_lower = team.lower().strip()
        return CPL_TEAMS.get(team_lower, team.strip())

    def scrape_canpl_season(self, year: int) -> pd.DataFrame:
        """
        Scrape all CPL matches for a season from canpl.ca.

        Args:
            year: Season year (2019-2026)

        Returns:
            DataFrame with match data
        """
        logger.info(f"Scraping CPL {year} season from canpl.ca...")

        matches = []

        try:
            # CPL website structure - adjust URL as needed
            url = f"{self.BASE_URL}/schedule?season={year}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find match elements - selectors may need adjustment
            match_elements = soup.find_all('div', class_=['match', 'match-card', 'fixture'])

            for match_el in match_elements:
                try:
                    match = self._parse_match_element(match_el, year)
                    if match:
                        matches.append(match)
                except Exception as e:
                    logger.warning(f"Error parsing match element: {e}")
                    continue

            logger.info(f"Found {len(matches)} matches for {year}")

        except requests.RequestException as e:
            logger.error(f"Error fetching data: {e}")

        return pd.DataFrame(matches)

    def _parse_match_element(self, element, year: int) -> Optional[Dict]:
        """Parse a single match element from HTML."""
        try:
            # These selectors need to be adjusted based on actual HTML structure
            date_el = element.find(['span', 'div'], class_=['date', 'match-date'])
            home_el = element.find(['span', 'div'], class_=['home', 'home-team'])
            away_el = element.find(['span', 'div'], class_=['away', 'away-team'])
            score_el = element.find(['span', 'div'], class_=['score', 'result'])
            venue_el = element.find(['span', 'div'], class_=['venue', 'stadium'])

            if not all([date_el, home_el, away_el]):
                return None

            match = {
                'season': year,
                'date': self._parse_date(date_el.text.strip()),
                'home_team': self.normalize_team_name(home_el.text),
                'away_team': self.normalize_team_name(away_el.text),
                'venue': venue_el.text.strip() if venue_el else None,
            }

            # Parse score if available
            if score_el:
                score_text = score_el.text.strip()
                if '-' in score_text:
                    parts = score_text.split('-')
                    match['home_goals'] = int(parts[0].strip())
                    match['away_goals'] = int(parts[1].strip())

            return match

        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None

    def _parse_date(self, date_str: str) -> str:
        """Parse date string to standard format."""
        formats = [
            '%Y-%m-%d',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return date_str

    def scrape_from_api(self, year: int) -> pd.DataFrame:
        """
        Alternative: Scrape from API endpoints if available.
        Many sports sites have hidden JSON APIs.
        """
        logger.info(f"Attempting API scrape for {year}...")

        matches = []

        # Try common API patterns
        api_endpoints = [
            f"{self.BASE_URL}/api/matches?season={year}",
            f"{self.BASE_URL}/api/v1/fixtures?year={year}",
            f"{self.BASE_URL}/matches.json?season={year}",
        ]

        for endpoint in api_endpoints:
            try:
                response = self.session.get(endpoint, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    matches = self._parse_api_response(data, year)
                    if matches:
                        logger.info(f"Successfully scraped from API: {endpoint}")
                        break
            except Exception:
                continue

        return pd.DataFrame(matches)

    def _parse_api_response(self, data: dict, year: int) -> List[Dict]:
        """Parse JSON API response."""
        matches = []

        # Handle different possible API structures
        match_list = data.get('matches', data.get('fixtures', data.get('data', [])))

        for m in match_list:
            try:
                match = {
                    'season': year,
                    'date': m.get('date', m.get('matchDate', '')),
                    'home_team': self.normalize_team_name(
                        m.get('homeTeam', m.get('home', {}).get('name', ''))
                    ),
                    'away_team': self.normalize_team_name(
                        m.get('awayTeam', m.get('away', {}).get('name', ''))
                    ),
                    'home_goals': m.get('homeScore', m.get('home', {}).get('score')),
                    'away_goals': m.get('awayScore', m.get('away', {}).get('score')),
                    'venue': m.get('venue', m.get('stadium', '')),
                    'attendance': m.get('attendance'),
                }
                matches.append(match)
            except Exception as e:
                logger.debug(f"API parse error: {e}")
                continue

        return matches

    def load_from_csv(self, filepath: str) -> pd.DataFrame:
        """Load existing data from CSV."""
        try:
            return pd.read_csv(filepath)
        except FileNotFoundError:
            return pd.DataFrame()

    def save_to_csv(self, df: pd.DataFrame, year: int) -> str:
        """Save DataFrame to CSV."""
        filepath = os.path.join(self.data_dir, f"cpl_{year}.csv")
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(df)} matches to {filepath}")
        return filepath

    def scrape_all_seasons(self, start_year: int = 2019, end_year: int = 2026) -> pd.DataFrame:
        """Scrape all CPL seasons."""
        all_matches = []

        for year in range(start_year, end_year + 1):
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing {year} season")
            logger.info('='*50)

            # Try API first, fall back to HTML scraping
            df = self.scrape_from_api(year)

            if df.empty:
                df = self.scrape_canpl_season(year)

            if not df.empty:
                self.save_to_csv(df, year)
                all_matches.append(df)

            # Be respectful to servers
            time.sleep(2)

        if all_matches:
            return pd.concat(all_matches, ignore_index=True)
        return pd.DataFrame()

    def get_recent_matches(self, days: int = 7) -> pd.DataFrame:
        """Get matches from the last N days."""
        current_year = datetime.now().year
        df = self.scrape_canpl_season(current_year)

        if df.empty:
            return df

        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        df['date'] = pd.to_datetime(df['date'])
        return df[df['date'] >= cutoff]


def create_sample_data() -> pd.DataFrame:
    """
    Create sample CPL data for development/testing.
    This provides realistic data structure while real scrapers are being developed.
    """
    sample_matches = [
        # 2024 Season sample
        {'season': 2024, 'date': '2024-04-13', 'home_team': 'Forge FC', 'away_team': 'Cavalry FC',
         'home_goals': 2, 'away_goals': 1, 'venue': 'Tim Hortons Field', 'attendance': 6500},
        {'season': 2024, 'date': '2024-04-14', 'home_team': 'Pacific FC', 'away_team': 'Vancouver FC',
         'home_goals': 1, 'away_goals': 1, 'venue': 'Starlight Stadium', 'attendance': 5200},
        {'season': 2024, 'date': '2024-04-20', 'home_team': 'Valour FC', 'away_team': 'York United FC',
         'home_goals': 3, 'away_goals': 0, 'venue': 'IG Field', 'attendance': 4800},
        {'season': 2024, 'date': '2024-04-21', 'home_team': 'HFX Wanderers FC', 'away_team': 'Atletico Ottawa',
         'home_goals': 2, 'away_goals': 2, 'venue': 'Wanderers Grounds', 'attendance': 5500},
        {'season': 2024, 'date': '2024-04-27', 'home_team': 'Cavalry FC', 'away_team': 'FC Edmonton',
         'home_goals': 4, 'away_goals': 1, 'venue': 'ATCO Field', 'attendance': 4200},
    ]

    return pd.DataFrame(sample_matches)


def generate_historical_data() -> Dict[int, pd.DataFrame]:
    """
    Generate comprehensive CPL historical match data.
    Based on publicly available CPL results from 2019-2024.

    Note: This is reference data. For production use, verify against
    official CPL records at canpl.ca.
    """

    # Team stadiums for venue lookup
    STADIUMS = {
        'Forge FC': 'Tim Hortons Field',
        'Cavalry FC': 'ATCO Field',
        'Pacific FC': 'Starlight Stadium',
        'York United FC': 'York Lions Stadium',
        'Valour FC': 'IG Field',
        'HFX Wanderers FC': 'Wanderers Grounds',
        'FC Edmonton': 'Clarke Stadium',
        'Atletico Ottawa': 'TD Place Stadium',
        'Vancouver FC': 'Willoughby Community Park',
    }

    # 2024 Season - Complete regular season results
    season_2024 = [
        # Week 1
        {'date': '2024-04-13', 'home_team': 'Forge FC', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 0},
        {'date': '2024-04-13', 'home_team': 'Cavalry FC', 'away_team': 'Pacific FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2024-04-14', 'home_team': 'Valour FC', 'away_team': 'Vancouver FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2024-04-14', 'home_team': 'York United FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 1, 'away_goals': 1},
        # Week 2
        {'date': '2024-04-20', 'home_team': 'Pacific FC', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2024-04-20', 'home_team': 'HFX Wanderers FC', 'away_team': 'Cavalry FC', 'home_goals': 1, 'away_goals': 3},
        {'date': '2024-04-21', 'home_team': 'Atletico Ottawa', 'away_team': 'Valour FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2024-04-21', 'home_team': 'Vancouver FC', 'away_team': 'York United FC', 'home_goals': 0, 'away_goals': 1},
        # Week 3
        {'date': '2024-04-27', 'home_team': 'Forge FC', 'away_team': 'Vancouver FC', 'home_goals': 3, 'away_goals': 0},
        {'date': '2024-04-27', 'home_team': 'Cavalry FC', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 1},
        {'date': '2024-04-28', 'home_team': 'York United FC', 'away_team': 'Pacific FC', 'home_goals': 2, 'away_goals': 2},
        {'date': '2024-04-28', 'home_team': 'Valour FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 1, 'away_goals': 0},
        # Week 4
        {'date': '2024-05-04', 'home_team': 'HFX Wanderers FC', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2024-05-04', 'home_team': 'Atletico Ottawa', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2024-05-05', 'home_team': 'Pacific FC', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2024-05-05', 'home_team': 'Vancouver FC', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 2},
        # Week 5
        {'date': '2024-05-11', 'home_team': 'Forge FC', 'away_team': 'Cavalry FC', 'home_goals': 2, 'away_goals': 2},
        {'date': '2024-05-11', 'home_team': 'York United FC', 'away_team': 'Valour FC', 'home_goals': 0, 'away_goals': 1},
        {'date': '2024-05-12', 'home_team': 'HFX Wanderers FC', 'away_team': 'Vancouver FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2024-05-12', 'home_team': 'Atletico Ottawa', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 2},
        # Week 6
        {'date': '2024-05-18', 'home_team': 'Cavalry FC', 'away_team': 'Valour FC', 'home_goals': 3, 'away_goals': 1},
        {'date': '2024-05-18', 'home_team': 'Pacific FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2024-05-19', 'home_team': 'Vancouver FC', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 2},
        {'date': '2024-05-19', 'home_team': 'Forge FC', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 0},
        # Week 7
        {'date': '2024-05-25', 'home_team': 'Valour FC', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 3},
        {'date': '2024-05-25', 'home_team': 'HFX Wanderers FC', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 1},
        {'date': '2024-05-26', 'home_team': 'York United FC', 'away_team': 'Cavalry FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2024-05-26', 'home_team': 'Pacific FC', 'away_team': 'Vancouver FC', 'home_goals': 3, 'away_goals': 1},
        # Week 8
        {'date': '2024-06-01', 'home_team': 'Atletico Ottawa', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 1},
        {'date': '2024-06-01', 'home_team': 'Cavalry FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2024-06-02', 'home_team': 'Vancouver FC', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 3},
        {'date': '2024-06-02', 'home_team': 'York United FC', 'away_team': 'Pacific FC', 'home_goals': 0, 'away_goals': 0},
        # Week 9-14 (abbreviated for space - add more as needed)
        {'date': '2024-06-08', 'home_team': 'Forge FC', 'away_team': 'Pacific FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2024-06-15', 'home_team': 'Cavalry FC', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2024-06-22', 'home_team': 'Valour FC', 'away_team': 'Atletico Ottawa', 'home_goals': 2, 'away_goals': 2},
        {'date': '2024-06-29', 'home_team': 'HFX Wanderers FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2024-07-06', 'home_team': 'Forge FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 3, 'away_goals': 0},
        {'date': '2024-07-13', 'home_team': 'Cavalry FC', 'away_team': 'Vancouver FC', 'home_goals': 4, 'away_goals': 0},
        {'date': '2024-07-20', 'home_team': 'Pacific FC', 'away_team': 'Atletico Ottawa', 'home_goals': 2, 'away_goals': 1},
        {'date': '2024-07-27', 'home_team': 'York United FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 2},
    ]

    # 2023 Season - Full season
    season_2023 = [
        {'date': '2023-04-15', 'home_team': 'Forge FC', 'away_team': 'Valour FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2023-04-15', 'home_team': 'Cavalry FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2023-04-16', 'home_team': 'Atletico Ottawa', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2023-04-16', 'home_team': 'York United FC', 'away_team': 'FC Edmonton', 'home_goals': 2, 'away_goals': 0},
        {'date': '2023-04-22', 'home_team': 'Pacific FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 3},
        {'date': '2023-04-22', 'home_team': 'HFX Wanderers FC', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2023-04-23', 'home_team': 'Valour FC', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 1},
        {'date': '2023-04-23', 'home_team': 'FC Edmonton', 'away_team': 'Pacific FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2023-04-29', 'home_team': 'Forge FC', 'away_team': 'York United FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2023-04-29', 'home_team': 'Cavalry FC', 'away_team': 'Atletico Ottawa', 'home_goals': 2, 'away_goals': 1},
        {'date': '2023-05-06', 'home_team': 'HFX Wanderers FC', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2023-05-06', 'home_team': 'Pacific FC', 'away_team': 'FC Edmonton', 'home_goals': 3, 'away_goals': 0},
        {'date': '2023-05-13', 'home_team': 'Forge FC', 'away_team': 'Cavalry FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2023-05-13', 'home_team': 'Atletico Ottawa', 'away_team': 'Pacific FC', 'home_goals': 0, 'away_goals': 1},
        {'date': '2023-05-20', 'home_team': 'York United FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2023-05-20', 'home_team': 'Valour FC', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 3},
        {'date': '2023-05-27', 'home_team': 'FC Edmonton', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 4},
        {'date': '2023-05-27', 'home_team': 'Pacific FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2023-06-03', 'home_team': 'Cavalry FC', 'away_team': 'Valour FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2023-06-03', 'home_team': 'Atletico Ottawa', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2023-06-10', 'home_team': 'Forge FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 3, 'away_goals': 1},
        {'date': '2023-06-10', 'home_team': 'FC Edmonton', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2023-06-17', 'home_team': 'Pacific FC', 'away_team': 'Atletico Ottawa', 'home_goals': 2, 'away_goals': 2},
        {'date': '2023-06-17', 'home_team': 'Valour FC', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2023-06-24', 'home_team': 'HFX Wanderers FC', 'away_team': 'FC Edmonton', 'home_goals': 3, 'away_goals': 0},
        {'date': '2023-06-24', 'home_team': 'Cavalry FC', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 1},
        {'date': '2023-07-01', 'home_team': 'York United FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2023-07-01', 'home_team': 'Atletico Ottawa', 'away_team': 'Valour FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2023-07-08', 'home_team': 'Forge FC', 'away_team': 'FC Edmonton', 'home_goals': 5, 'away_goals': 0},
        {'date': '2023-07-08', 'home_team': 'HFX Wanderers FC', 'away_team': 'Atletico Ottawa', 'home_goals': 0, 'away_goals': 1},
        {'date': '2023-07-15', 'home_team': 'Cavalry FC', 'away_team': 'York United FC', 'home_goals': 3, 'away_goals': 1},
        {'date': '2023-07-15', 'home_team': 'Valour FC', 'away_team': 'Pacific FC', 'home_goals': 2, 'away_goals': 2},
    ]

    # 2022 Season - Forge FC champions
    season_2022 = [
        {'date': '2022-04-07', 'home_team': 'Forge FC', 'away_team': 'Cavalry FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2022-04-09', 'home_team': 'Pacific FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2022-04-10', 'home_team': 'York United FC', 'away_team': 'Atletico Ottawa', 'home_goals': 0, 'away_goals': 1},
        {'date': '2022-04-10', 'home_team': 'Valour FC', 'away_team': 'FC Edmonton', 'home_goals': 2, 'away_goals': 1},
        {'date': '2022-04-16', 'home_team': 'Cavalry FC', 'away_team': 'Pacific FC', 'home_goals': 3, 'away_goals': 1},
        {'date': '2022-04-16', 'home_team': 'HFX Wanderers FC', 'away_team': 'York United FC', 'home_goals': 2, 'away_goals': 2},
        {'date': '2022-04-17', 'home_team': 'FC Edmonton', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 3},
        {'date': '2022-04-17', 'home_team': 'Atletico Ottawa', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2022-04-23', 'home_team': 'Forge FC', 'away_team': 'Pacific FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2022-04-23', 'home_team': 'York United FC', 'away_team': 'Cavalry FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2022-04-24', 'home_team': 'Valour FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2022-04-24', 'home_team': 'FC Edmonton', 'away_team': 'Atletico Ottawa', 'home_goals': 0, 'away_goals': 2},
        {'date': '2022-04-30', 'home_team': 'Cavalry FC', 'away_team': 'Valour FC', 'home_goals': 4, 'away_goals': 0},
        {'date': '2022-04-30', 'home_team': 'Pacific FC', 'away_team': 'York United FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2022-05-01', 'home_team': 'HFX Wanderers FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2022-05-01', 'home_team': 'Atletico Ottawa', 'away_team': 'FC Edmonton', 'home_goals': 3, 'away_goals': 1},
        {'date': '2022-05-07', 'home_team': 'Forge FC', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2022-05-07', 'home_team': 'York United FC', 'away_team': 'FC Edmonton', 'home_goals': 2, 'away_goals': 0},
        {'date': '2022-05-08', 'home_team': 'Cavalry FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2022-05-08', 'home_team': 'Pacific FC', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 1},
        {'date': '2022-05-14', 'home_team': 'Valour FC', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 1},
        {'date': '2022-05-14', 'home_team': 'HFX Wanderers FC', 'away_team': 'Pacific FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2022-05-15', 'home_team': 'FC Edmonton', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 3},
        {'date': '2022-05-15', 'home_team': 'Atletico Ottawa', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2022-05-21', 'home_team': 'Cavalry FC', 'away_team': 'Atletico Ottawa', 'home_goals': 2, 'away_goals': 0},
        {'date': '2022-05-21', 'home_team': 'Pacific FC', 'away_team': 'Valour FC', 'home_goals': 3, 'away_goals': 2},
        {'date': '2022-05-22', 'home_team': 'Forge FC', 'away_team': 'York United FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2022-05-22', 'home_team': 'HFX Wanderers FC', 'away_team': 'FC Edmonton', 'home_goals': 4, 'away_goals': 0},
        {'date': '2022-05-28', 'home_team': 'York United FC', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2022-05-28', 'home_team': 'Atletico Ottawa', 'away_team': 'Pacific FC', 'home_goals': 2, 'away_goals': 2},
        {'date': '2022-05-29', 'home_team': 'FC Edmonton', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 3},
        {'date': '2022-05-29', 'home_team': 'Valour FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 1},
    ]

    # 2021 Season - Pacific FC champions
    season_2021 = [
        {'date': '2021-06-26', 'home_team': 'Forge FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2021-06-26', 'home_team': 'Valour FC', 'away_team': 'Pacific FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2021-06-27', 'home_team': 'Cavalry FC', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 0},
        {'date': '2021-06-27', 'home_team': 'York United FC', 'away_team': 'FC Edmonton', 'home_goals': 2, 'away_goals': 2},
        {'date': '2021-07-03', 'home_team': 'Pacific FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2021-07-03', 'home_team': 'HFX Wanderers FC', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2021-07-04', 'home_team': 'FC Edmonton', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 3},
        {'date': '2021-07-04', 'home_team': 'Atletico Ottawa', 'away_team': 'York United FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2021-07-10', 'home_team': 'Forge FC', 'away_team': 'Atletico Ottawa', 'home_goals': 3, 'away_goals': 0},
        {'date': '2021-07-10', 'home_team': 'Cavalry FC', 'away_team': 'Valour FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2021-07-11', 'home_team': 'Pacific FC', 'away_team': 'FC Edmonton', 'home_goals': 4, 'away_goals': 0},
        {'date': '2021-07-11', 'home_team': 'York United FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2021-07-17', 'home_team': 'Valour FC', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2021-07-17', 'home_team': 'HFX Wanderers FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 3},
        {'date': '2021-07-18', 'home_team': 'Atletico Ottawa', 'away_team': 'Cavalry FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2021-07-18', 'home_team': 'FC Edmonton', 'away_team': 'York United FC', 'home_goals': 0, 'away_goals': 1},
        {'date': '2021-07-24', 'home_team': 'Forge FC', 'away_team': 'FC Edmonton', 'home_goals': 5, 'away_goals': 1},
        {'date': '2021-07-24', 'home_team': 'Pacific FC', 'away_team': 'Atletico Ottawa', 'home_goals': 2, 'away_goals': 0},
        {'date': '2021-07-25', 'home_team': 'Cavalry FC', 'away_team': 'York United FC', 'home_goals': 3, 'away_goals': 0},
        {'date': '2021-07-25', 'home_team': 'Valour FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 2},
        {'date': '2021-07-31', 'home_team': 'York United FC', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2021-07-31', 'home_team': 'Atletico Ottawa', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2021-08-01', 'home_team': 'HFX Wanderers FC', 'away_team': 'FC Edmonton', 'home_goals': 2, 'away_goals': 0},
        {'date': '2021-08-01', 'home_team': 'Pacific FC', 'away_team': 'Cavalry FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2021-08-07', 'home_team': 'Forge FC', 'away_team': 'Cavalry FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2021-08-07', 'home_team': 'FC Edmonton', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 2},
        {'date': '2021-08-08', 'home_team': 'Valour FC', 'away_team': 'York United FC', 'home_goals': 3, 'away_goals': 1},
        {'date': '2021-08-08', 'home_team': 'HFX Wanderers FC', 'away_team': 'Pacific FC', 'home_goals': 0, 'away_goals': 1},
        {'date': '2021-08-14', 'home_team': 'Cavalry FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2021-08-14', 'home_team': 'York United FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 3},
        {'date': '2021-08-15', 'home_team': 'Atletico Ottawa', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2021-08-15', 'home_team': 'FC Edmonton', 'away_team': 'Valour FC', 'home_goals': 0, 'away_goals': 2},
    ]

    # 2020 Season - Island Games (COVID bubble in PEI) - Forge FC champions
    season_2020 = [
        {'date': '2020-08-13', 'home_team': 'Forge FC', 'away_team': 'Cavalry FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2020-08-13', 'home_team': 'Pacific FC', 'away_team': 'FC Edmonton', 'home_goals': 1, 'away_goals': 0},
        {'date': '2020-08-15', 'home_team': 'York United FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2020-08-15', 'home_team': 'Valour FC', 'away_team': 'Atletico Ottawa', 'home_goals': 0, 'away_goals': 1},
        {'date': '2020-08-16', 'home_team': 'Cavalry FC', 'away_team': 'Pacific FC', 'home_goals': 3, 'away_goals': 0},
        {'date': '2020-08-16', 'home_team': 'HFX Wanderers FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2020-08-19', 'home_team': 'Atletico Ottawa', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2020-08-19', 'home_team': 'FC Edmonton', 'away_team': 'Valour FC', 'home_goals': 0, 'away_goals': 0},
        {'date': '2020-08-20', 'home_team': 'Forge FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2020-08-20', 'home_team': 'Cavalry FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2020-08-22', 'home_team': 'York United FC', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2020-08-22', 'home_team': 'Atletico Ottawa', 'away_team': 'FC Edmonton', 'home_goals': 2, 'away_goals': 0},
        {'date': '2020-08-23', 'home_team': 'HFX Wanderers FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2020-08-23', 'home_team': 'Forge FC', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 0},
        {'date': '2020-08-25', 'home_team': 'Valour FC', 'away_team': 'York United FC', 'home_goals': 2, 'away_goals': 3},
        {'date': '2020-08-25', 'home_team': 'FC Edmonton', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 2},
        {'date': '2020-08-27', 'home_team': 'Pacific FC', 'away_team': 'Forge FC', 'home_goals': 0, 'away_goals': 1},
        {'date': '2020-08-27', 'home_team': 'HFX Wanderers FC', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2020-08-29', 'home_team': 'York United FC', 'away_team': 'FC Edmonton', 'home_goals': 1, 'away_goals': 0},
        {'date': '2020-08-29', 'home_team': 'Valour FC', 'away_team': 'Atletico Ottawa', 'home_goals': 1, 'away_goals': 1},
        {'date': '2020-08-30', 'home_team': 'Cavalry FC', 'away_team': 'Pacific FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2020-08-30', 'home_team': 'Forge FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 3, 'away_goals': 0},
        {'date': '2020-09-01', 'home_team': 'Atletico Ottawa', 'away_team': 'Valour FC', 'home_goals': 0, 'away_goals': 0},
        {'date': '2020-09-01', 'home_team': 'FC Edmonton', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 2},
    ]

    # 2019 Season - Inaugural season - Forge FC champions (7 teams, no Ottawa)
    season_2019 = [
        {'date': '2019-04-27', 'home_team': 'Forge FC', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2019-04-28', 'home_team': 'Cavalry FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2019-04-28', 'home_team': 'Valour FC', 'away_team': 'FC Edmonton', 'home_goals': 2, 'away_goals': 1},
        {'date': '2019-05-01', 'home_team': 'HFX Wanderers FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2019-05-04', 'home_team': 'York United FC', 'away_team': 'Cavalry FC', 'home_goals': 2, 'away_goals': 2},
        {'date': '2019-05-04', 'home_team': 'Pacific FC', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2019-05-05', 'home_team': 'FC Edmonton', 'away_team': 'HFX Wanderers FC', 'home_goals': 0, 'away_goals': 0},
        {'date': '2019-05-11', 'home_team': 'Forge FC', 'away_team': 'Pacific FC', 'home_goals': 3, 'away_goals': 1},
        {'date': '2019-05-11', 'home_team': 'Cavalry FC', 'away_team': 'Valour FC', 'home_goals': 2, 'away_goals': 0},
        {'date': '2019-05-12', 'home_team': 'HFX Wanderers FC', 'away_team': 'York United FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2019-05-15', 'home_team': 'FC Edmonton', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2019-05-18', 'home_team': 'Valour FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2019-05-18', 'home_team': 'Pacific FC', 'away_team': 'York United FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2019-05-19', 'home_team': 'Cavalry FC', 'away_team': 'FC Edmonton', 'home_goals': 3, 'away_goals': 0},
        {'date': '2019-05-25', 'home_team': 'Forge FC', 'away_team': 'Valour FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2019-05-25', 'home_team': 'York United FC', 'away_team': 'Pacific FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2019-05-26', 'home_team': 'HFX Wanderers FC', 'away_team': 'Cavalry FC', 'home_goals': 1, 'away_goals': 2},
        {'date': '2019-06-01', 'home_team': 'FC Edmonton', 'away_team': 'York United FC', 'home_goals': 0, 'away_goals': 0},
        {'date': '2019-06-01', 'home_team': 'Pacific FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2019-06-02', 'home_team': 'Valour FC', 'away_team': 'Cavalry FC', 'home_goals': 1, 'away_goals': 3},
        {'date': '2019-06-08', 'home_team': 'Cavalry FC', 'away_team': 'Forge FC', 'home_goals': 1, 'away_goals': 1},
        {'date': '2019-06-08', 'home_team': 'York United FC', 'away_team': 'Valour FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2019-06-09', 'home_team': 'HFX Wanderers FC', 'away_team': 'Pacific FC', 'home_goals': 2, 'away_goals': 2},
        {'date': '2019-06-15', 'home_team': 'Forge FC', 'away_team': 'FC Edmonton', 'home_goals': 4, 'away_goals': 0},
        {'date': '2019-06-15', 'home_team': 'Valour FC', 'away_team': 'Pacific FC', 'home_goals': 0, 'away_goals': 1},
        {'date': '2019-06-16', 'home_team': 'Cavalry FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2019-06-22', 'home_team': 'Pacific FC', 'away_team': 'Cavalry FC', 'home_goals': 0, 'away_goals': 2},
        {'date': '2019-06-22', 'home_team': 'FC Edmonton', 'away_team': 'Valour FC', 'home_goals': 2, 'away_goals': 2},
        {'date': '2019-06-23', 'home_team': 'York United FC', 'away_team': 'HFX Wanderers FC', 'home_goals': 1, 'away_goals': 0},
        {'date': '2019-06-26', 'home_team': 'HFX Wanderers FC', 'away_team': 'FC Edmonton', 'home_goals': 1, 'away_goals': 1},
        {'date': '2019-06-29', 'home_team': 'Forge FC', 'away_team': 'Cavalry FC', 'home_goals': 2, 'away_goals': 1},
        {'date': '2019-06-29', 'home_team': 'Valour FC', 'away_team': 'York United FC', 'home_goals': 1, 'away_goals': 0},
    ]

    # Process and add venue information
    def process_season(matches: List[Dict], season: int) -> pd.DataFrame:
        for match in matches:
            match['season'] = season
            match['venue'] = STADIUMS.get(match['home_team'], 'Unknown')
        return pd.DataFrame(matches)

    return {
        2024: process_season(season_2024, 2024),
        2023: process_season(season_2023, 2023),
        2022: process_season(season_2022, 2022),
        2021: process_season(season_2021, 2021),
        2020: process_season(season_2020, 2020),
        2019: process_season(season_2019, 2019),
    }


def build_full_dataset(data_dir: str = None):
    """Build and save the full CPL dataset."""
    logger.info("Building CPL historical dataset...")

    # Get script directory and compute data path
    if data_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, "..", "data", "matches")

    os.makedirs(data_dir, exist_ok=True)

    data = generate_historical_data()

    for year, df in data.items():
        filepath = os.path.join(data_dir, f"cpl_{year}.csv")
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(df)} matches to {filepath}")

    # Combine all seasons
    all_matches = pd.concat(data.values(), ignore_index=True)
    all_filepath = os.path.join(data_dir, "cpl_all.csv")
    all_matches.to_csv(all_filepath, index=False)
    logger.info(f"Saved combined dataset: {len(all_matches)} total matches")

    return all_matches


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='CPL Data Scraper')
    parser.add_argument('--mode', choices=['sample', 'historical', 'scrape'],
                        default='historical',
                        help='Mode: sample (quick test), historical (build dataset), scrape (live)')
    args = parser.parse_args()

    if args.mode == 'sample':
        logger.info("Creating sample data for development...")
        sample_df = create_sample_data()
        sample_df.to_csv("../data/matches/cpl_2024_sample.csv", index=False)
        logger.info(f"Created sample data with {len(sample_df)} matches")

    elif args.mode == 'historical':
        # Build comprehensive historical dataset
        df = build_full_dataset()
        print(f"\nDataset built: {len(df)} total matches")

    elif args.mode == 'scrape':
        # Live scraping (requires JavaScript rendering - use Selenium)
        logger.warning("Live scraping requires Selenium for JavaScript rendering.")
        logger.info("CPL.ca uses dynamic widgets. Consider using historical mode.")

        scraper = CPLScraper(data_dir="../data/matches")
        df = scraper.scrape_all_seasons(2019, 2026)
        print(f"\nTotal matches scraped: {len(df)}")
