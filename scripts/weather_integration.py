"""
CPL Weather Integration
Fetches weather data for CPL matches using OpenWeatherMap API.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import logging
import os
import json
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Weather conditions for a match."""
    temperature_c: float
    feels_like_c: float
    humidity: int
    wind_speed_kmh: float
    wind_direction: str
    conditions: str
    description: str
    precipitation_mm: float
    visibility_km: float
    pressure_hpa: int


# CPL Stadium Coordinates
CPL_STADIUMS = {
    'Forge FC': {
        'name': 'Tim Hortons Field',
        'city': 'Hamilton',
        'lat': 43.2557,
        'lon': -79.8711
    },
    'Cavalry FC': {
        'name': 'ATCO Field',
        'city': 'Calgary',
        'lat': 50.9977,
        'lon': -114.0672
    },
    'Pacific FC': {
        'name': 'Starlight Stadium',
        'city': 'Langford',
        'lat': 48.4494,
        'lon': -123.4879
    },
    'York United FC': {
        'name': 'York Lions Stadium',
        'city': 'Toronto',
        'lat': 43.7735,
        'lon': -79.4980
    },
    'Valour FC': {
        'name': 'IG Field',
        'city': 'Winnipeg',
        'lat': 49.8076,
        'lon': -97.1443
    },
    'HFX Wanderers FC': {
        'name': 'Wanderers Grounds',
        'city': 'Halifax',
        'lat': 44.6488,
        'lon': -63.5752
    },
    'FC Edmonton': {
        'name': 'Clarke Stadium',
        'city': 'Edmonton',
        'lat': 53.5720,
        'lon': -113.4564
    },
    'Vancouver FC': {
        'name': 'Willoughby Community Park',
        'city': 'Langley',
        'lat': 49.0171,
        'lon': -122.6593
    },
    'Atletico Ottawa': {
        'name': 'TD Place Stadium',
        'city': 'Ottawa',
        'lat': 45.3989,
        'lon': -75.6831
    }
}


class WeatherService:
    """Service for fetching weather data from OpenWeatherMap."""

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize weather service.

        Args:
            api_key: OpenWeatherMap API key. If not provided, looks for
                     OPENWEATHER_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
        if not self.api_key:
            logger.warning("No OpenWeatherMap API key provided. Set OPENWEATHER_API_KEY env var.")

    def get_current_weather(self, lat: float, lon: float) -> Optional[WeatherData]:
        """Get current weather for coordinates."""
        if not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return self._parse_weather_response(data)

        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return None

    def get_forecast(self, lat: float, lon: float, target_date: datetime) -> Optional[WeatherData]:
        """
        Get weather forecast for a specific date.

        Args:
            lat: Latitude
            lon: Longitude
            target_date: Date to get forecast for

        Returns:
            WeatherData for the target date, or None if not available
        """
        if not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Find forecast closest to target date
            best_forecast = None
            min_diff = float('inf')

            for item in data.get('list', []):
                forecast_time = datetime.fromtimestamp(item['dt'])
                diff = abs((forecast_time - target_date).total_seconds())

                if diff < min_diff:
                    min_diff = diff
                    best_forecast = item

            if best_forecast:
                return self._parse_forecast_item(best_forecast)

            return None

        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            return None

    def _parse_weather_response(self, data: dict) -> WeatherData:
        """Parse current weather API response."""
        main = data.get('main', {})
        wind = data.get('wind', {})
        weather = data.get('weather', [{}])[0]

        # Convert wind direction from degrees to cardinal
        wind_deg = wind.get('deg', 0)
        wind_dir = self._degrees_to_cardinal(wind_deg)

        # Get rain/snow if present
        rain = data.get('rain', {}).get('1h', 0)
        snow = data.get('snow', {}).get('1h', 0)

        return WeatherData(
            temperature_c=main.get('temp', 0),
            feels_like_c=main.get('feels_like', 0),
            humidity=main.get('humidity', 0),
            wind_speed_kmh=wind.get('speed', 0) * 3.6,  # m/s to km/h
            wind_direction=wind_dir,
            conditions=weather.get('main', 'Unknown'),
            description=weather.get('description', ''),
            precipitation_mm=rain + snow,
            visibility_km=data.get('visibility', 10000) / 1000,
            pressure_hpa=main.get('pressure', 0)
        )

    def _parse_forecast_item(self, item: dict) -> WeatherData:
        """Parse a single forecast item."""
        main = item.get('main', {})
        wind = item.get('wind', {})
        weather = item.get('weather', [{}])[0]

        wind_deg = wind.get('deg', 0)
        wind_dir = self._degrees_to_cardinal(wind_deg)

        rain = item.get('rain', {}).get('3h', 0)
        snow = item.get('snow', {}).get('3h', 0)

        return WeatherData(
            temperature_c=main.get('temp', 0),
            feels_like_c=main.get('feels_like', 0),
            humidity=main.get('humidity', 0),
            wind_speed_kmh=wind.get('speed', 0) * 3.6,
            wind_direction=wind_dir,
            conditions=weather.get('main', 'Unknown'),
            description=weather.get('description', ''),
            precipitation_mm=rain + snow,
            visibility_km=item.get('visibility', 10000) / 1000,
            pressure_hpa=main.get('pressure', 0)
        )

    def _degrees_to_cardinal(self, degrees: float) -> str:
        """Convert wind direction from degrees to cardinal direction."""
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                      'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        idx = round(degrees / 22.5) % 16
        return directions[idx]


