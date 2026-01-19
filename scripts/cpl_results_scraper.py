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
        # Add more sample matches...
    ]

    return pd.DataFrame(sample_matches)


if __name__ == "__main__":
    # Initialize scraper
    scraper = CPLScraper(data_dir="../data/matches")

    # Create sample data for development
    logger.info("Creating sample data for development...")
    sample_df = create_sample_data()
    sample_df.to_csv("../data/matches/cpl_2024_sample.csv", index=False)
    logger.info(f"Created sample data with {len(sample_df)} matches")

    # Uncomment to scrape real data:
    # df = scraper.scrape_all_seasons(2019, 2026)
    # print(f"\nTotal matches scraped: {len(df)}")
