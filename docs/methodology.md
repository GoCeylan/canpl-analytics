# Data Collection Methodology

This document describes how CPL Analytics data is collected and processed.

## Data Sources

### Primary Sources

1. **CanPL.ca** - Official CPL website
   - Match results
   - Lineups
   - Basic statistics

2. **OneSoccer** - Official CPL broadcaster
   - Detailed match statistics
   - Video-derived data

3. **Transfermarkt** - Player/team data
   - Player information
   - Transfer history

### Secondary Sources

1. **Soccerway** - Match verification
2. **FlashScore** - Live data verification
3. **Wikipedia** - Historical reference

### Betting Odds Sources

- Bet365
- Sports Interaction
- Pinnacle
- Betway

## Collection Process

### Match Results

```
1. Automated scraper runs daily at 6 AM EST
2. Scraper fetches previous day's results from CanPL.ca
3. Results are validated against secondary sources
4. Data validator checks for anomalies
5. If validated, data is appended to season CSV
6. Weekly manual review for completeness
```

### Match Statistics

```
1. Stats collected from OneSoccer post-match
2. Cross-referenced with CPL website
3. xG calculated using public xG models (where available)
4. Aggregated into team season stats weekly
```

### Weather Data

```
1. OpenWeatherMap API called for each match
2. For upcoming matches: forecast API
3. For past matches: historical API (or cached data)
4. Data linked to match by date and venue
```

### Betting Odds

```
1. Live odds tracked every 5 minutes during betting windows
2. Opening odds recorded when markets open (~7 days pre-match)
3. Closing odds recorded at kickoff
4. Line movements flagged when >5% change detected
```

## Data Processing

### Cleaning Steps

1. **Team Name Normalization**
   - Map variations to standard names
   - Handle historical name changes (York9 → York United)

2. **Date Standardization**
   - All dates in ISO 8601 format (YYYY-MM-DD)
   - Times in 24-hour format, local timezone

3. **Missing Value Handling**
   - Required fields: Must be present or row excluded
   - Optional fields: Left as null/empty

4. **Duplicate Detection**
   - Primary key: (date, home_team, away_team)
   - Duplicates flagged and manually reviewed

### Validation Rules

```python
# Score validation
assert home_goals >= 0
assert away_goals >= 0
assert home_goals <= 15  # Flag if exceeded

# Team validation
assert home_team in VALID_TEAMS
assert away_team in VALID_TEAMS
assert home_team != away_team

# Date validation
assert date >= '2019-04-27'  # First CPL match
assert date <= today

# Attendance validation
assert attendance >= 0
assert attendance <= 30000  # Max CPL stadium capacity
```

## Update Schedule

| Data Type | Frequency | Time (EST) |
|-----------|-----------|------------|
| Match Results | Daily | 6:00 AM |
| Team Stats | Weekly | Monday 9:00 AM |
| Weather | Per match | Kickoff + 1 hour |
| Odds (Public) | Daily | End of day |
| Odds (Live) | 5 minutes | Continuous |

## Quality Assurance

### Automated Checks

1. Schema validation (required fields present)
2. Range checks (scores, attendance, odds)
3. Consistency checks (season matches date year)
4. Duplicate detection
5. Team name validation

### Manual Reviews

1. Weekly data completeness review
2. Monthly cross-source verification
3. Season-end full audit

### Error Handling

- Scraping failures: Retry 3 times with exponential backoff
- Validation failures: Flag for manual review, don't auto-commit
- Source conflicts: Primary source takes precedence

## Limitations

1. **Historical Data (2019-2020)**
   - Less complete statistics
   - Some attendance figures missing
   - Limited weather data

2. **xG Data**
   - Not provided by CPL officially
   - Calculated using approximation models
   - Less accurate than commercial providers

3. **Odds Data**
   - Not all bookmakers available historically
   - Some line movements may be missed
   - Market depth not captured

## Reproducibility

All scraping scripts are included in `scripts/` directory.
To reproduce data collection:

```bash
# Set up environment
pip install -r requirements.txt

# Set API keys
export OPENWEATHER_API_KEY=your_key

# Run scrapers
python scripts/cpl_results_scraper.py
python scripts/weather_integration.py

# Validate
python scripts/data_validator.py
```
