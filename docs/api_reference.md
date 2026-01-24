# CPL Analytics API Reference

Complete reference documentation for the CPL Analytics public API.

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Rate Limits](#rate-limits)
- [Endpoints](#endpoints)
  - [GET /api/matches](#get-apimatches)
  - [GET /api/standings](#get-apistandings)
  - [GET /api/teams](#get-apiteams)
- [Error Handling](#error-handling)
- [CORS Support](#cors-support)

---

## Overview

The CPL Analytics API provides read-only access to Canadian Premier League match data, standings, and team information. All endpoints return JSON responses.

## Base URL

```
https://canpl-analytics.vercel.app
```

For local development:
```
http://localhost:3000
```

## Authentication

**No authentication required.** The API is publicly accessible for educational and research purposes.

## Rate Limits

| Tier | Limit | Window |
|------|-------|--------|
| Public (testing) | 20 requests | per hour per IP |

When rate limited, the API returns HTTP 429 with a `Retry-After` header.

---

## Endpoints

### GET /api/matches

Retrieve historical match data with optional filtering and pagination.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `season` | Integer | No | All | Filter by season year (2019-2025) |
| `team` | String | No | All | Filter by team name (case-insensitive, partial match) |
| `limit` | Integer | No | 100 | Maximum results per page (1-500) |
| `offset` | Integer | No | 0 | Number of results to skip |

#### Example Requests

**Get all matches:**
```bash
curl "https://canpl-analytics.vercel.app/api/matches"
```

**Get 2024 season matches:**
```bash
curl "https://canpl-analytics.vercel.app/api/matches?season=2024"
```

**Get Forge FC matches:**
```bash
curl "https://canpl-analytics.vercel.app/api/matches?team=Forge"
```

**Paginate results:**
```bash
curl "https://canpl-analytics.vercel.app/api/matches?limit=25&offset=50"
```

**Combined filters:**
```bash
curl "https://canpl-analytics.vercel.app/api/matches?season=2024&team=Cavalry&limit=10"
```

#### Example Response

```json
{
  "total": 156,
  "count": 10,
  "offset": 0,
  "limit": 10,
  "matches": [
    {
      "date": "2024-04-13",
      "home_team": "Forge FC",
      "away_team": "Atletico Ottawa",
      "home_goals": 3,
      "away_goals": 1,
      "season": 2024,
      "venue": "Tim Hortons Field"
    },
    {
      "date": "2024-04-14",
      "home_team": "Cavalry FC",
      "away_team": "Pacific FC",
      "home_goals": 2,
      "away_goals": 2,
      "season": 2024,
      "venue": "ATCO Field"
    }
  ]
}
```

#### Pagination

Use `offset` and `limit` to paginate through large result sets:

```python
# Python pagination example
import requests

base_url = "https://canpl-analytics.vercel.app/api/matches"
limit = 50
offset = 0
all_matches = []

while True:
    response = requests.get(f"{base_url}?limit={limit}&offset={offset}")
    data = response.json()
    all_matches.extend(data["matches"])

    if offset + data["count"] >= data["total"]:
        break
    offset += limit

print(f"Retrieved {len(all_matches)} matches")
```

---

### GET /api/standings

Get league standings for one or all seasons.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `season` | Integer | No | All | Specific season year (2019-2025) |

#### Example Requests

**Get current season standings:**
```bash
curl "https://canpl-analytics.vercel.app/api/standings?season=2024"
```

**Get all seasons:**
```bash
curl "https://canpl-analytics.vercel.app/api/standings"
```

#### Single Season Response

```json
{
  "season": 2024,
  "standings": [
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
    },
    {
      "position": 2,
      "team": "Cavalry FC",
      "played": 28,
      "wins": 16,
      "draws": 7,
      "losses": 5,
      "goals_for": 45,
      "goals_against": 25,
      "goal_difference": 20,
      "points": 55
    }
  ],
  "source": "official"
}
```

#### All Seasons Response

```json
{
  "seasons": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
  "standings": {
    "2024": [
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
    ],
    "2023": [...]
  }
}
```

#### Data Source

The `source` field indicates where the standings data originated:

| Value | Description |
|-------|-------------|
| `"official"` | From official CanPL SDP API (excludes playoffs) |
| `"calculated"` | Calculated from match results |

---

### GET /api/teams

Get information about CPL teams.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `active_only` | String | No | `"false"` | Set to `"true"` to exclude inactive teams |

#### Example Requests

**Get all teams:**
```bash
curl "https://canpl-analytics.vercel.app/api/teams"
```

**Get active teams only:**
```bash
curl "https://canpl-analytics.vercel.app/api/teams?active_only=true"
```

#### Example Response

```json
{
  "count": 10,
  "teams": [
    {
      "name": "Atletico Ottawa",
      "city": "Ottawa",
      "stadium": "TD Place Stadium",
      "founded": 2020,
      "latitude": 45.3985,
      "longitude": -75.6825,
      "surface": "turf",
      "status": "active"
    },
    {
      "name": "Cavalry FC",
      "city": "Calgary",
      "stadium": "ATCO Field",
      "founded": 2018,
      "latitude": 50.99,
      "longitude": -114.006,
      "surface": "grass",
      "status": "active"
    },
    {
      "name": "FC Edmonton",
      "city": "Edmonton",
      "stadium": "Clarke Stadium",
      "founded": 2010,
      "latitude": 53.5722,
      "longitude": -113.4557,
      "surface": "turf",
      "status": "inactive"
    }
  ]
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": "Error message description"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `400` | Bad Request | Invalid parameters |
| `404` | Not Found | Endpoint does not exist |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Server Error | Internal server error |

### Common Errors

**Invalid season parameter:**
```json
{
  "error": "Invalid season: must be between 2019 and 2025"
}
```

**Server error:**
```json
{
  "error": "Failed to load matches data"
}
```

### Error Handling Best Practices

```python
import requests

def fetch_matches(season=None):
    url = "https://canpl-analytics.vercel.app/api/matches"
    params = {}
    if season:
        params["season"] = season

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("Rate limited. Wait before retrying.")
        elif e.response.status_code == 500:
            print("Server error. Try again later.")
        raise
    except requests.exceptions.Timeout:
        print("Request timed out")
        raise
```

---

## CORS Support

The API supports Cross-Origin Resource Sharing (CORS) for browser-based applications.

### CORS Headers

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

### Browser Usage

```javascript
// Works directly in browser without proxy
fetch('https://canpl-analytics.vercel.app/api/matches')
  .then(response => response.json())
  .then(data => console.log(data.matches));
```

---

## Caching

Responses include cache headers for performance:

| Endpoint | Cache Duration |
|----------|----------------|
| `/api/matches` | 1 hour |
| `/api/standings` | 1 hour |
| `/api/teams` | 24 hours |

```
Cache-Control: s-maxage=3600, stale-while-revalidate
```

---

## Related Documentation

- [Data Dictionary](./api_data_dictionary.md) - Field definitions
- [Use Cases](./use_cases.md) - Example queries and analysis
- [Data Sources](./data_sources.md) - Data provenance and quality
