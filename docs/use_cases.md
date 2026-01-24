# CPL Analytics API Use Cases

Practical examples demonstrating how to query and analyze CPL data using the API.

## Table of Contents

- [Find All Forge FC Home Wins in 2024](#find-all-forge-fc-home-wins-in-2024)
- [Calculate Head-to-Head Records Between Teams](#calculate-head-to-head-records-between-teams)
- [Track Goal Difference Trends Over Seasons](#track-goal-difference-trends-over-seasons)
- [Map Team Locations Geographically](#map-team-locations-geographically)
- [Analyze Home vs Away Performance](#analyze-home-vs-away-performance)
- [Find Highest-Scoring Matches](#find-highest-scoring-matches)

---

## Find All Forge FC Home Wins in 2024

### Query

```
GET /api/matches?season=2024&team=Forge
```

### Python Implementation

```python
import requests

def get_forge_home_wins_2024():
    """Find all Forge FC home wins in the 2024 season."""
    url = "https://canpl-analytics.vercel.app/api/matches"
    params = {"season": 2024, "team": "Forge", "limit": 500}

    response = requests.get(url, params=params)
    data = response.json()

    # Filter for home wins
    home_wins = [
        match for match in data["matches"]
        if match["home_team"] == "Forge FC"
        and match["home_goals"] > match["away_goals"]
    ]

    print(f"Forge FC Home Wins in 2024: {len(home_wins)}")
    for match in home_wins:
        print(f"  {match['date']}: Forge FC {match['home_goals']} - "
              f"{match['away_goals']} {match['away_team']}")

    return home_wins

# Execute
wins = get_forge_home_wins_2024()
```

### JavaScript Implementation

```javascript
async function getForgeHomeWins2024() {
  const url = 'https://canpl-analytics.vercel.app/api/matches?season=2024&team=Forge&limit=500';

  const response = await fetch(url);
  const data = await response.json();

  // Filter for home wins
  const homeWins = data.matches.filter(match =>
    match.home_team === 'Forge FC' &&
    match.home_goals > match.away_goals
  );

  console.log(`Forge FC Home Wins in 2024: ${homeWins.length}`);
  homeWins.forEach(match => {
    console.log(`  ${match.date}: Forge FC ${match.home_goals} - ${match.away_goals} ${match.away_team}`);
  });

  return homeWins;
}

// Execute
getForgeHomeWins2024();
```

### Expected Output

```
Forge FC Home Wins in 2024: 11
  2024-04-13: Forge FC 3 - 1 Atletico Ottawa
  2024-04-27: Forge FC 2 - 0 Valour FC
  2024-05-11: Forge FC 4 - 2 Pacific FC
  ...
```

### Analysis Insights

- Forge FC typically has strong home form due to passionate local support
- Tim Hortons Field's grass surface suits their playing style
- Compare home win percentage to league average to assess home advantage

---

## Calculate Head-to-Head Records Between Teams

### Query

```
GET /api/matches?team=Forge
GET /api/matches?team=Cavalry
```

### Python Implementation

```python
import requests
from collections import defaultdict

def head_to_head(team1: str, team2: str):
    """Calculate head-to-head record between two teams."""
    url = "https://canpl-analytics.vercel.app/api/matches"

    # Get all matches for team1 (includes matches vs team2)
    response = requests.get(url, params={"team": team1, "limit": 500})
    matches = response.json()["matches"]

    # Filter to matches between the two teams
    h2h_matches = [
        m for m in matches
        if (team1.lower() in m["home_team"].lower() or team1.lower() in m["away_team"].lower())
        and (team2.lower() in m["home_team"].lower() or team2.lower() in m["away_team"].lower())
    ]

    # Calculate record
    record = {"team1_wins": 0, "team2_wins": 0, "draws": 0, "matches": []}

    for match in h2h_matches:
        is_team1_home = team1.lower() in match["home_team"].lower()
        team1_goals = match["home_goals"] if is_team1_home else match["away_goals"]
        team2_goals = match["away_goals"] if is_team1_home else match["home_goals"]

        if team1_goals > team2_goals:
            record["team1_wins"] += 1
        elif team2_goals > team1_goals:
            record["team2_wins"] += 1
        else:
            record["draws"] += 1

        record["matches"].append({
            "date": match["date"],
            "score": f"{team1_goals}-{team2_goals}",
            "venue": match["venue"]
        })

    print(f"\n=== {team1} vs {team2} Head-to-Head ===")
    print(f"Total matches: {len(h2h_matches)}")
    print(f"{team1} wins: {record['team1_wins']}")
    print(f"{team2} wins: {record['team2_wins']}")
    print(f"Draws: {record['draws']}")
    print(f"\nRecent matches:")
    for m in record["matches"][-5:]:
        print(f"  {m['date']}: {m['score']} at {m['venue']}")

    return record

# Execute
h2h = head_to_head("Forge", "Cavalry")
```

### JavaScript Implementation

```javascript
async function headToHead(team1, team2) {
  const url = `https://canpl-analytics.vercel.app/api/matches?team=${team1}&limit=500`;

  const response = await fetch(url);
  const data = await response.json();

  // Filter to head-to-head matches
  const h2hMatches = data.matches.filter(m =>
    (m.home_team.toLowerCase().includes(team1.toLowerCase()) ||
     m.away_team.toLowerCase().includes(team1.toLowerCase())) &&
    (m.home_team.toLowerCase().includes(team2.toLowerCase()) ||
     m.away_team.toLowerCase().includes(team2.toLowerCase()))
  );

  let team1Wins = 0, team2Wins = 0, draws = 0;

  h2hMatches.forEach(match => {
    const isTeam1Home = match.home_team.toLowerCase().includes(team1.toLowerCase());
    const team1Goals = isTeam1Home ? match.home_goals : match.away_goals;
    const team2Goals = isTeam1Home ? match.away_goals : match.home_goals;

    if (team1Goals > team2Goals) team1Wins++;
    else if (team2Goals > team1Goals) team2Wins++;
    else draws++;
  });

  console.log(`\n=== ${team1} vs ${team2} Head-to-Head ===`);
  console.log(`Total matches: ${h2hMatches.length}`);
  console.log(`${team1} wins: ${team1Wins}`);
  console.log(`${team2} wins: ${team2Wins}`);
  console.log(`Draws: ${draws}`);

  return { team1Wins, team2Wins, draws, matches: h2hMatches };
}

// Execute
headToHead('Forge', 'Cavalry');
```

### Expected Output

```
=== Forge vs Cavalry Head-to-Head ===
Total matches: 24
Forge wins: 10
Cavalry wins: 8
Draws: 6

Recent matches:
  2024-09-21: 2-1 at ATCO Field
  2024-07-06: 1-1 at Tim Hortons Field
  2024-05-04: 3-2 at Tim Hortons Field
```

### Analysis Insights

- Forge vs Cavalry is known as the "Battle of the Shields"
- These are the two most successful CPL teams historically
- Home venue plays a significant role in these matchups
- Consider altitude (Calgary) and travel distance factors

---

## Track Goal Difference Trends Over Seasons

### Query

```
GET /api/standings
```

### Python Implementation

```python
import requests

def goal_difference_trends(team_name: str):
    """Track a team's goal difference across all seasons."""
    url = "https://canpl-analytics.vercel.app/api/standings"
    response = requests.get(url)
    data = response.json()

    print(f"\n=== {team_name} Goal Difference Trend ===\n")
    print(f"{'Season':<8} {'GF':<5} {'GA':<5} {'GD':<6} {'Position'}")
    print("-" * 35)

    trends = []
    for season in sorted(data["seasons"]):
        standings = data["standings"][str(season)]
        team_data = next(
            (t for t in standings if team_name.lower() in t["team"].lower()),
            None
        )
        if team_data:
            trends.append({
                "season": season,
                "gf": team_data["goals_for"],
                "ga": team_data["goals_against"],
                "gd": team_data["goal_difference"],
                "position": team_data["position"]
            })
            print(f"{season:<8} {team_data['goals_for']:<5} "
                  f"{team_data['goals_against']:<5} "
                  f"{team_data['goal_difference']:+<5} "
                  f"#{team_data['position']}")

    # Calculate trend
    if len(trends) >= 2:
        first_gd = trends[0]["gd"]
        last_gd = trends[-1]["gd"]
        change = last_gd - first_gd
        print(f"\nOverall GD change: {change:+d}")

    return trends

# Execute
trends = goal_difference_trends("Forge")
```

### JavaScript Implementation

```javascript
async function goalDifferenceTrends(teamName) {
  const url = 'https://canpl-analytics.vercel.app/api/standings';
  const response = await fetch(url);
  const data = await response.json();

  console.log(`\n=== ${teamName} Goal Difference Trend ===\n`);
  console.log('Season  GF    GA    GD     Position');
  console.log('-'.repeat(35));

  const trends = [];
  data.seasons.sort().forEach(season => {
    const standings = data.standings[season];
    const teamData = standings.find(t =>
      t.team.toLowerCase().includes(teamName.toLowerCase())
    );

    if (teamData) {
      trends.push({
        season,
        gf: teamData.goals_for,
        ga: teamData.goals_against,
        gd: teamData.goal_difference,
        position: teamData.position
      });
      const gdStr = teamData.goal_difference >= 0 ?
        `+${teamData.goal_difference}` : `${teamData.goal_difference}`;
      console.log(`${season}    ${teamData.goals_for}     ${teamData.goals_against}     ${gdStr}    #${teamData.position}`);
    }
  });

  return trends;
}

// Execute
goalDifferenceTrends('Forge');
```

### Expected Output

```
=== Forge Goal Difference Trend ===

Season  GF    GA    GD     Position
-----------------------------------
2019    50    29    +21    #1
2020    25    14    +11    #1
2021    42    28    +14    #1
2022    45    32    +13    #2
2023    48    30    +18    #1
2024    52    28    +24    #1

Overall GD change: +3
```

### Analysis Insights

- Consistent positive GD indicates defensive solidity and attacking prowess
- Forge has maintained top-tier GD throughout CPL history
- Year-over-year improvement suggests team development
- Compare to league averages to contextualize performance

---

## Map Team Locations Geographically

### Query

```
GET /api/teams
```

### Python Implementation

```python
import requests
import json

def map_team_locations():
    """Generate GeoJSON for mapping CPL team locations."""
    url = "https://canpl-analytics.vercel.app/api/teams?active_only=true"
    response = requests.get(url)
    data = response.json()

    # Generate GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    for team in data["teams"]:
        if team.get("latitude") and team.get("longitude"):
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [team["longitude"], team["latitude"]]
                },
                "properties": {
                    "name": team["name"],
                    "city": team["city"],
                    "stadium": team["stadium"],
                    "surface": team["surface"]
                }
            }
            geojson["features"].append(feature)

    print(f"Generated GeoJSON with {len(geojson['features'])} team locations")
    print("\nTeam Coordinates:")
    for team in data["teams"]:
        if team.get("latitude"):
            print(f"  {team['name']}: ({team['latitude']}, {team['longitude']})")

    # Save to file
    with open("cpl_teams.geojson", "w") as f:
        json.dump(geojson, f, indent=2)

    return geojson

# Execute
geojson = map_team_locations()
```

### JavaScript Implementation

```javascript
async function mapTeamLocations() {
  const url = 'https://canpl-analytics.vercel.app/api/teams?active_only=true';
  const response = await fetch(url);
  const data = await response.json();

  // Generate GeoJSON
  const geojson = {
    type: 'FeatureCollection',
    features: data.teams
      .filter(team => team.latitude && team.longitude)
      .map(team => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [team.longitude, team.latitude]
        },
        properties: {
          name: team.name,
          city: team.city,
          stadium: team.stadium,
          surface: team.surface
        }
      }))
  };

  console.log(`Generated GeoJSON with ${geojson.features.length} team locations`);
  console.log('\nTeam Coordinates:');
  data.teams.forEach(team => {
    if (team.latitude) {
      console.log(`  ${team.name}: (${team.latitude}, ${team.longitude})`);
    }
  });

  return geojson;
}

