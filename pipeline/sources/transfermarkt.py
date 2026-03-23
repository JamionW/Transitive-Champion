"""
Transfermarkt-datasets source.

Downloads the weekly-updated games.csv.gz from dcaribou/transfermarkt-datasets
and converts it into match dicts compatible with the pipeline.

Coverage: European top flights, domestic cups, Champions League, Europa League,
international tournaments. ~80k games. No US domestic leagues.

Source: https://github.com/dcaribou/transfermarkt-datasets
License: CC-BY-4.0 (Transfermarkt data)
"""

import csv
import gzip
import io
import os
from pathlib import Path

GAMES_URL = (
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/games.csv.gz"
)
COMPETITIONS_URL = (
    "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/competitions.csv.gz"
)


def download_csv_gz(url, cache_path, force=False):
    """Download a gzipped CSV to cache_path. Returns the decompressed text."""
    if cache_path.exists() and not force:
        size_kb = cache_path.stat().st_size / 1024
        print(f"  cached: {cache_path.name} ({size_kb:.0f} KB)")
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    import urllib.request

    print(f"  downloading {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "transitive-champion-pipeline/1.0"})
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()

    text = gzip.decompress(raw).decode("utf-8")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"  saved {len(text) // 1024} KB to {cache_path}")
    return text


def load_competition_names(cache_dir):
    """Build a map from competition_id to human-readable name."""
    text = download_csv_gz(
        COMPETITIONS_URL, cache_dir / "tm_competitions.csv"
    )
    reader = csv.DictReader(io.StringIO(text))
    comp_map = {}
    for row in reader:
        cid = row.get("competition_id", "")
        name = row.get("name", "").replace("-", " ").title()
        comp_map[cid] = name
    return comp_map


def parse_matches(cache_dir, name_map, force_download=False):
    """
    Download and parse transfermarkt-datasets games.csv.gz.

    Returns a list of match dicts:
      {winner, loser, ws, ls, date, comp}

    Draws and rows with missing scores are skipped.
    """
    print("transfermarkt-datasets:")
    comp_names = load_competition_names(cache_dir)

    text = download_csv_gz(
        GAMES_URL, cache_dir / "tm_games.csv", force=force_download
    )

    reader = csv.DictReader(io.StringIO(text))
    matches = []
    skipped = 0

    for row in reader:
        hg_raw = row.get("home_club_goals", "")
        ag_raw = row.get("away_club_goals", "")

        if not hg_raw or not ag_raw:
            skipped += 1
            continue

        try:
            hg = int(hg_raw)
            ag = int(ag_raw)
        except ValueError:
            skipped += 1
            continue

        if hg == ag:
            skipped += 1
            continue

        home = (row.get("home_club_name") or "").strip()
        away = (row.get("away_club_name") or "").strip()
        if not home or not away:
            skipped += 1
            continue

        # apply the shared name map
        home = name_map.get(home, home)
        away = name_map.get(away, away)

        date_val = (row.get("date") or "unknown")[:10]
        comp_id = row.get("competition_id", "")
        comp = comp_names.get(comp_id, comp_id)

        if hg > ag:
            matches.append({
                "winner": home, "loser": away,
                "ws": hg, "ls": ag,
                "date": date_val, "comp": comp,
            })
        else:
            matches.append({
                "winner": away, "loser": home,
                "ws": ag, "ls": hg,
                "date": date_val, "comp": comp,
            })

    print(f"  parsed {len(matches)} decisive matches ({skipped} draws/nulls skipped)")
    return matches