class CPLWeatherTracker:
    """Track weather for CPL matches."""

    def __init__(self, api_key: Optional[str] = None):
        self.weather_service = WeatherService(api_key)

    def get_stadium_coords(self, home_team: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a team's home stadium."""
        stadium = CPL_STADIUMS.get(home_team)
        if stadium:
            return (stadium['lat'], stadium['lon'])
        return None

    def get_match_weather(self, home_team: str,
                          match_datetime: datetime) -> Optional[WeatherData]:
        """
        Get weather for a CPL match.

        Args:
            home_team: Name of home team
            match_datetime: Date and time of match

        Returns:
            WeatherData or None if unavailable
        """
        coords = self.get_stadium_coords(home_team)
        if not coords:
            logger.warning(f"Unknown team: {home_team}")
            return None

        lat, lon = coords

        # Use current weather if match is within 3 hours
        now = datetime.now()
        if abs((match_datetime - now).total_seconds()) < 3 * 3600:
            return self.weather_service.get_current_weather(lat, lon)

        # Use forecast for future matches
        return self.weather_service.get_forecast(lat, lon, match_datetime)

    def enrich_matches_with_weather(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """
        Add weather data to a DataFrame of matches.

        Args:
            matches_df: DataFrame with 'home_team', 'date', and optionally 'kickoff_time'

        Returns:
            DataFrame with weather columns added
        """
        weather_data = []

        for _, row in matches_df.iterrows():
            home_team = row['home_team']

            # Parse date/time
            if 'kickoff_time' in row and pd.notna(row['kickoff_time']):
                match_dt = datetime.strptime(
                    f"{row['date']} {row['kickoff_time']}",
                    '%Y-%m-%d %H:%M'
                )
            else:
                # Default to 7 PM local time
                match_dt = datetime.strptime(row['date'], '%Y-%m-%d').replace(hour=19)

            weather = self.get_match_weather(home_team, match_dt)

            if weather:
                weather_data.append({
                    'weather_temp_c': weather.temperature_c,
                    'weather_feels_like_c': weather.feels_like_c,
                    'weather_humidity': weather.humidity,
                    'weather_wind_kmh': weather.wind_speed_kmh,
                    'weather_wind_dir': weather.wind_direction,
                    'weather_conditions': weather.conditions,
                    'weather_precipitation_mm': weather.precipitation_mm,
                })
            else:
                weather_data.append({
                    'weather_temp_c': None,
                    'weather_feels_like_c': None,
                    'weather_humidity': None,
                    'weather_wind_kmh': None,
                    'weather_wind_dir': None,
                    'weather_conditions': None,
                    'weather_precipitation_mm': None,
                })

        weather_df = pd.DataFrame(weather_data)
        return pd.concat([matches_df.reset_index(drop=True), weather_df], axis=1)

    def get_historical_weather(self, home_team: str, date: str) -> Optional[Dict]:
        """
        Get historical weather for a past match.
        Requires OpenWeatherMap One Call API (paid tier).

        For free tier, consider using:
        - Visual Crossing API
        - World Weather Online
        - Meteostat
        """
        # Placeholder for historical weather API
        logger.warning("Historical weather requires paid API tier")
        return None


def calculate_travel_distance(home_team: str, away_team: str) -> Optional[float]:
    """
    Calculate straight-line distance between two teams' stadiums.

    Args:
        home_team: Home team name
        away_team: Away team name

    Returns:
        Distance in kilometers
    """
    from math import radians, sin, cos, sqrt, atan2

    home = CPL_STADIUMS.get(home_team)
    away = CPL_STADIUMS.get(away_team)

    if not home or not away:
        return None

    # Haversine formula
    R = 6371  # Earth's radius in km

    lat1, lon1 = radians(home['lat']), radians(home['lon'])
    lat2, lon2 = radians(away['lat']), radians(away['lon'])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c


def get_all_travel_distances() -> pd.DataFrame:
    """Generate travel distance matrix for all CPL teams."""
    teams = list(CPL_STADIUMS.keys())
    distances = []

    for home in teams:
        for away in teams:
            if home != away:
                dist = calculate_travel_distance(home, away)
                distances.append({
                    'home_team': home,
                    'away_team': away,
                    'distance_km': round(dist, 1) if dist else None
                })

    return pd.DataFrame(distances)


if __name__ == "__main__":
    # Example usage
    print("CPL Stadium Travel Distances")
    print("=" * 50)

    distances = get_all_travel_distances()
    print(distances.to_string(index=False))

    # Save to CSV
    distances.to_csv("../data/travel_distances.csv", index=False)
    print("\nSaved to data/travel_distances.csv")

    # Weather example (requires API key)
    tracker = CPLWeatherTracker()
    coords = tracker.get_stadium_coords('Forge FC')
    print(f"\nForge FC stadium coordinates: {coords}")
