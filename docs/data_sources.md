# Data Sources & Quality

Documentation on data provenance, quality, and limitations for the CPL Analytics API.

## Table of Contents

- [Data Sources](#data-sources)
- [Update Frequency](#update-frequency)
- [Data Quality](#data-quality)
- [Known Limitations](#known-limitations)
- [Historical Notes](#historical-notes)
- [Reporting Issues](#reporting-issues)

---

## Data Sources

### 2025 Season Data

| Data Type | Source | Reliability |
|-----------|--------|-------------|
| Match results | Official CanPL SDP API | High |
| Standings | Official CanPL SDP API | High |
| Team information | Official CanPL sources | High |

The 2025 season data is sourced directly from the Canadian Premier League's official Sports Data Platform (SDP) API, providing authoritative match results and standings.

### 2019-2024 Historical Data

| Data Type | Source | Reliability |
|-----------|--------|-------------|
| Match results | Historical records + verification | High |
| Standings | Calculated from match results | High |
| Team information | Official archives | High |

Historical data was compiled from:
- Official CPL match reports and press releases
- Verified third-party sports databases
- Cross-referenced with multiple sources for accuracy

### Team Metadata

| Field | Source | Notes |
|-------|--------|-------|
| Coordinates | Manual geocoding | Stadium center points |
| Surface type | Official stadium info | May change with renovations |
| Founded year | Official team records | Year franchise was established |

---

## Update Frequency

### During Season (April - November)

| Data Type | Update Frequency | Typical Delay |
|-----------|-----------------|---------------|
| Match results | After each matchday | < 24 hours |
| Standings | After each matchday | < 24 hours |
| Team info | As changes occur | < 1 week |

### Off-Season (December - March)

| Data Type | Update Frequency |
|-----------|-----------------|
| Match results | No updates |
| Standings | Final standings frozen |
| Team info | Updated for roster/stadium changes |

### API Cache

- Match data: Cached for 1 hour (`s-maxage=3600`)
- Standings: Cached for 1 hour
- Team data: Cached for 24 hours (`s-maxage=86400`)

---

## Data Quality

### Completeness by Field

| Field | Completeness | Notes |
|-------|--------------|-------|
| `date` | 100% | All matches have dates |
| `home_team` | 100% | All matches have team names |
| `away_team` | 100% | All matches have team names |
| `home_goals` | 100% | Final scores always recorded |
| `away_goals` | 100% | Final scores always recorded |
| `season` | 100% | Derived from date |
| `venue` | 98% | Some early matches missing |

### Data Verification Process

1. **Primary source collection** - Data pulled from official APIs/records
2. **Cross-reference check** - Verified against multiple sources
3. **Automated validation** - Scripts check for:
   - Invalid scores (negative goals)
   - Date formatting issues
   - Team name consistency
   - Duplicate matches
4. **Manual review** - Spot checks on random samples

### Standings Accuracy

| Source | Accuracy Notes |
|--------|----------------|
| `official` | Directly from CanPL API, excludes playoff matches |
| `calculated` | Computed from match results, includes all matches |

When `source: "official"` is returned, standings reflect the official league table. When `source: "calculated"`, standings are computed from match results which may include playoff matches.

---

## Known Limitations

### Team Name Variations

Different data sources use different team name formats:

| Standard Name | Variations Found |
|---------------|-----------------|
| Forge FC | "Forge", "Hamilton Forge" |
| HFX Wanderers FC | "HFX Wanderers", "Halifax Wanderers" |
| Atletico Ottawa | "Atlético Ottawa" (with accent) |
| York United FC | "York9 FC" (pre-2021) |

The API normalizes to the standard names shown in the first column.

### Playoff vs Regular Season

- Official standings from the API exclude playoff matches
- Calculated standings may include playoff matches
- There is no `is_playoff` flag in the current API response
- Future versions may add playoff filtering

### Inactive Teams

| Team | Status | Seasons Active |
|------|--------|----------------|
| FC Edmonton | Inactive | 2019-2023 |
| York United FC | Inactive | 2019-2024 |

These teams appear in historical data but not in current season matches.

### Coordinate Precision

Team coordinates are:
- Manually geocoded to stadium center points
- Accurate to approximately 50 meters
- May not reflect exact pitch center
- Subject to change if teams relocate

### Surface Type Accuracy

Playing surface data:
- Based on current stadium configuration
- May not reflect temporary changes
- Grass fields can convert to turf (or vice versa)
- Not historically tracked per-season

---

## Historical Notes

### 2019 Season

- CPL inaugural season
- 7 teams competed
- Season format: Spring and Fall split seasons
- Some early attendance figures missing

### 2020 Season

- COVID-19 pandemic impact
- "Island Games" format in PEI
- Shortened season (8 matches per team)
- No attendance data (closed doors)

### 2021 Season

- Hybrid format with bubble phases
- York9 FC renamed to York United FC
- Gradual return of fans

### 2022 Season

- Return to normal home-and-away format
- Full season (28 matches per team)
- Atletico Ottawa's first full home season

### 2023 Season

- FC Edmonton final season
- Vancouver FC first full season
- Standard 28-match format

### 2024 Season

- York United FC final season
- Inter Toronto expansion team announced
- 8 active teams

### 2025 Season

- Inter Toronto begins play
- Potential additional expansion
- Data sourced from official SDP API

---

## Reporting Issues

### How to Report Data Errors

If you find incorrect or missing data, please report it:

**GitHub Issues (Preferred)**
1. Go to the repository issues page
2. Create a new issue with label "data-error"
3. Include:
   - The specific match/team/date affected
   - What the data currently shows
   - What the correct data should be
   - Source for the correct data (link if possible)

**Required Information**

```markdown
## Data Error Report

**Endpoint:** /api/matches
**Date/Match:** 2024-05-15, Forge FC vs Cavalry FC
**Current Value:** home_goals: 2
**Correct Value:** home_goals: 3
**Source:** [Official CPL match report](link)
```

### Response Time

- Critical errors (wrong scores): < 24 hours
- Minor issues (spelling, metadata): < 1 week
- Feature requests: Reviewed monthly

### What Constitutes a Data Error

**Report These:**
- Incorrect match scores
- Wrong dates
- Missing matches
- Team name typos
- Incorrect stadium names
- Wrong standings positions

**Don't Report These:**
- Feature requests (use feature request template)
- API performance issues (use bug report template)
- Questions (use discussions)

---

## Data License

The match data in this API is provided for:
- Educational purposes
- Personal projects
- Research and analysis
- Non-commercial use

For commercial use, please contact the Canadian Premier League directly for official data licensing.

---

## Related Documentation

- [API Reference](./api_reference.md) - Endpoint details and parameters
- [Data Dictionary](./api_data_dictionary.md) - Field definitions
- [Use Cases](./use_cases.md) - Example queries and analysis
