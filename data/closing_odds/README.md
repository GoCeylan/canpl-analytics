# CPL Closing Odds Data

> **⚠️ PREVIEW - LIMITED DATA AVAILABLE**
>
> Only **5 matches from the 2024 CPL playoffs** are available as sample data. Full historical odds (2019-2025) will be added in a future update once a reliable data source is secured.

Historical closing odds for Canadian Premier League matches.

## What is "Closing Odds"?

Closing odds are the final odds offered by bookmakers immediately before
a match starts (typically within 5-10 minutes of kickoff). These are
considered the most efficient market prices as they incorporate all
available information.

## Data Sources

- **Bet365**: Primary bookmaker (largest CPL betting volume)
- **Sports Interaction**: Secondary bookmaker (Canadian-based)

## Update Frequency

- Updated weekly after matches complete
- Includes matches from previous 7 days
- Real-time odds are NOT included (available via premium API)

## File Format

Each season has its own CSV file: `cpl_YYYY_closing_odds.csv`

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | string | Unique identifier matching matches CSV (format: `team1_vs_team2_YYYYMMDD`) |
| `date` | date | Match date (YYYY-MM-DD) |
| `home_team` | string | Home team name |
| `away_team` | string | Away team name |
| `bookmaker` | string | `bet365` or `sportsinteraction` |
| `closing_home` | decimal | Final home win odds before kickoff |
| `closing_draw` | decimal | Final draw odds |
| `closing_away` | decimal | Final away win odds |
| `closing_over_2.5` | decimal | Final over 2.5 goals odds (optional) |
| `closing_under_2.5` | decimal | Final under 2.5 goals odds (optional) |
| `scraped_at` | datetime | UTC timestamp when odds were captured (ISO 8601) |

### Example

```csv
match_id,date,home_team,away_team,bookmaker,closing_home,closing_draw,closing_away,closing_over_2.5,closing_under_2.5,scraped_at
forge_vs_ottawa_20240413,2024-04-13,Forge FC,Atletico Ottawa,bet365,1.75,3.60,4.20,1.85,1.95,2024-04-13T18:55:00Z
forge_vs_ottawa_20240413,2024-04-13,Forge FC,Atletico Ottawa,sportsinteraction,1.78,3.55,4.10,1.83,1.97,2024-04-13T18:55:00Z
```

## Use Cases

- **Market efficiency analysis** - Compare predicted probabilities to market prices
- **Model validation** - Benchmark your predictions against closing lines
- **Historical betting market sentiment** - Track how markets viewed each team
- **Academic research** - Study sports betting markets in a smaller league
- **Closing Line Value (CLV) analysis** - Measure edge by comparing bet prices to closing

## Understanding Odds

All odds are in **decimal format**:

- `1.75` means a $100 bet wins $175 ($75 profit)
- `3.60` means a $100 bet wins $360 ($260 profit)

### Implied Probability

Convert decimal odds to implied probability:

```python
probability = 1 / decimal_odds
# 1.75 odds = 57.1% implied probability
# 3.60 odds = 27.8% implied probability
```

### Bookmaker Margin (Vig)

The sum of implied probabilities exceeds 100% due to bookmaker margin:

```python
# Example: Home 1.75, Draw 3.60, Away 4.20
margin = (1/1.75 + 1/3.60 + 1/4.20) - 1
# = 0.571 + 0.278 + 0.238 - 1 = 0.087 (8.7% margin)
```

## Data Coverage

| Season | Status | Matches |
|--------|--------|---------|
| 2019 | ❌ No data | 0 |
| 2020 | ❌ No data | 0 |
| 2021 | ❌ No data | 0 |
| 2022 | ❌ No data | 0 |
| 2023 | ❌ No data | 0 |
| 2024 | ⚠️ Playoffs only | 5 |
| 2025 | ❌ No data | 0 |

## Current Data Source

The 5 available matches are a limited sample from the 2024 CPL playoffs. Full historical data is not yet available.

## Future Plans

Options being considered:
1. Purchase historical odds from The Odds API (~$50-100 one-time)
2. Manual data collection from archived sources
3. Wait for 2025 season and capture closing odds in real-time

## Important Notes

- These are **CLOSING odds only** (not opening or mid-market)
- Odds represent the final efficient market price
- Bookmaker juice (vig) is included in odds
- Real-time odds available via premium API (coming soon)
- Historical data available from 2019 (CPL inaugural season)

## License

This data is provided under CC-BY-4.0. Attribution required.

When using this data, please cite:

```
CPL Analytics - Canadian Premier League Open Data
https://canpl-analytics.vercel.app
```
