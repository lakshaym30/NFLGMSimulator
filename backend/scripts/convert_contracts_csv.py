"""Convert a Spotrac/OTC-style CSV export into normalized contract JSON."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a league-wide contracts CSV into JSON."
    )
    parser.add_argument("--csv", required=True, type=Path, help="Source CSV file")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination JSON file (default data/contracts_league_YYYY-MM-DD.json).",
    )
    parser.add_argument(
        "--as-of-date",
        type=str,
        default=None,
        help="ISO date for the dataset (defaults to today).",
    )
    parser.add_argument(
        "--source-name",
        type=str,
        default="Manual CSV Export",
        help="Name of the contract data source.",
    )
    parser.add_argument(
        "--source-url",
        type=str,
        default=None,
        help="Where the CSV originated (Spotrac link, etc.).",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=datetime.today().year,
        help="League year used when constructing placeholder contract seasons.",
    )
    return parser.parse_args()


YEAR_PATTERN = re.compile(r"(20\d{2})")
YEAR_FIELD_KEYWORDS: Dict[str, List[str]] = {
    "base_salary": ["base", "base salary"],
    "signing_proration": ["proration", "prorated", "signing"],
    "roster_bonus": ["roster"],
    "workout_bonus": ["workout"],
    "other_bonus": ["option", "other", "misc"],
    "cap_hit": ["cap hit", "cap"],
    "cash": ["cash"],
    "guaranteed": ["guaranteed"],
    "rolling_guarantee": ["rolling", "remaining guarantee"],
}
GENERAL_FIELDS = {
    "player": ["player", "name"],
    "position": ["pos", "position"],
    "team": ["team"],
    "total_value": ["total value", "contract total", "value"],
    "apy": ["apy", "average per year"],
    "total_guaranteed": ["total guaranteed"],
    "avg_guarantee_per_year": ["avg guarantee per year", "avg guarantee", "avg. guarantee/year"],
    "percent_guaranteed": ["% guaranteed", "percent guaranteed"],
}


def normalize_header(header: Optional[str]) -> str:
    if not header:
        return ""
    cleaned = header.replace("\xa0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def slug_header(header: Optional[str]) -> str:
    normalized = normalize_header(header)
    slug = re.sub(r"[^a-z0-9]+", "_", normalized)
    return slug.strip("_")


def clean_currency(value: Optional[str]) -> Optional[float]:
    if value is None:
        return 0.0
    if value.strip() in {"", "$0", "$0.0", "$0.00"}:
        return 0.0
    sanitized = (
        value.replace("$", "")
        .replace(",", "")
        .replace("%", "")
        .replace("\xa0", "")
        .strip()
    )
    if not sanitized:
        return 0.0
    try:
        return float(sanitized)
    except ValueError:
        return None


def finalize_year_entry(season: int, values: Dict[str, Optional[float]]) -> Dict[str, Any]:
    entry = {
        "season": season,
        "base_salary": values.get("base_salary") or 0.0,
        "signing_proration": values.get("signing_proration") or 0.0,
        "roster_bonus": values.get("roster_bonus") or 0.0,
        "workout_bonus": values.get("workout_bonus") or 0.0,
        "other_bonus": values.get("other_bonus") or 0.0,
        "cash": values.get("cash") or 0.0,
        "cap_hit": values.get("cap_hit") or 0.0,
        "guaranteed": values.get("guaranteed") or 0.0,
        "rolling_guarantee": values.get("rolling_guarantee") or 0.0,
        "is_void_year": bool(values.get("is_void_year", False)),
    }
    if not entry["cash"]:
        entry["cash"] = round(entry["base_salary"] + entry["roster_bonus"] + entry["workout_bonus"] + entry["other_bonus"], 2)
    if not entry["cap_hit"]:
        entry["cap_hit"] = round(
            entry["base_salary"]
            + entry["signing_proration"]
            + entry["roster_bonus"]
            + entry["workout_bonus"]
            + entry["other_bonus"],
            2,
        )
    if not entry["rolling_guarantee"]:
        entry["rolling_guarantee"] = entry["guaranteed"]
    return entry


def build_contract_years(
    total_value: Optional[float], apy: Optional[float], start_year: int
) -> List[Dict[str, Any]]:
    if not total_value and not apy:
        return []
    inferred_total = total_value or (apy or 0)
    inferred_length = 1
    if apy and apy > 0:
        inferred_length = max(int(round(inferred_total / apy)) or 1, 1)
    annual = (inferred_total or 0) / inferred_length if inferred_length else (apy or 0)
    years: List[Dict[str, Any]] = []
    for offset in range(inferred_length):
        years.append(
            finalize_year_entry(
                start_year + offset,
                {
                    "base_salary": round(annual, 2),
                    "signing_proration": 0.0,
                    "cap_hit": round(annual, 2),
                    "cash": round(annual, 2),
                },
            )
        )
    return years


def detect_year_columns(fieldnames: List[str]) -> Dict[int, Dict[str, str]]:
    mapping: Dict[int, Dict[str, str]] = defaultdict(dict)
    for header in fieldnames or []:
        if not header:
            continue
        normalized = normalize_header(header)
        match = YEAR_PATTERN.search(normalized)
        if not match:
            continue
        season = int(match.group(1))
        remainder = normalized.replace(match.group(1), "").strip(" -_/")
        for attribute, keywords in YEAR_FIELD_KEYWORDS.items():
            if any(keyword in remainder for keyword in keywords):
                mapping[season][attribute] = header
                break
    return mapping


def normalize_row(row: Dict[str, str]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in row.items():
        slug = slug_header(key)
        if not slug:
            continue
        normalized[slug] = (value or "").strip()
    return normalized


def extract_general_field(normalized_row: Dict[str, str], name: str) -> str:
    aliases = GENERAL_FIELDS.get(name, [name])
    for alias in aliases:
        for key, value in normalized_row.items():
            if alias == key or alias.replace(" ", "_") == key:
                if value:
                    return value
        for key, value in normalized_row.items():
            if alias.replace(" ", "") in key and value:
                return value
    return ""


def parse_contract_years(row: Dict[str, str], year_columns: Dict[int, Dict[str, str]]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for season in sorted(year_columns.keys()):
        columns = year_columns[season]
        values: Dict[str, Optional[float]] = {}
        for attribute, header in columns.items():
            values[attribute] = clean_currency(row.get(header, ""))
        entries.append(finalize_year_entry(season, values))
    return entries


def load_contracts(csv_path: Path, start_year: int) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        year_columns = detect_year_columns(reader.fieldnames or [])
        for row in reader:
            normalized = normalize_row(row)
            player = extract_general_field(normalized, "player")
            team = extract_general_field(normalized, "team").replace("\xa0", " ").strip()
            if not player or not team:
                continue
            position = extract_general_field(normalized, "position")
            total_value = clean_currency(
                normalized.get("total_value")
                or normalized.get("total_value_contract_total")
                or normalized.get("value")
            )
            apy = clean_currency(normalized.get("apy"))
            total_guaranteed = clean_currency(normalized.get("total_guaranteed"))
            avg_guarantee = clean_currency(normalized.get("avg_guarantee_per_year"))
            percent_guaranteed = clean_currency(normalized.get("percent_guaranteed"))
            contract_years = parse_contract_years(row, year_columns)
            if not contract_years:
                contract_years = build_contract_years(total_value, apy, start_year)
            records.append(
                {
                    "player": player,
                    "position": position,
                    "team": team,
                    "total_value": total_value,
                    "apy": apy,
                    "total_guaranteed": total_guaranteed,
                    "avg_guarantee_per_year": avg_guarantee,
                    "percent_guaranteed": percent_guaranteed,
                    "contract_years": contract_years,
                }
            )
    return records


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def main() -> None:
    args = parse_args()
    records = load_contracts(args.csv, start_year=args.start_year)
    as_of = args.as_of_date or datetime.today().date().isoformat()
    output_path = args.output or Path("data") / f"contracts_league_{as_of}.json"
    payload = {
        "as_of_date": as_of,
        "source": {"name": args.source_name, "url": args.source_url},
        "contracts": records,
    }
    write_json(output_path, payload)
    print(f"Wrote {len(records)} contract rows to {output_path}")


if __name__ == "__main__":
    main()
