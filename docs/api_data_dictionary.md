# API Data Dictionary

This document describes all fields returned by the CPL Analytics API endpoints.

## Table of Contents

- [/api/matches Response](#apimatches-response)
- [/api/standings Response](#apistandings-response)
- [/api/teams Response](#apiteams-response)

---

## /api/matches Response

Returns paginated match data with filtering support.

### Response Envelope

| Field | Type | Description |
|-------|------|-------------|
| `total` | Integer | Total number of matches matching filters |
| `count` | Integer | Number of matches in current page |
| `offset` | Integer | Current pagination offset |
| `limit` | Integer | Current page size limit |
| `matches` | Array | Array of match objects |

### Match Object Fields

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `date` | String | `"2024-04-15"` | Match date in YYYY-MM-DD format |
| `home_team` | String | `"Forge FC"` | Full name of home team |
| `away_team` | String | `"Cavalry FC"` | Full name of away team |
| `home_goals` | Integer | `2` | Goals scored by home team |
| `away_goals` | Integer | `1` | Goals scored by away team |
| `season` | Integer | `2024` | Season year (2019-2025) |
| `venue` | String | `"Tim Hortons Field"` | Stadium where match was played |

### Example Match Object

```json
{
  "date": "2024-04-15",
  "home_team": "Forge FC",
  "away_team": "Cavalry FC",
  "home_goals": 2,
  "away_goals": 1,
  "season": 2024,
  "venue": "Tim Hortons Field"
}
```

---

## /api/standings Response

Returns league standings calculated from match results or official API data.

### Single Season Response Envelope

When `?season=YYYY` is provided:

| Field | Type | Description |
|-------|------|-------------|
| `season` | Integer | The requested season year |
| `standings` | Array | Array of team standing objects |
| `source` | String | `"official"` or `"calculated"` |

### All Seasons Response Envelope

When no season filter:

| Field | Type | Description |
|-------|------|-------------|
| `seasons` | Array | List of available seasons (integers) |
| `standings` | Object | Map of season year to standings array |

### Standing Object Fields

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `position` | Integer | `1` | League rank (1-8, 1 being top) |
| `team` | String | `"Forge FC"` | Team name |
| `played` | Integer | `28` | Total matches played |
| `wins` | Integer | `18` | Number of wins |
| `draws` | Integer | `5` | Number of draws |
| `losses` | Integer | `5` | Number of losses |
| `goals_for` | Integer | `52` | Total goals scored |
| `goals_against` | Integer | `28` | Total goals conceded |
| `goal_difference` | Integer | `24` | goals_for minus goals_against |
| `points` | Integer | `59` | League points (3 per win, 1 per draw) |
| `source` | String | `"official"` | Data source indicator (single-season only) |

### Points Calculation

```
points = (wins × 3) + (draws × 1) + (losses × 0)
```

### Tiebreaker Rules

Standings are sorted by:
1. Points (descending)
2. Goal difference (descending)
3. Goals scored (descending)

### Example Standing Object

```json
{
  "position": 1,
  "team": "Forge FC",
  "played": 28,
  "wins": 18,
  "draws": 5,
  "losses": 5,
  "goals_for": 52,
  "goals_against": 28,
  "goal_difference": 24,
  "points": 59
}
```

---

## /api/teams Response

Returns information about CPL teams.

### Response Envelope

| Field | Type | Description |
|-------|------|-------------|
| `count` | Integer | Number of teams returned |
| `teams` | Array | Array of team objects |

### Team Object Fields

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `name` | String | `"Forge FC"` | Official team name |
| `city` | String | `"Hamilton"` | Home city |
| `stadium` | String | `"Tim Hortons Field"` | Home stadium name |
| `founded` | Integer | `2018` | Year team was founded |
| `latitude` | Float | `43.2557` | Stadium latitude (hardcoded) |
| `longitude` | Float | `-79.8711` | Stadium longitude (hardcoded) |
| `surface` | String | `"grass"` | Playing surface type |
| `status` | String | `"active"` | Team activity status |

### Field Value Details

#### `surface` Values

| Value | Description |
|-------|-------------|
| `"grass"` | Natural grass surface |
| `"turf"` | Artificial turf surface |

#### `status` Values

| Value | Description |
|-------|-------------|
| `"active"` | Currently competing in CPL |
| `"inactive"` | No longer competing (e.g., FC Edmonton) |

### Current CPL Teams (2025)

| Team | City | Surface | Status |
|------|------|---------|--------|
| Atletico Ottawa | Ottawa | turf | active |
| Cavalry FC | Calgary | grass | active |
| Forge FC | Hamilton | grass | active |
| HFX Wanderers FC | Halifax | grass | active |
| Pacific FC | Langford | turf | active |
| Valour FC | Winnipeg | turf | active |
| Vancouver FC | Langley | turf | active |
| Inter Toronto | Toronto | turf | active |
| FC Edmonton | Edmonton | turf | inactive |
| York United FC | Toronto | turf | inactive |

### Example Team Object

```json
{
  "name": "Forge FC",
  "city": "Hamilton",
  "stadium": "Tim Hortons Field",
  "founded": 2018,
  "latitude": 43.2557,
  "longitude": -79.8711,
  "surface": "grass",
  "status": "active"
}
```

---

## Data Types Reference

| Type | Format | Notes |
|------|--------|-------|
| String | UTF-8 | Team names may include accented characters (e.g., "Atlético Ottawa") |
| Integer | 32-bit signed | Numeric IDs, counts, scores |
| Float | 64-bit double | Coordinates to 4 decimal places |
| Date String | YYYY-MM-DD | ISO 8601 date format |

---

## Related Documentation

- [API Reference](./api_reference.md) - Endpoint details and parameters
- [Use Cases](./use_cases.md) - Example queries and analysis
- [Data Sources](./data_sources.md) - Data provenance and quality
