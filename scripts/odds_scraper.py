"""
CPL Historical Closing Odds Scraper

Scrapes closing odds from Odds Portal and BetExplorer for Canadian Premier League matches.
Handles anti-scraping measures with delays, rotating user agents, and optional Selenium support.

Usage:
    # Scrape all seasons from Odds Portal
    python scripts/odds_scraper.py --source oddsportal --seasons 2019 2020 2021 2022 2023 2024 2025

    # Scrape specific season from BetExplorer
    python scripts/odds_scraper.py --source betexplorer --seasons 2024

    # Use Selenium for JavaScript-rendered content
    python scripts/odds_scraper.py --source oddsportal --seasons 2024 --use-selenium

Requirements:
    pip install requests beautifulsoup4 selenium webdriver-manager pandas
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Optional Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ClosingOdds:
    """Represents closing odds for a single match from one bookmaker."""
    match_id: str
    date: str
    home_team: str
    away_team: str
    bookmaker: str
    closing_home: float
    closing_draw: float
    closing_away: float
    closing_over_2_5: Optional[float] = None
    closing_under_2_5: Optional[float] = None
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to CSV row format."""
        return {
            'match_id': self.match_id,
            'date': self.date,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'bookmaker': self.bookmaker,
            'closing_home': self.closing_home,
            'closing_draw': self.closing_draw,
            'closing_away': self.closing_away,
            'closing_over_2.5': self.closing_over_2_5 or '',
            'closing_under_2.5': self.closing_under_2_5 or '',
            'scraped_at': self.scraped_at
        }


@dataclass
class Match:
    """Represents a CPL match."""
    date: str
    home_team: str
    away_team: str
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    match_url: Optional[str] = None

    @property
    def match_id(self) -> str:
        """Generate unique match ID."""
        home_clean = self._clean_team_name(self.home_team)
        away_clean = self._clean_team_name(self.away_team)
        date_clean = self.date.replace('-', '')
        return f"{home_clean}_vs_{away_clean}_{date_clean}"

    @staticmethod
    def _clean_team_name(name: str) -> str:
        """Clean team name for use in match ID."""
        name = name.lower()
        name = re.sub(r'\s*(fc|united)\s*', '', name)
        name = re.sub(r'[^a-z0-9]', '_', name)
        name = re.sub(r'_+', '_', name)
        return name.strip('_')


# =============================================================================
# Anti-Scraping Utilities
# =============================================================================

class AntiScrapingHandler:
    """Handles anti-scraping measures."""

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    ]

    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_count = 0

    def get_headers(self) -> Dict[str, str]:
        """Get randomized request headers."""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

    def wait(self):
        """Wait a random amount of time between requests."""
        delay = random.uniform(self.min_delay, self.max_delay)

        # Add extra delay every 10 requests
        self.request_count += 1
        if self.request_count % 10 == 0:
            delay += random.uniform(3.0, 7.0)
            logger.info(f"Extended delay after {self.request_count} requests")

        logger.debug(f"Waiting {delay:.2f}s before next request")
        time.sleep(delay)


# =============================================================================
# Base Scraper
# =============================================================================