// Execute (can be used with Leaflet, Mapbox, etc.)
mapTeamLocations();
```

### Expected Output

```
Generated GeoJSON with 8 team locations

Team Coordinates:
  Atletico Ottawa: (45.3985, -75.6825)
  Cavalry FC: (50.99, -114.006)
  Forge FC: (43.2557, -79.8711)
  HFX Wanderers FC: (44.6488, -63.5752)
  Pacific FC: (48.45, -123.496)
  Valour FC: (49.8076, -97.1445)
  Vancouver FC: (49.0197, -122.6465)
  Inter Toronto: (43.7735, -79.4992)
```

### Analysis Insights

- CPL spans 5,000+ km from Halifax to Vancouver
- Travel distances significantly impact player fatigue
- Pacific and Vancouver are closest geographically
- Eastern teams cluster in Ontario while west is spread out
- Use with mapping libraries (Leaflet, Mapbox) for visualization

---

## Analyze Home vs Away Performance

### Query

```
GET /api/matches?season=2024&limit=500
```

### Python Implementation

```python
import requests
from collections import defaultdict

def home_vs_away_analysis(season: int):
    """Analyze home vs away performance for all teams."""
    url = "https://canpl-analytics.vercel.app/api/matches"
    response = requests.get(url, params={"season": season, "limit": 500})
    matches = response.json()["matches"]

    # Track home/away stats
    stats = defaultdict(lambda: {
        "home": {"played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0},
        "away": {"played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
    })

    for match in matches:
        home = match["home_team"]
        away = match["away_team"]
        hg, ag = match["home_goals"], match["away_goals"]

        # Home team stats
        stats[home]["home"]["played"] += 1
        stats[home]["home"]["gf"] += hg
        stats[home]["home"]["ga"] += ag

        # Away team stats
        stats[away]["away"]["played"] += 1
        stats[away]["away"]["gf"] += ag
        stats[away]["away"]["ga"] += hg

        if hg > ag:
            stats[home]["home"]["wins"] += 1
            stats[away]["away"]["losses"] += 1
        elif ag > hg:
            stats[home]["home"]["losses"] += 1
            stats[away]["away"]["wins"] += 1
        else:
            stats[home]["home"]["draws"] += 1
            stats[away]["away"]["draws"] += 1

    print(f"\n=== {season} Home vs Away Performance ===\n")
    print(f"{'Team':<20} {'Home W-D-L':<12} {'Home Pts':<10} {'Away W-D-L':<12} {'Away Pts':<10} {'Diff'}")
    print("-" * 75)

    results = []
    for team, data in sorted(stats.items()):
        h = data["home"]
        a = data["away"]
        home_pts = h["wins"] * 3 + h["draws"]
        away_pts = a["wins"] * 3 + a["draws"]
        diff = home_pts - away_pts

        results.append({
            "team": team,
            "home_record": f"{h['wins']}-{h['draws']}-{h['losses']}",
            "home_pts": home_pts,
            "away_record": f"{a['wins']}-{a['draws']}-{a['losses']}",
            "away_pts": away_pts,
            "diff": diff
        })

        print(f"{team:<20} {h['wins']}-{h['draws']}-{h['losses']:<8} {home_pts:<10} "
              f"{a['wins']}-{a['draws']}-{a['losses']:<8} {away_pts:<10} {diff:+d}")

    # League averages
    total_home_wins = sum(s["home"]["wins"] for s in stats.values())
    total_away_wins = sum(s["away"]["wins"] for s in stats.values())
    total_draws = sum(s["home"]["draws"] for s in stats.values())
    total_matches = total_home_wins + total_away_wins + total_draws

    print(f"\nLeague Home Win Rate: {total_home_wins/total_matches*100:.1f}%")
    print(f"League Away Win Rate: {total_away_wins/total_matches*100:.1f}%")
    print(f"League Draw Rate: {total_draws/total_matches*100:.1f}%")

    return results

# Execute
analysis = home_vs_away_analysis(2024)
```

### JavaScript Implementation

```javascript
async function homeVsAwayAnalysis(season) {
  const url = `https://canpl-analytics.vercel.app/api/matches?season=${season}&limit=500`;
  const response = await fetch(url);
  const matches = (await response.json()).matches;

  const stats = {};
  const initStats = () => ({
    home: { played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0 },
    away: { played: 0, wins: 0, draws: 0, losses: 0, gf: 0, ga: 0 }
  });

  matches.forEach(match => {
    const { home_team, away_team, home_goals, away_goals } = match;

    if (!stats[home_team]) stats[home_team] = initStats();
    if (!stats[away_team]) stats[away_team] = initStats();

    stats[home_team].home.played++;
    stats[home_team].home.gf += home_goals;
    stats[home_team].home.ga += away_goals;

    stats[away_team].away.played++;
    stats[away_team].away.gf += away_goals;
    stats[away_team].away.ga += home_goals;

    if (home_goals > away_goals) {
      stats[home_team].home.wins++;
      stats[away_team].away.losses++;
    } else if (away_goals > home_goals) {
      stats[home_team].home.losses++;
      stats[away_team].away.wins++;
    } else {
      stats[home_team].home.draws++;
      stats[away_team].away.draws++;
    }
  });

  console.log(`\n=== ${season} Home vs Away Performance ===\n`);
  Object.entries(stats).sort().forEach(([team, data]) => {
    const h = data.home;
    const a = data.away;
    const homePts = h.wins * 3 + h.draws;
    const awayPts = a.wins * 3 + a.draws;
    console.log(`${team}: Home ${h.wins}-${h.draws}-${h.losses} (${homePts}pts) | ` +
                `Away ${a.wins}-${a.draws}-${a.losses} (${awayPts}pts)`);
  });

  return stats;
}

// Execute
homeVsAwayAnalysis(2024);
```

### Expected Output

```
=== 2024 Home vs Away Performance ===

Team                 Home W-D-L   Home Pts   Away W-D-L   Away Pts   Diff
---------------------------------------------------------------------------
Atletico Ottawa      8-3-3        27         4-5-5        17         +10
Cavalry FC           9-2-3        29         7-5-2        26         +3
Forge FC             10-2-2       32         8-3-3        27         +5
...

League Home Win Rate: 44.2%
League Away Win Rate: 28.6%
League Draw Rate: 27.2%
```

### Analysis Insights

- CPL has significant home advantage (~15% higher win rate)
- Travel distances contribute to away team fatigue
- Grass vs turf surface changes affect performance
- Altitude (Calgary at 1,045m) impacts visiting teams

---

## Find Highest-Scoring Matches

### Query

```
GET /api/matches?limit=500
```

### Python Implementation

```python
import requests

def find_highest_scoring_matches(top_n: int = 10, season: int = None):
    """Find the highest-scoring matches in CPL history."""
    url = "https://canpl-analytics.vercel.app/api/matches"
    params = {"limit": 500}
    if season:
        params["season"] = season

    # Paginate to get all matches
    all_matches = []
    offset = 0
    while True:
        params["offset"] = offset
        response = requests.get(url, params=params)
        data = response.json()
        all_matches.extend(data["matches"])
        if offset + data["count"] >= data["total"]:
            break
        offset += 500

    # Sort by total goals
    all_matches.sort(
        key=lambda m: m["home_goals"] + m["away_goals"],
        reverse=True
    )

    title = f"Top {top_n} Highest-Scoring Matches"
    if season:
        title += f" ({season})"
    print(f"\n=== {title} ===\n")
    print(f"{'Date':<12} {'Match':<40} {'Score':<8} {'Total'}")
    print("-" * 70)

    for match in all_matches[:top_n]:
        total = match["home_goals"] + match["away_goals"]
        matchup = f"{match['home_team']} vs {match['away_team']}"
        score = f"{match['home_goals']}-{match['away_goals']}"
        print(f"{match['date']:<12} {matchup:<40} {score:<8} {total}")

    # Stats
    avg_goals = sum(m["home_goals"] + m["away_goals"] for m in all_matches) / len(all_matches)
    print(f"\nTotal matches: {len(all_matches)}")
    print(f"Average goals per match: {avg_goals:.2f}")

    return all_matches[:top_n]

# Execute
top_matches = find_highest_scoring_matches(10)
top_2024 = find_highest_scoring_matches(5, season=2024)
```

### JavaScript Implementation

```javascript
async function findHighestScoringMatches(topN = 10, season = null) {
  const baseUrl = 'https://canpl-analytics.vercel.app/api/matches';
  let allMatches = [];
  let offset = 0;

  // Paginate to get all matches
  while (true) {
    const params = new URLSearchParams({ limit: 500, offset });
    if (season) params.append('season', season);

    const response = await fetch(`${baseUrl}?${params}`);
    const data = await response.json();
    allMatches.push(...data.matches);

    if (offset + data.count >= data.total) break;
    offset += 500;
  }

  // Sort by total goals
  allMatches.sort((a, b) =>
    (b.home_goals + b.away_goals) - (a.home_goals + a.away_goals)
  );

  console.log(`\n=== Top ${topN} Highest-Scoring Matches${season ? ` (${season})` : ''} ===\n`);

  allMatches.slice(0, topN).forEach(match => {
    const total = match.home_goals + match.away_goals;
    console.log(`${match.date}: ${match.home_team} ${match.home_goals}-${match.away_goals} ${match.away_team} (${total} goals)`);
  });

  const avgGoals = allMatches.reduce((sum, m) => sum + m.home_goals + m.away_goals, 0) / allMatches.length;
  console.log(`\nAverage goals per match: ${avgGoals.toFixed(2)}`);

  return allMatches.slice(0, topN);
}

// Execute
findHighestScoringMatches(10);
```

### Expected Output

```
=== Top 10 Highest-Scoring Matches ===

Date         Match                                    Score    Total
----------------------------------------------------------------------
2019-08-28   Pacific FC vs HFX Wanderers FC           5-4      9
2021-07-17   Valour FC vs FC Edmonton                 6-2      8
2022-06-04   Forge FC vs Pacific FC                   5-3      8
2023-09-02   Cavalry FC vs Valour FC                  4-4      8
2019-07-06   Forge FC vs Valour FC                    4-3      7
...

Total matches: 532
Average goals per match: 2.73
```

### Analysis Insights

- CPL averages ~2.7 goals per match (comparable to top European leagues)
- High-scoring matches often involve Pacific FC (open style of play)
- Consider over/under betting markets based on team matchups
- Track teams with leaky defenses for goal-scoring opportunities

---

## Related Documentation

- [API Reference](./api_reference.md) - Endpoint details and parameters
- [Data Dictionary](./api_data_dictionary.md) - Field definitions
- [Data Sources](./data_sources.md) - Data provenance and quality
