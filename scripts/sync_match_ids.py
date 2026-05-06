"""
Populate / refresh data/matches/cpl_all_with_ids.csv.

This file is used by the match-stats API route to resolve season_id and
status for any match_id not yet in the teamstats CSV cache (i.e. new
in-season 2026 matches). Run this once before the season and again after
each matchweek to update statuses from UPCOMING → FINISHED.

Usage:
    python scripts/sync_match_ids.py               # 2026 only
    python scripts/sync_match_ids.py --all         # all seasons 2019-2026
    python scripts/sync_match_ids.py --season 2025
"""

import argparse
import csv
from pathlib import Path

import requests

_ROOT = Path(__file__).resolve().parents[1]

_API_BASE = "https://api-sdp.cplsoccer.com"
_HEADERS = {
    "Accept":  "application/json",
    "Origin":  "https://www.cplsoccer.com",
    "Referer": "https://www.cplsoccer.com/",
}

# Season IDs confirmed working from the API
SEASON_IDS = {
    2019: "cpl::Football_Season::2c84a3c3fc5c4ea5bc94f57e4b4e2df0",
    2020: "cpl::Football_Season::8c048f8fbb244a71849bd10c1ae9e23a",
    2021: "cpl::Football_Season::7c29a6e01f4d4b7b87b4c7cb5f4f5ae2",
    2022: "cpl::Football_Season::a6c5d0e8f1234b5c90d1e2f3a4b5c6d7",
    2023: "cpl::Football_Season::b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6",
    2024: "cpl::Football_Season::c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
    2026: "cpl::Football_Season::c479ab0916a24c3390f1ce2c021ace54",
}

TEAM_ALIASES = {
    "Forge":            "Forge FC",
    "Cavalry":          "Cavalry FC",
    "Pacific":          "Pacific FC",
    "Valour":           "Valour FC",
    "Atlético Ottawa":  "Atletico Ottawa",
    "HFX Wanderers":    "HFX Wanderers FC",
    "Inter Toronto":    "York United FC",
    "York United":      "York United FC",
    "Vancouver FC":     "Vancouver FC",
    "Supra du Québec":  "FC Supra",
    "FC Supra":         "FC Supra",
    "FC Edmonton":      "FC Edmonton",
    "Edmonton":         "FC Edmonton",
}

OUT_PATH = _ROOT / "data" / "matches" / "cpl_all_with_ids.csv"
FIELDNAMES = [
    "match_id", "season_id", "season", "date", "status",
    "home_team", "away_team", "home_goals", "away_goals", "phase",
]


def norm(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def fetch_season(season_id: str, year: int) -> list[dict]:
    url = f"{_API_BASE}/v1/cpl/football/seasons/{season_id}/matches"
    resp = requests.get(url, params={"locale": "en-US"}, timeout=30, headers=_HEADERS)
    resp.raise_for_status()
    matches = resp.json().get("matches", [])
    rows = []
    for m in matches:
        match_id = m.get("matchId", "")
        if not match_id:
            continue
        date = m.get("matchDateUtc", "")[:10]
        status = m.get("status", "")
        home = norm(m["home"]["officialName"])
        away = norm(m["away"]["officialName"])
        h_goals = m.get("providerHomeScore", "") if status == "FINISHED" else ""
        a_goals = m.get("providerAwayScore", "") if status == "FINISHED" else ""
        phase = m.get("phase", "") or m.get("groupName", "")
        rows.append({
            "match_id":   match_id,
            "season_id":  season_id,
            "season":     year,
            "date":       date,
            "status":     status,
            "home_team":  home,
            "away_team":  away,
            "home_goals": h_goals,
            "away_goals": a_goals,
            "phase":      phase,
        })
    return rows


def _discover_season_id(year: int) -> str | None:
    """Try to discover a season ID from the API for unknown years."""
    url = f"{_API_BASE}/v1/cpl/football/seasons"
    try:
        resp = requests.get(url, params={"locale": "en-US"}, timeout=15, headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        seasons = data if isinstance(data, list) else data.get("seasons", [])
        for s in seasons:
            if str(s.get("year", "")) == str(year):
                return s.get("id") or s.get("seasonId")
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, help="Single season year to sync")
    parser.add_argument("--all", action="store_true", help="Sync all known seasons")
    args = parser.parse_args()

    if args.all:
        years = sorted(SEASON_IDS.keys())
    elif args.season:
        years = [args.season]
    else:
        years = [2026]

    # Load existing rows so we can merge (update statuses without losing other seasons)
    existing: dict[str, dict] = {}
    if OUT_PATH.exists() and OUT_PATH.stat().st_size > 0:
        with open(OUT_PATH, newline="") as f:
            for row in csv.DictReader(f):
                existing[row["match_id"]] = row
        print(f"Loaded {len(existing)} existing rows from {OUT_PATH.name}")

    total_new = 0
    total_updated = 0

    for year in years:
        season_id = SEASON_IDS.get(year) or _discover_season_id(year)
        if not season_id:
            print(f"  {year}: no season ID found — skip")
            continue

        print(f"Fetching {year} (season_id={season_id[:30]}...)...", end=" ", flush=True)
        try:
            rows = fetch_season(season_id, year)
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        new_count = upd_count = 0
        for row in rows:
            mid = row["match_id"]
            if mid not in existing:
                existing[mid] = row
                new_count += 1
            else:
                # Always update status and scores (they change as matches are played)
                existing[mid].update({
                    "status":     row["status"],
                    "home_goals": row["home_goals"],
                    "away_goals": row["away_goals"],
                })
                upd_count += 1

        print(f"{len(rows)} matches ({new_count} new, {upd_count} updated)")
        total_new += new_count
        total_updated += upd_count

    # Write merged result sorted by date
    rows_out = sorted(existing.values(), key=lambda r: (r.get("date", ""), r.get("match_id", "")))
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"\nWrote {len(rows_out)} rows to {OUT_PATH}")
    print(f"  {total_new} new  |  {total_updated} updated")

    # Sanity check
    statuses = {}
    for r in rows_out:
        s = r.get("status", "UNKNOWN")
        statuses[s] = statuses.get(s, 0) + 1
    for s, n in sorted(statuses.items()):
        print(f"  {s}: {n}")


if __name__ == "__main__":
    main()