class BaseScraper(ABC):
    """Abstract base class for odds scrapers."""

    def __init__(self, use_selenium: bool = False, headless: bool = True):
        self.use_selenium = use_selenium
        self.headless = headless
        self.anti_scraping = AntiScrapingHandler()
        self.session = requests.Session()
        self.driver = None

        if use_selenium:
            self._init_selenium()

    def _init_selenium(self):
        """Initialize Selenium WebDriver."""
        if not SELENIUM_AVAILABLE:
            raise ImportError(
                "Selenium not installed. Run: pip install selenium webdriver-manager"
            )

        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--user-agent={random.choice(self.anti_scraping.USER_AGENTS)}')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(30)

    def fetch_page(self, url: str) -> str:
        """Fetch page content with anti-scraping measures."""
        self.anti_scraping.wait()

        if self.use_selenium and self.driver:
            logger.info(f"Fetching (Selenium): {url}")
            self.driver.get(url)
            time.sleep(2)  # Wait for JS to render
            return self.driver.page_source
        else:
            logger.info(f"Fetching (requests): {url}")
            response = self.session.get(
                url,
                headers=self.anti_scraping.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.text

    def close(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
        self.session.close()

    @abstractmethod
    def get_results_url(self, season: int) -> str:
        """Get URL for season results page."""
        pass

    @abstractmethod
    def parse_results_page(self, html: str, season: int) -> List[Match]:
        """Parse results page to extract matches."""
        pass

    @abstractmethod
    def get_match_odds_url(self, match: Match) -> Optional[str]:
        """Get URL for individual match odds page."""
        pass

    @abstractmethod
    def parse_match_odds(self, html: str, match: Match) -> List[ClosingOdds]:
        """Parse match page to extract closing odds."""
        pass

    def scrape_season(self, season: int) -> List[ClosingOdds]:
        """Scrape all closing odds for a season."""
        all_odds = []

        # Get results page
        results_url = self.get_results_url(season)
        logger.info(f"Scraping season {season} from {results_url}")

        try:
            html = self.fetch_page(results_url)
            matches = self.parse_results_page(html, season)
            logger.info(f"Found {len(matches)} matches for season {season}")

            # Scrape each match
            for i, match in enumerate(matches):
                logger.info(f"Processing match {i+1}/{len(matches)}: {match.home_team} vs {match.away_team}")

                match_url = self.get_match_odds_url(match)
                if not match_url:
                    logger.warning(f"No URL for match: {match.match_id}")
                    continue

                try:
                    match_html = self.fetch_page(match_url)
                    odds = self.parse_match_odds(match_html, match)
                    all_odds.extend(odds)
                    logger.info(f"  Found {len(odds)} odds records")
                except Exception as e:
                    logger.error(f"  Error scraping match odds: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error scraping season {season}: {e}")

        return all_odds


# =============================================================================
# Odds Portal Scraper
# =============================================================================

class OddsPortalScraper(BaseScraper):
    """Scraper for oddsportal.com"""

    BASE_URL = "https://www.oddsportal.com"
    CPL_PATH = "/football/canada/canadian-premier-league"

    # Team name mapping (Odds Portal -> Standard)
    TEAM_MAPPING = {
        'forge': 'Forge FC',
        'forge fc': 'Forge FC',
        'cavalry': 'Cavalry FC',
        'cavalry fc': 'Cavalry FC',
        'pacific': 'Pacific FC',
        'pacific fc': 'Pacific FC',
        'valour': 'Valour FC',
        'valour fc': 'Valour FC',
        'york united': 'York United FC',
        'york utd': 'York United FC',
        'york': 'York United FC',
        'hfx wanderers': 'HFX Wanderers FC',
        'halifax': 'HFX Wanderers FC',
        'hfx': 'HFX Wanderers FC',
        'atletico ottawa': 'Atletico Ottawa',
        'ottawa': 'Atletico Ottawa',
        'atl. ottawa': 'Atletico Ottawa',
        'fc edmonton': 'FC Edmonton',
        'edmonton': 'FC Edmonton',
        'vancouver': 'Vancouver FC',
        'vancouver fc': 'Vancouver FC',
    }

    # Bookmaker mapping (Odds Portal -> Standard)
    BOOKMAKER_MAPPING = {
        'bet365': 'bet365',
        '365': 'bet365',
        'sports interaction': 'sportsinteraction',
        'sportsinteraction': 'sportsinteraction',
        'pinnacle': 'pinnacle',
        'betway': 'betway',
        'unibet': 'unibet',
        'william hill': 'williamhill',
        'bwin': 'bwin',
        '1xbet': '1xbet',
        'betfair': 'betfair',
    }

    def normalize_team_name(self, name: str) -> str:
        """Normalize team name to standard format."""
        name_lower = name.lower().strip()
        return self.TEAM_MAPPING.get(name_lower, name)

    def normalize_bookmaker(self, name: str) -> Optional[str]:
        """Normalize bookmaker name, return None if not in our list."""
        name_lower = name.lower().strip()
        return self.BOOKMAKER_MAPPING.get(name_lower)

    def get_results_url(self, season: int) -> str:
        """Get URL for season results page."""
        if season == datetime.now().year:
            return f"{self.BASE_URL}{self.CPL_PATH}/results/"
        else:
            return f"{self.BASE_URL}{self.CPL_PATH}-{season}/results/"

    def parse_results_page(self, html: str, season: int) -> List[Match]:
        """Parse results page to extract matches."""
        soup = BeautifulSoup(html, 'html.parser')
        matches = []

        # Find all match rows
        # Odds Portal structure varies, try multiple selectors
        match_rows = soup.select('div.eventRow, tr.deactivate, div[class*="event"]')

        for row in match_rows:
            try:
                match = self._parse_match_row(row, season)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.debug(f"Error parsing row: {e}")
                continue

        return matches

    def _parse_match_row(self, row, season: int) -> Optional[Match]:
        """Parse a single match row."""
        # Try to find team names
        teams = row.select('a[href*="/football/"] span, .participant-name, td.name')

        if len(teams) < 2:
            # Alternative: look for text with " - " separator
            text = row.get_text()
            if ' - ' in text:
                parts = text.split(' - ')
                if len(parts) >= 2:
                    home_team = self.normalize_team_name(parts[0].strip())
                    away_team = self.normalize_team_name(parts[1].split()[0].strip())
            else:
                return None
        else:
            home_team = self.normalize_team_name(teams[0].get_text().strip())
            away_team = self.normalize_team_name(teams[1].get_text().strip())

        # Try to find date
        date_elem = row.select_one('td.date, span.date, [class*="date"]')
        if date_elem:
            date_str = self._parse_date(date_elem.get_text().strip(), season)
        else:
            date_str = f"{season}-01-01"  # Fallback

        # Try to find match URL
        link = row.select_one('a[href*="/football/"]')
        match_url = urljoin(self.BASE_URL, link['href']) if link else None

        return Match(
            date=date_str,
            home_team=home_team,
            away_team=away_team,
            match_url=match_url
        )

    def _parse_date(self, date_str: str, season: int) -> str:
        """Parse date string to YYYY-MM-DD format."""
        # Try various formats
        formats = [
            '%d %b %Y',  # 15 Apr 2024
            '%d.%m.%Y',  # 15.04.2024
            '%d/%m/%Y',  # 15/04/2024
            '%Y-%m-%d',  # 2024-04-15
            '%d %B %Y',  # 15 April 2024
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If no year in string, assume current season
        for fmt in ['%d %b', '%d.%m', '%d/%m']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return f"{season}-{dt.month:02d}-{dt.day:02d}"
            except ValueError:
                continue

        return f"{season}-01-01"  # Fallback

    def get_match_odds_url(self, match: Match) -> Optional[str]:
        """Get URL for individual match odds page."""
        return match.match_url

    def parse_match_odds(self, html: str, match: Match) -> List[ClosingOdds]:
        """Parse match page to extract closing odds."""
        soup = BeautifulSoup(html, 'html.parser')
        odds_list = []

        # Find odds table
        odds_rows = soup.select('tr[data-bid], div.odds-row, tr.lo')

        for row in odds_rows:
            try:
                bookmaker_elem = row.select_one('a.name, td.bookmaker, span.bookmaker')
                if not bookmaker_elem:
                    continue

                bookmaker_raw = bookmaker_elem.get_text().strip()
                bookmaker = self.normalize_bookmaker(bookmaker_raw)

                # Only keep bookmakers we care about
                if not bookmaker or bookmaker not in ['bet365', 'sportsinteraction']:
                    continue

                # Find odds values
                odds_cells = row.select('td.odds, span.odds-value, a[data-odd]')

                if len(odds_cells) >= 3:
                    home_odds = self._parse_odds(odds_cells[0].get_text())
                    draw_odds = self._parse_odds(odds_cells[1].get_text())
                    away_odds = self._parse_odds(odds_cells[2].get_text())

                    if home_odds and draw_odds and away_odds:
                        odds_list.append(ClosingOdds(
                            match_id=match.match_id,
                            date=match.date,
                            home_team=match.home_team,
                            away_team=match.away_team,
                            bookmaker=bookmaker,
                            closing_home=home_odds,
                            closing_draw=draw_odds,
                            closing_away=away_odds
                        ))

            except Exception as e:
                logger.debug(f"Error parsing odds row: {e}")
                continue

        return odds_list

    def _parse_odds(self, odds_str: str) -> Optional[float]:
        """Parse odds string to float."""
        try:
            odds_str = odds_str.strip()
            odds_str = re.sub(r'[^\d.]', '', odds_str)
            return float(odds_str)
        except (ValueError, AttributeError):
            return None


# =============================================================================
# BetExplorer Scraper
# =============================================================================

class BetExplorerScraper(BaseScraper):
    """Scraper for betexplorer.com"""

    BASE_URL = "https://www.betexplorer.com"
    CPL_PATH = "/football/canada/canadian-premier-league"

    # Team name mapping
    TEAM_MAPPING = {
        'forge': 'Forge FC',
        'forge fc': 'Forge FC',
        'cavalry': 'Cavalry FC',
        'cavalry fc': 'Cavalry FC',
        'pacific': 'Pacific FC',
        'pacific fc': 'Pacific FC',
        'valour': 'Valour FC',
        'valour fc': 'Valour FC',
        'york united': 'York United FC',
        'york utd': 'York United FC',
        'york': 'York United FC',
        'hfx wanderers': 'HFX Wanderers FC',
        'hfx': 'HFX Wanderers FC',
        'atl. ottawa': 'Atletico Ottawa',
        'atletico ottawa': 'Atletico Ottawa',
        'ottawa': 'Atletico Ottawa',
        'fc edmonton': 'FC Edmonton',
        'edmonton': 'FC Edmonton',
        'vancouver': 'Vancouver FC',
        'vancouver fc': 'Vancouver FC',
        'inter toronto': 'Inter Toronto FC',
    }

    def normalize_team_name(self, name: str) -> str:
        name_lower = name.lower().strip()
        return self.TEAM_MAPPING.get(name_lower, name)

    def get_results_url(self, season: int) -> str:
        if season == datetime.now().year:
            return f"{self.BASE_URL}{self.CPL_PATH}/results/"
        else:
            return f"{self.BASE_URL}{self.CPL_PATH}-{season}/results/"

    def parse_results_page(self, html: str, season: int) -> List[Match]:
        soup = BeautifulSoup(html, 'html.parser')
        matches = []

        # Find the main results table
        table = soup.select_one('table.table-main')
        if not table:
            logger.warning("Could not find main table")
            return matches

        # Find all match rows (tr with match links)
        for row in table.select('tr'):
            try:
                # Skip header rows
                if row.find('th'):
                    continue

                # Find the match link
                match_link = row.select_one('a.in-match')
                if not match_link:
                    continue

                # Extract team names from spans
                spans = match_link.select('span')
                if len(spans) < 2:
                    continue

                home_team = self.normalize_team_name(spans[0].get_text().strip())
                away_team = self.normalize_team_name(spans[1].get_text().strip())

                # Extract date from last cell
                date_cell = row.select_one('td.h-text-right')
                date_str = f"{season}-01-01"
                if date_cell:
                    date_str = self._parse_date(date_cell.get_text().strip(), season)

                # Get match URL
                match_url = urljoin(self.BASE_URL, match_link['href']) if match_link.get('href') else None

                # Extract odds directly from this row (average closing odds)
                odds_cells = row.select('td.table-main__odds')
                home_odds = draw_odds = away_odds = None

                if len(odds_cells) >= 3:
                    home_odds = self._parse_odds(odds_cells[0].get_text())
                    draw_odds = self._parse_odds(odds_cells[1].get_text())
                    away_odds = self._parse_odds(odds_cells[2].get_text())

                match = Match(
                    date=date_str,
                    home_team=home_team,
                    away_team=away_team,
                    match_url=match_url
                )

                # Store odds directly if we have them
                if home_odds and draw_odds and away_odds:
                    match._odds = (home_odds, draw_odds, away_odds)

                matches.append(match)
                logger.debug(f"Found match: {home_team} vs {away_team} on {date_str}")

            except Exception as e:
                logger.debug(f"Error parsing row: {e}")
                continue

        return matches

    def _parse_date(self, date_str: str, season: int) -> str:
        """Parse BetExplorer date format (DD.MM.YYYY)"""
        date_str = date_str.strip()

        # Try DD.MM.YYYY format
        try:
            dt = datetime.strptime(date_str, '%d.%m.%Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            pass

        # Try DD.MM. format (year implied)
        try:
            dt = datetime.strptime(date_str, '%d.%m.')
            return f"{season}-{dt.month:02d}-{dt.day:02d}"
        except ValueError:
            pass

        return f"{season}-01-01"

    def get_match_odds_url(self, match: Match) -> Optional[str]:
        return match.match_url

    def parse_match_odds(self, html: str, match: Match) -> List[ClosingOdds]:
        """Parse individual match page to get bookmaker-specific odds."""
        # If we already have odds from the results page, use those
        if hasattr(match, '_odds') and match._odds:
            home_odds, draw_odds, away_odds = match._odds
            return [ClosingOdds(
                match_id=match.match_id,
                date=match.date,
                home_team=match.home_team,
                away_team=match.away_team,
                bookmaker='average',  # BetExplorer shows average odds on results page
                closing_home=home_odds,
                closing_draw=draw_odds,
                closing_away=away_odds
            )]

        # Otherwise try to parse the match page for bookmaker-specific odds
        soup = BeautifulSoup(html, 'html.parser')
        odds_list = []

        # Look for odds table on match page
        odds_table = soup.select_one('table.table-main, #odds-data-table')
        if not odds_table:
            return odds_list

        for row in odds_table.select('tr'):
            try:
                # Find bookmaker name
                bookmaker_elem = row.select_one('td.h-text-left a, a.in-bookmaker-logo-link, td a[href*="/bookmaker/"]')
                if not bookmaker_elem:
                    continue

                bookmaker_raw = bookmaker_elem.get('title', '') or bookmaker_elem.get_text()
                bookmaker_raw = bookmaker_raw.lower().strip()

                # Map to our standard bookmaker names
                if 'bet365' in bookmaker_raw or '365' in bookmaker_raw:
                    bookmaker = 'bet365'
                elif 'sports interaction' in bookmaker_raw or 'sportsint' in bookmaker_raw:
                    bookmaker = 'sportsinteraction'
                else:
                    continue  # Skip other bookmakers

                odds_cells = row.select('td.table-main__odds, td[data-odd]')

                if len(odds_cells) >= 3:
                    home_odds = self._parse_odds(odds_cells[0].get_text())
                    draw_odds = self._parse_odds(odds_cells[1].get_text())
                    away_odds = self._parse_odds(odds_cells[2].get_text())

                    if home_odds and draw_odds and away_odds:
                        odds_list.append(ClosingOdds(
                            match_id=match.match_id,
                            date=match.date,
                            home_team=match.home_team,
                            away_team=match.away_team,
                            bookmaker=bookmaker,
                            closing_home=home_odds,
                            closing_draw=draw_odds,
                            closing_away=away_odds
                        ))

            except Exception as e:
                logger.debug(f"Error parsing odds row: {e}")
                continue

        return odds_list

    def _parse_odds(self, odds_str: str) -> Optional[float]:
        try:
            odds_str = re.sub(r'[^\d.]', '', odds_str.strip())
            if odds_str:
                return float(odds_str)
        except (ValueError, AttributeError):
            pass
        return None

    def scrape_season(self, season: int) -> List[ClosingOdds]:
        """Override to get odds directly from results page, handling pagination."""
        all_odds = []
        all_matches = []

        results_url = self.get_results_url(season)
        logger.info(f"Scraping season {season} from {results_url}")

        try:
            # Use Selenium to load all results if available
            if self.use_selenium and self.driver:
                html = self._fetch_all_results_selenium(results_url)
            else:
                html = self.fetch_page(results_url)

            matches = self.parse_results_page(html, season)
            logger.info(f"Found {len(matches)} matches for season {season}")

            # Get odds from results page
            for match in matches:
                if hasattr(match, '_odds') and match._odds:
                    home_odds, draw_odds, away_odds = match._odds
                    all_odds.append(ClosingOdds(
                        match_id=match.match_id,
                        date=match.date,
                        home_team=match.home_team,
                        away_team=match.away_team,
                        bookmaker='betexplorer_avg',
                        closing_home=home_odds,
                        closing_draw=draw_odds,
                        closing_away=away_odds
                    ))
                    logger.debug(f"  Got odds for {match.home_team} vs {match.away_team}")

        except Exception as e:
            logger.error(f"Error scraping season {season}: {e}")

        return all_odds

    def _fetch_all_results_selenium(self, url: str) -> str:
        """Use Selenium to load all results by scrolling/clicking 'show more'."""
        logger.info(f"Fetching all results with Selenium: {url}")
        self.anti_scraping.wait()

        self.driver.get(url)
        time.sleep(3)  # Initial wait

        # Try to load all results by clicking "Show more" or scrolling
        max_attempts = 20
        last_count = 0

        for attempt in range(max_attempts):
            # Get current match count
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            current_count = len(soup.select('table.table-main tr a.in-match'))

            if current_count == last_count and attempt > 0:
                logger.info(f"No new matches loaded after attempt {attempt}")
                break

            last_count = current_count
            logger.debug(f"Attempt {attempt + 1}: Found {current_count} matches so far")

            # Try to find and click "Show more" button
            try:
                # Look for various "show more" elements
                show_more_selectors = [
                    'a.show-more',
                    'button.show-more',
                    'a[class*="show-more"]',
                    'a[class*="load-more"]',
                    '#show-more-results',
                    '.js-show-more',
                ]

                clicked = False
                for selector in show_more_selectors:
                    try:
                        from selenium.webdriver.common.by import By
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                elem.click()
                                clicked = True
                                time.sleep(2)
                                break
                        if clicked:
                            break
                    except:
                        continue

                if not clicked:
                    # Try scrolling to load more
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.5)

            except Exception as e:
                logger.debug(f"Could not click show more: {e}")
                break

        return self.driver.page_source


# =============================================================================
# CSV Export
# =============================================================================

class OddsExporter:
    """Export closing odds to CSV files."""

    CSV_HEADERS = [
        'match_id', 'date', 'home_team', 'away_team', 'bookmaker',
        'closing_home', 'closing_draw', 'closing_away',
        'closing_over_2.5', 'closing_under_2.5', 'scraped_at'
    ]

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_season(self, season: int, odds: List[ClosingOdds], append: bool = False):
        """Export odds for a single season to CSV."""
        filename = self.output_dir / f"cpl_{season}_closing_odds.csv"
        mode = 'a' if append and filename.exists() else 'w'
        write_header = mode == 'w' or not filename.exists()

        with open(filename, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)

            if write_header:
                writer.writeheader()

            for odd in odds:
                writer.writerow(odd.to_csv_row())

        logger.info(f"Exported {len(odds)} odds to {filename}")

    def export_all(self, odds_by_season: Dict[int, List[ClosingOdds]]):
        """Export all seasons to separate CSV files."""
        for season, odds in odds_by_season.items():
            self.export_season(season, odds)


# =============================================================================
# Main Scraper Manager
# =============================================================================

class CPLOddsScraper:
    """Main class for scraping CPL closing odds."""

    SCRAPERS = {
        'oddsportal': OddsPortalScraper,
        'betexplorer': BetExplorerScraper,
    }

    def __init__(
        self,
        source: str = 'oddsportal',
        use_selenium: bool = False,
        output_dir: Optional[Path] = None
    ):
        if source not in self.SCRAPERS:
            raise ValueError(f"Unknown source: {source}. Available: {list(self.SCRAPERS.keys())}")

        self.source = source
        self.scraper = self.SCRAPERS[source](use_selenium=use_selenium)
        self.output_dir = output_dir or Path(__file__).parent.parent / 'data' / 'closing_odds'
        self.exporter = OddsExporter(self.output_dir)

    def scrape_seasons(self, seasons: List[int]) -> Dict[int, List[ClosingOdds]]:
        """Scrape multiple seasons."""
        all_odds = {}

        try:
            for season in seasons:
                logger.info(f"\n{'='*60}")
                logger.info(f"Scraping season {season}")
                logger.info(f"{'='*60}")

                odds = self.scraper.scrape_season(season)
                all_odds[season] = odds

                # Export after each season (in case of failure)
                if odds:
                    self.exporter.export_season(season, odds)

                logger.info(f"Season {season}: Found {len(odds)} closing odds records")

        finally:
            self.scraper.close()

        return all_odds

    def scrape_and_export(self, seasons: List[int]) -> Dict[int, int]:
        """Scrape seasons and return count of records per season."""
        odds = self.scrape_seasons(seasons)
        return {season: len(records) for season, records in odds.items()}


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Scrape CPL closing odds from Odds Portal or BetExplorer'
    )
    parser.add_argument(
        '--source',
        choices=['oddsportal', 'betexplorer'],
        default='oddsportal',
        help='Source website to scrape (default: oddsportal)'
    )
    parser.add_argument(
        '--seasons',
        type=int,
        nargs='+',
        default=[2024],
        help='Seasons to scrape (default: 2024)'
    )
    parser.add_argument(
        '--use-selenium',
        action='store_true',
        help='Use Selenium for JavaScript-rendered content'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory for CSV files'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"CPL Closing Odds Scraper")
    logger.info(f"Source: {args.source}")
    logger.info(f"Seasons: {args.seasons}")
    logger.info(f"Selenium: {args.use_selenium}")

    scraper = CPLOddsScraper(
        source=args.source,
        use_selenium=args.use_selenium,
        output_dir=args.output_dir
    )

    results = scraper.scrape_and_export(args.seasons)

    logger.info("\n" + "="*60)
    logger.info("SCRAPING COMPLETE")
    logger.info("="*60)
    for season, count in results.items():
        logger.info(f"Season {season}: {count} records")
    logger.info(f"Total: {sum(results.values())} records")


if __name__ == '__main__':
    main()
