# Canada Soccer API

The open data layer for the Canadian Premier League: complete results and schedules, live scores, official standings, player ratings and leaderboards, advanced player/team/match statistics, referees, venues, weather, and odds.

Production: [canadasoccerapi.com](https://canadasoccerapi.com)

API discovery: [canadasoccerapi.com/api/v1](https://canadasoccerapi.com/api/v1)

OpenAPI 3.1: [canadasoccerapi.com/openapi.json](https://canadasoccerapi.com/openapi.json)

## Quick start

No account or API key is required.

```bash
curl "https://canadasoccerapi.com/api/v1/live"
curl "https://canadasoccerapi.com/api/v1/players?eligible=true&limit=10"
curl "https://canadasoccerapi.com/api/v1/leaderboards?metric=rating,goals,assists&limit=5"
```

```js
const response = await fetch(
  'https://canadasoccerapi.com/api/v1/matches?season=2026&team=Forge&limit=10'
);
const data = await response.json();
```

## Resources

| Endpoint | Coverage |
|---|---|
| `GET /api/v1/matches` | 2019–current results plus the official live schedule |
| `GET /api/v1/live` | Live scores, match clock, broadcasters, and near-term fixtures |
| `GET /api/v1/standings` | Official historical tables and live current table |
| `GET /api/v1/players` | Identities, 30+ season metrics, overall ratings, and area breakdowns |
| `GET /api/v1/leaderboards` | Rating, scoring, creation, passing, defending, and goalkeeping boards |
| `GET /api/v1/team-stats` | Current advanced team profiles and optional raw source metrics |
| `GET /api/v1/teams` | Normalized current and historical club directory |
| `GET /api/v1/match-stats` | Match-level advanced statistics, xG, scorers, and attendance |
| `GET /api/v1/referees` | Historical assignments and referee summaries |
| `GET /api/v1/venues` | Capacity, surface, city, and coordinates |
| `GET /api/v1/weather` | Historical match weather |
| `GET /api/v1/odds` | Recorded closing prices |
| `GET /api/v1/odds-quotes` | Timestamped bookmaker snapshots |
| `GET /api/v1/seasons` | Season identifiers and dataset coverage |
| `GET /api/v1/health` | Service and data-file diagnostics |

Legacy `/api/{resource}` routes remain available. New integrations should use `/api/v1/{resource}`.

## Player ratings

Season ratings are transparent, position-aware, and recalculated with the live player feed. Players are compared with positional peers across attack, creativity, possession, defending, and discipline. Role-specific weights produce the overall 0–10 rating. Samples are shrunk toward league average until 720 minutes; 270 minutes is required for leaderboard eligibility. Every player response includes the five-area breakdown.

## API behaviour

- JSON responses and permissive CORS
- `limit`/`offset` pagination with `total`, `count`, and `has_more`
- case-insensitive team and player search
- 15-second live-match caching, 60-second season-feed caching, longer archive caching
- best-effort public limit of 300 requests per IP per hour
- stable HTTP 400/404/405/429/500 error responses

See the [API reference](https://canadasoccerapi.com/docs/api-reference.html) or [`public/openapi.json`](public/openapi.json) for every query parameter.

## Local development

```bash
npm install
npm test
npx vercel dev
```

The API runs as Node serverless functions configured in `vercel.json`. Stable datasets live under `data/`; current-season competition feeds are fetched from the official CPL site API with a repository snapshot fallback for the match schedule.

## License and attribution

Project data is released under CC BY 4.0 unless a source file states otherwise. This is an independent project and is not affiliated with or endorsed by the Canadian Premier League or Canada Soccer. Attribute Canada Soccer API when publishing derived work and retain the `source` fields returned by the API.
