# CPL Analytics Data Dictionary

This document describes all fields in the CPL Analytics dataset.

## Match Data (`data/matches/cpl_YYYY.csv`)

| Field | Type | Description |
|-------|------|-------------|
| `season` | Integer | Season year (2019-2026) |
| `match_week` | Integer | Match week number in season |
| `date` | Date | Match date (YYYY-MM-DD format) |
| `kickoff_time` | Time | Local kickoff time (HH:MM) |
| `home_team` | String | Home team name |
| `away_team` | String | Away team name |
| `home_goals` | Integer | Full-time home team goals |
| `away_goals` | Integer | Full-time away team goals |
| `ht_home_goals` | Integer | Half-time home team goals |
| `ht_away_goals` | Integer | Half-time away team goals |
| `venue` | String | Stadium name |
| `attendance` | Integer | Match attendance |
| `referee` | String | Match referee |
| `is_playoff` | Boolean | Whether match is a playoff game |
| `weather_temp_c` | Decimal | Temperature at kickoff (Celsius) |
| `weather_conditions` | String | Weather conditions (Clear, Rain, etc.) |
| `wind_speed_kmh` | Decimal | Wind speed (km/h) |

## Team Statistics (`data/team_stats/team_season_stats.csv`)

| Field | Type | Description |
|-------|------|-------------|
| `team` | String | Team name |
| `season` | Integer | Season year |
| `matches_played` | Integer | Total matches played |
| `wins` | Integer | Total wins |
| `draws` | Integer | Total draws |
| `losses` | Integer | Total losses |
| `goals_for` | Integer | Total goals scored |
| `goals_against` | Integer | Total goals conceded |
| `goal_difference` | Integer | GF - GA |
| `points` | Integer | League points (W=3, D=1, L=0) |
| `avg_shots` | Decimal | Average shots per match |
| `avg_shots_on_target` | Decimal | Average SOT per match |
| `avg_possession` | Decimal | Average possession % |
| `avg_corners` | Decimal | Average corners per match |
| `yellow_cards` | Integer | Total yellow cards |
| `red_cards` | Integer | Total red cards |

## Historical Odds (`data/historical_odds/odds_YYYY.csv`)

| Field | Type | Description |
|-------|------|-------------|
| `match_id` | Integer | Reference to match |
| `date` | Date | Match date |
| `home_team` | String | Home team |
| `away_team` | String | Away team |
| `bookmaker` | String | Bookmaker name |
| `timestamp` | Datetime | When odds were recorded |
| `home_odds` | Decimal | Home win decimal odds |
| `draw_odds` | Decimal | Draw decimal odds |
| `away_odds` | Decimal | Away win decimal odds |
| `over_25_odds` | Decimal | Over 2.5 goals odds |
| `under_25_odds` | Decimal | Under 2.5 goals odds |
| `is_opening` | Boolean | Opening odds (True) or closing (False) |

## Teams Reference

| Team Name | City | Stadium | Active |
|-----------|------|---------|--------|
| Forge FC | Hamilton | Tim Hortons Field | 2019-present |
| Cavalry FC | Calgary | ATCO Field | 2019-present |
| Pacific FC | Langford | Starlight Stadium | 2019-present |
| York United FC | Toronto | York Lions Stadium | 2019-present |
| Valour FC | Winnipeg | IG Field | 2019-present |
| HFX Wanderers FC | Halifax | Wanderers Grounds | 2019-present |
| FC Edmonton | Edmonton | Clarke Stadium | 2019-2023 |
| Atletico Ottawa | Ottawa | TD Place Stadium | 2020-present |
| Vancouver FC | Langley | Willoughby Park | 2023-present |

### Historical Team Names

- **York9 FC** → **York United FC** (renamed 2021)

## Data Quality Notes

### Completeness

- Match results: 100% complete
- Attendance: ~95% complete (some early matches missing)
- Weather: ~90% complete (requires API for historical)
- Odds: Varies by season

### Known Issues

1. Early 2019 season has some missing attendance figures
2. Weather data before 2021 may be incomplete
3. Some playoff matches marked as regular season

### Update Frequency

- Match results: Within 24 hours of match end
- Team stats: Weekly (Monday mornings)
- Odds: Historical - daily updates, Live - every 5 minutes (premium)

## Decimal Odds Explanation

All odds are in decimal (European) format:

- `1.50` = Bet $100 to win $50 profit ($150 total return)
- `2.00` = Even money (bet $100 to win $100)
- `3.00` = 2-to-1 (bet $100 to win $200)

**Implied probability** = 1 / odds × 100%

Example: Odds of 2.50 = 40% implied probability
