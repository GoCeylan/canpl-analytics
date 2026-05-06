"""Fetch finished 2026 CPL matches from the SDP API and append to cpl_all.csv.

Lives in canpl-analytics — owns its own data pipeline. Run by the
.github/workflows/update-data.yml cron, or manually from the repo root.

Usage:
    python scripts/update_match_data.py
"""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

_ROOT = Path(__file__).resolve().parents[1]

# SDP API constants (no auth required)
_API_BASE = "https://api-sdp.cplsoccer.com/v1/cpl/football"
_SEASON_ID_2026 = "cpl::Football_Season::c479ab0916a24c3390f1ce2c021ace54"


def _fetch_matches() -> list[dict]:
    """Fetch all 2026 matches from the public SDP API."""
    url = f"{_API_BASE}/seasons/{_SEASON_ID_2026}/matches"
    params = {"locale": "en-US"}
    time.sleep(1)
    resp = requests.get(url, params=params, timeout=30, headers={
        "Accept": "application/json",
        "Origin": "https://www.cplsoccer.com",
        "Referer": "https://www.cplsoccer.com/",
    })
    resp.raise_for_status()
    return resp.json().get("matches", [])

# Team name mapping: SDP officialName → cpl_all.csv canonical names
_ALIASES = {
    "Forge": "Forge FC",
    "Cavalry": "Cavalry FC",
    "Pacific": "Pacific FC",
    "Valour": "Valour FC",
    "Atlético Ottawa": "Atletico Ottawa",
    "HFX Wanderers": "HFX Wanderers FC",
    "York United": "Inter Toronto",
    "Supra du Québec": "Supra",
    "FC Edmonton": "FC Edmonton",
}

# Venue mapping from team name
_VENUES = {
    "Forge FC": "Hamilton Stadium",
    "Cavalry FC": "ATCO Field",
    "Pacific FC": "Starlight Stadium",
    "Atletico Ottawa": "TD Place",
    "Valour FC": "IG Field",
    "Inter Toronto": "York Lions Stadium",
    "HFX Wanderers FC": "Wanderers Grounds",
    "Vancouver FC": "Willoughby Community Park",
    "Supra": "Stade Boréale",
    "FC Edmonton": "Clarke Stadium",
}


def _normalize(name: str) -> str:
    return _ALIASES.get(name, name)


def main():
    csv_path = _ROOT / "data" / "matches" / "cpl_all.csv"
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        sys.exit(1)

    existing = pd.read_csv(csv_path, parse_dates=["date"])
    print(f"Existing matches: {len(existing)}")

    # Build set of existing (date, home, away) for dedup
    existing_keys = set(
        zip(
            existing["date"].dt.strftime("%Y-%m-%d"),
            existing["home_team"],
            existing["away_team"],
        )
    )

    # Fetch 2026 matches from API
    matches = _fetch_matches()
    finished = [m for m in matches if m.get("status") == "FINISHED"]
    print(f"Finished 2026 matches from API: {len(finished)}")

    new_rows = []
    for m in finished:
        home = _normalize(m["home"]["officialName"])
        away = _normalize(m["away"]["officialName"])
        date_str = m["matchDateUtc"][:10]

        if (date_str, home, away) in existing_keys:
            continue

        new_rows.append(
            {
                # Match the existing CSV's datetime format so downstream
                # parse_dates=['date'] consumers see a uniform datetime64 column.
                "date": pd.Timestamp(date_str),
                "home_team": home,
                "away_team": away,
                "home_goals": int(m.get("providerHomeScore", 0)),
                "away_goals": int(m.get("providerAwayScore", 0)),
                "season": 2026,
                "venue": _VENUES.get(home, ""),
            }
        )

    if not new_rows:
        print("No new matches to add.")
        return

    new_df = pd.DataFrame(new_rows)
    updated = pd.concat([existing, new_df], ignore_index=True)
    updated.to_csv(csv_path, index=False)
    print(f"Added {len(new_rows)} new matches. Total: {len(updated)}")

    for r in new_rows:
        print(f"  + {r['date']}  {r['home_team']} {r['home_goals']}-{r['away_goals']} {r['away_team']}")


if __name__ == "__main__":
    main()
