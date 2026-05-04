"""
Backfill historical match stats from CPL API (api-sdp.cplsoccer.com).

Fetches teamstats + header (attendance) for every FINISHED match across all
seasons and writes two CSV files:

  data/matches/match_teamstats_history.csv  — per-match team-level stats
  data/matches/match_header_history.csv     — per-match metadata (attendance, etc.)

Run:
    python3 scripts/fetch_match_stats.py

Options:
    --seasons 2019 2024 2025   fetch only specific seasons
    --resume                   skip matches already in output CSVs
    --teamstats-only           skip header fetch (faster)
    --delay 0.3                seconds between requests (default 0.25)
"""

import argparse
import csv
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "https://api-sdp.cplsoccer.com/v1/cpl/football"
HEADERS = {
    "Origin": "https://www.cplsoccer.com",
    "Referer": "https://www.cplsoccer.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.6 Safari/605.1.15"
    ),
    "Accept": "*/*",
}

SEASONS = {
    2019: "cpl::Football_Season::c8c9bdc288f34aa89073a8bd89d2da3e",
    2020: "cpl::Football_Season::11aa5cc094d0481fa8e73d326763584f",
    2021: "cpl::Football_Season::2f07c39671b84933ad7bb1e1958a7427",
    2022: "cpl::Football_Season::046f0ab31ba641c7b7bf27eb0dda4b9d",
    2023: "cpl::Football_Season::fc0855108c9044218a84fc5d2bee0000",
    2024: "cpl::Football_Season::6fb9e6fae4f24ce9bf4fa3172616a762",
    2025: "cpl::Football_Season::fd43e1d61dfe4396a7356bc432de0007",
    2026: "cpl::Football_Season::c479ab0916a24c3390f1ce2c021ace54",
}

# Teamstats fields to extract (statsId -> csv column name)
TEAMSTATS_FIELDS = {
    "possession-perc":              "possession_pct",
    "shots":                        "shots",
    "shots-on-goal":                "shots_on_target",
    "shots-at-goal-inside-box":     "shots_inside_box",
    "shots-at-goal-outside-box":    "shots_outside_box",
    "blocked-shots":                "blocked_shots",
    "big-chances":                  "big_chances",
    "chances-created":              "chances_created",
    "expected-goals":               "xg_api",
    "total-passes":                 "passes",
    "passing-accuracy-perc":        "pass_accuracy_pct",
    "corners":                      "corners",
    "crosses":                      "crosses",
    "fouls":                        "fouls",
    "yellow-cards":                 "yellow_cards",
    "red-cards":                    "red_cards",
    "offsides":                     "offsides",
    "saves":                        "saves",
    "clearences":                   "clearances",
    "duels-won":                    "duels_won",
    "tackles-total":                "tackles",
    "tackles-successful":           "tackles_successful",
    "key-passes":                   "key_passes",
    "penalty-goals":                "penalty_goals",
    "own-goals":                    "own_goals",
    "touches-opponent-box":         "touches_opp_box",
    "aerial-duels-won-perc":        "aerial_duels_won_pct",
    "counter-attacks":              "counter_attacks",
    "goals-scored":                 "goals",
}

DATA_DIR = Path(__file__).parent.parent / "data" / "matches"
TEAMSTATS_CSV = DATA_DIR / "match_teamstats_history.csv"
HEADER_CSV = DATA_DIR / "match_header_history.csv"


def fetch_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"    HTTP {e.code}: {url}")
        return None
    except Exception as e:
        print(f"    ERR: {e} — {url}")
        return None


def parse_teamstats(data: dict) -> tuple[dict, dict]:
    """Returns (home_stats, away_stats) dicts keyed by csv column name."""
    home, away = {}, {}
    stats_by_id = {s["statsId"]: s for s in data.get("stats", [])}
    for stats_id, col in TEAMSTATS_FIELDS.items():
        s = stats_by_id.get(stats_id)
        home[f"home_{col}"] = s["statsValueHome"] if s else None
        away[f"away_{col}"] = s["statsValueAway"] if s else None

    # Calculated xG from shot location (fallback if api xg is 0)
    h_ibox = (stats_by_id.get("shots-at-goal-inside-box") or {}).get("statsValueHome", 0) or 0
    h_obox = (stats_by_id.get("shots-at-goal-outside-box") or {}).get("statsValueHome", 0) or 0
    h_sot  = (stats_by_id.get("shots-on-goal") or {}).get("statsValueHome", 0) or 0
    a_ibox = (stats_by_id.get("shots-at-goal-inside-box") or {}).get("statsValueAway", 0) or 0
    a_obox = (stats_by_id.get("shots-at-goal-outside-box") or {}).get("statsValueAway", 0) or 0
    a_sot  = (stats_by_id.get("shots-on-goal") or {}).get("statsValueAway", 0) or 0
    home["home_xg_calc"] = round(h_ibox * 0.12 + h_obox * 0.03 + h_sot * 0.05, 3)
    away["away_xg_calc"] = round(a_ibox * 0.12 + a_obox * 0.03 + a_sot * 0.05, 3)

    return home, away


def parse_header(data: dict) -> dict:
    """Extracts attendance and basic match metadata from header response."""
    home_d = data.get("home", {})
    away_d = data.get("away", {})
    return {
        "attendance":       data.get("attendance"),
        "phase":            data.get("phase"),
        "additional_time":  data.get("additionalTime"),
        "win_reason":       data.get("winReason"),
        "home_red_cards":   len(home_d.get("redCards", [])),
        "away_red_cards":   len(away_d.get("redCards", [])),
        "home_scorers":     ",".join(
            f"{g.get('shortName','?')}({e['time']})"
            for g in home_d.get("scores", [])
            for e in g.get("events", [])
            if e.get("type") == "goal"
        ),
        "away_scorers":     ",".join(
            f"{g.get('shortName','?')}({e['time']})"
            for g in away_d.get("scores", [])
            for e in g.get("events", [])
            if e.get("type") == "goal"
        ),
    }


