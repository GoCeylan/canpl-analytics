#!/usr/bin/env python3
"""
Extract historical referee data for CPL matches.

Outputs a CSV with one row per finished match, containing the main referee.
"""

import argparse
import csv
import logging
from datetime import datetime
from typing import Dict, Optional

from canpl_api_client import CanPLAPIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _parse_date(match_date_utc: Optional[str]) -> str:
    if not match_date_utc:
        return ""
    return match_date_utc[:10]


def _extract_main_referee(match_facts: Dict) -> Dict[str, str]:
    """
    Return a dict with referee_id, referee_name, referee_short_name.
    Empty strings if not found.
    """
    referees = match_facts.get("referees") or []
    for ref in referees:
        if not isinstance(ref, dict):
            continue
        role_label = str(ref.get("roleLabel") or ref.get("role") or "").strip()
        if role_label.lower() == "referee":
            first = (ref.get("mediaFirstName") or "").strip()
            last = (ref.get("mediaLastName") or "").strip()
            name = " ".join([p for p in [first, last] if p]).strip()
            return {
                "referee_id": ref.get("refereeId", "") or "",
                "referee_name": name,
                "referee_short_name": ref.get("shortName", "") or "",
            }
    return {"referee_id": "", "referee_name": "", "referee_short_name": ""}


def extract_referees(start_year: int, end_year: int, output_path: str, limit: Optional[int] = None) -> None:
    client = CanPLAPIClient()
    rows = []

    for year in range(start_year, end_year + 1):
        season_id = client.get_season_id(year)
        if not season_id:
            logger.warning("Skipping unknown season: %s", year)
            continue

        logger.info("Fetching matches for %s...", year)
        matches = client.get_matches(season_id)
        finished = [m for m in matches if m.get("status") == "FINISHED"]

        if limit:
            finished = finished[:limit]

        logger.info("  %s finished matches", len(finished))

        for match in finished:
            match_id = match.get("matchId")
            if not match_id:
                continue

            try:
                facts = client.get_match_facts(season_id, match_id)
            except Exception as exc:
                logger.warning("Matchfacts failed for %s: %s", match_id, exc)
                continue

            ref = _extract_main_referee(facts)

            rows.append({
                "season": year,
                "match_id": match_id,
                "date": _parse_date(match.get("matchDateUtc")),
                "home_team": match.get("home", {}).get("officialName", ""),
                "away_team": match.get("away", {}).get("officialName", ""),
                "referee_id": ref["referee_id"],
                "referee_name": ref["referee_name"],
                "referee_short_name": ref["referee_short_name"],
            })

    logger.info("Writing %s rows to %s", len(rows), output_path)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "season",
                "match_id",
                "date",
                "home_team",
                "away_team",
                "referee_id",
                "referee_name",
                "referee_short_name",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract CPL referees from matchfacts endpoint.")
    parser.add_argument("--start-year", type=int, default=2019)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument(
        "--output",
        default="data/matches/cpl_referees_2019_2025.csv",
        help="Output CSV path",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit matches per season")
    args = parser.parse_args()

    if args.start_year > args.end_year:
        raise SystemExit("start-year must be <= end-year")

    extract_referees(args.start_year, args.end_year, args.output, args.limit)


if __name__ == "__main__":
    main()