def load_existing_ids(csv_path: Path) -> set[str]:
    if not csv_path.exists():
        return set()
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        return {row["match_id"] for row in reader}


def build_teamstats_columns() -> list[str]:
    base = ["match_id", "season_id", "season", "date", "home_team", "away_team",
            "home_goals", "away_goals", "has_data"]
    for col in TEAMSTATS_FIELDS.values():
        base.append(f"home_{col}")
        base.append(f"away_{col}")
    base += ["home_xg_calc", "away_xg_calc"]
    return base


def build_header_columns() -> list[str]:
    return ["match_id", "season_id", "season", "date", "home_team", "away_team",
            "attendance", "phase", "additional_time", "win_reason",
            "home_red_cards", "away_red_cards", "home_scorers", "away_scorers"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", nargs="+", type=int, default=None,
                        help="Seasons to fetch (default: all)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip match_ids already in output CSVs")
    parser.add_argument("--teamstats-only", action="store_true",
                        help="Skip header fetch")
    parser.add_argument("--delay", type=float, default=0.25,
                        help="Seconds between API requests (default 0.25)")
    args = parser.parse_args()

    target_seasons = {y: sid for y, sid in SEASONS.items()
                      if args.seasons is None or y in args.seasons}

    # Load existing match IDs if resuming
    existing_ts = load_existing_ids(TEAMSTATS_CSV) if args.resume else set()
    existing_hd = load_existing_ids(HEADER_CSV) if args.resume else set()

    # Open CSV writers (append if resuming, write if fresh)
    ts_mode = "a" if args.resume and TEAMSTATS_CSV.exists() else "w"
    hd_mode = "a" if args.resume and HEADER_CSV.exists() else "w"

    ts_cols = build_teamstats_columns()
    hd_cols = build_header_columns()

    ts_file = open(TEAMSTATS_CSV, ts_mode, newline="")
    hd_file = open(HEADER_CSV, hd_mode, newline="") if not args.teamstats_only else None

    ts_writer = csv.DictWriter(ts_file, fieldnames=ts_cols, extrasaction="ignore")
    hd_writer = csv.DictWriter(hd_file, fieldnames=hd_cols, extrasaction="ignore") if hd_file else None

    if ts_mode == "w":
        ts_writer.writeheader()
    if hd_writer and hd_mode == "w":
        hd_writer.writeheader()

    total_fetched = 0
    total_skipped = 0
    total_no_data = 0

    try:
        for year, sid in sorted(target_seasons.items()):
            print(f"\n=== Season {year} ===")
            data = fetch_json(f"{BASE_URL}/seasons/{sid}/matches?locale=en-US")
            if not data:
                print(f"  Failed to fetch match list for {year}")
                continue

            matches = [m for m in data.get("matches", []) if m.get("status") == "FINISHED"]
            print(f"  {len(matches)} finished matches")

            for i, m in enumerate(matches, 1):
                mid = m["matchId"]
                date = (m.get("matchDateLocal") or "")[:10]
                home = m.get("home", {}).get("shortName") or m.get("home", {}).get("officialName", "")
                away = m.get("away", {}).get("shortName") or m.get("away", {}).get("officialName", "")
                hg = m.get("homeScorePush", "")
                ag = m.get("awayScorePush", "")

                base_row = {
                    "match_id": mid, "season_id": sid, "season": year,
                    "date": date, "home_team": home, "away_team": away,
                    "home_goals": hg, "away_goals": ag,
                }

                # Teamstats
                if mid not in existing_ts:
                    ts_data = fetch_json(
                        f"{BASE_URL}/seasons/{sid}/match/{mid}/teamstats?locale=en-US"
                    )
                    time.sleep(args.delay)

                    if ts_data:
                        home_stats, away_stats = parse_teamstats(ts_data)
                        shots = home_stats.get("home_shots")
                        has_data = 1 if shots and shots > 0 else 0
                        row = {**base_row, "has_data": has_data, **home_stats, **away_stats}
                        ts_writer.writerow(row)
                        ts_file.flush()
                        total_fetched += 1
                        if not has_data:
                            total_no_data += 1
                        status = "ok" if has_data else "empty"
                    else:
                        row = {**base_row, "has_data": 0}
                        ts_writer.writerow(row)
                        ts_file.flush()
                        total_no_data += 1
                        status = "404"

                    if i % 20 == 0 or i == len(matches):
                        print(f"  [{i}/{len(matches)}] {date} {home} v {away} — {status}")
                else:
                    total_skipped += 1

                # Header (attendance + scorers)
                if hd_writer and mid not in existing_hd:
                    hd_data = fetch_json(
                        f"{BASE_URL}/seasons/{sid}/matches/{mid}/header?locale=en-US"
                    )
                    time.sleep(args.delay)
                    if hd_data:
                        hd_row = {**base_row, **parse_header(hd_data)}
                        hd_writer.writerow(hd_row)
                        hd_file.flush()

    finally:
        ts_file.close()
        if hd_file:
            hd_file.close()

    print(f"\nDone. fetched={total_fetched}, skipped={total_skipped}, no-data={total_no_data}")
    print(f"Teamstats → {TEAMSTATS_CSV}")
    if not args.teamstats_only:
        print(f"Headers   → {HEADER_CSV}")


if __name__ == "__main__":
    main()
