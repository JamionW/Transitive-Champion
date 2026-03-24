"""
transitive_champion pipeline

Downloads the schochastics football-data parquet file, merges it with
manually maintained match results, US Open Cup data, transfermarkt-datasets,
and API-Football cached results, normalizes team names, and outputs a single
JSON file the React app consumes.

Data sources (in merge order):
    1. schochastics/football-data parquet (1.2M+ historical matches)
    2. transfermarkt-datasets games.csv.gz (~80k European/intl matches)
    3. US Open Cup results from pipeline/data/us_open_cup.json
    4. API-Football cached results from maintenance.py
    5. Manual overrides from pipeline/data/manual_matches.json

Usage:
    python pipeline.py                    # full run: download + build
    python pipeline.py --skip-download    # rebuild from cached data
    python pipeline.py --stats            # print dataset statistics only
    python pipeline.py --no-transfermarkt # skip transfermarkt source
    python pipeline.py --no-open-cup      # skip US Open Cup source
    python pipeline.py --no-api-football  # skip API-Football cache

Output:
    output/graph_data.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import pyarrow.parquet as pq
except ImportError:
    print("pyarrow is required. Install it with: pip install pyarrow")
    sys.exit(1)

# --- paths ---

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

REPO_URL = "https://github.com/schochastics/football-data.git"
PARQUET_PATH = CACHE_DIR / "football-repo" / "data" / "results" / "games.parquet"

MANUAL_MATCHES_PATH = DATA_DIR / "manual_matches.json"
CHAMPIONSHIPS_PATH = DATA_DIR / "championships.json"
TEAM_NAME_MAP_PATH = DATA_DIR / "team_name_map.json"
OUTPUT_PATH = OUTPUT_DIR / "graph_data.json"


def ensure_dirs():
    for d in [CACHE_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# --- download ---

def download_parquet(force=False):
    repo_dir = CACHE_DIR / "football-repo"
    if PARQUET_PATH.exists() and not force:
        size_mb = PARQUET_PATH.stat().st_size / (1024 * 1024)
        print(f"cached parquet found ({size_mb:.1f} MB), skipping download")
        return

    import subprocess

    if repo_dir.exists():
        import shutil
        shutil.rmtree(repo_dir)

    print(f"cloning repo (sparse, LFS) for parquet file...")
    print("(this may take a minute on first run)")

    subprocess.run(["git", "lfs", "install"], check=True, capture_output=True)
    subprocess.run([
        "git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
        REPO_URL, str(repo_dir)
    ], check=True, capture_output=True)
    subprocess.run(
        ["git", "sparse-checkout", "set", "data/results"],
        cwd=str(repo_dir), check=True, capture_output=True
    )
    subprocess.run(
        ["git", "lfs", "pull"],
        cwd=str(repo_dir), check=True, capture_output=True
    )

    if not PARQUET_PATH.exists():
        print(f"ERROR: parquet not found after clone at {PARQUET_PATH}")
        sys.exit(1)

    size_mb = PARQUET_PATH.stat().st_size / (1024 * 1024)
    print(f"downloaded {size_mb:.1f} MB parquet via git LFS")


# --- team name normalization ---

def load_name_map():
    with open(TEAM_NAME_MAP_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def normalize_name(name, name_map):
    return name_map.get(name, name)


# --- parquet parsing ---

def parse_parquet(name_map):
    """
    Read the schochastics parquet file and extract wins.
    Only keeps matches where one side scored strictly more than the other.
    """
    print(f"reading {PARQUET_PATH}...")
    table = pq.read_table(PARQUET_PATH)
    df_columns = table.column_names
    print(f"columns found: {df_columns}")

    col_map = {}
    for c in df_columns:
        cl = c.lower()
        if cl in ("date",):
            col_map["date"] = c
        elif cl in ("home",):
            col_map["home"] = c
        elif cl in ("away",):
            col_map["away"] = c
        elif cl in ("hg", "gh", "homegoals", "home_goals", "fthg"):
            col_map["hg"] = c
        elif cl in ("ag", "ga", "awaygoals", "away_goals", "ftag"):
            col_map["ag"] = c
        elif cl in ("tournament", "competition", "league", "comp"):
            col_map["comp"] = c
        elif cl in ("country",):
            col_map["country"] = c

    required = ["date", "home", "away", "hg", "ag"]
    missing = [k for k in required if k not in col_map]
    if missing:
        print(f"ERROR: could not find columns for: {missing}")
        print(f"available columns: {df_columns}")
        sys.exit(1)

    dates = table.column(col_map["date"]).to_pylist()
    homes = table.column(col_map["home"]).to_pylist()
    aways = table.column(col_map["away"]).to_pylist()
    hgs = table.column(col_map["hg"]).to_pylist()
    ags = table.column(col_map["ag"]).to_pylist()
    comps = table.column(col_map.get("comp", col_map.get("country", "date"))).to_pylist() if "comp" in col_map else ["Unknown"] * len(dates)

    matches = []
    skipped = 0

    for i in range(len(dates)):
        hg = hgs[i]
        ag = ags[i]

        if hg is None or ag is None or hg == ag:
            skipped += 1
            continue

        home = normalize_name(str(homes[i]).strip(), name_map)
        away = normalize_name(str(aways[i]).strip(), name_map)
        date_val = str(dates[i])[:10] if dates[i] else "unknown"
        comp = str(comps[i]) if comps[i] else "Unknown"

        if hg > ag:
            matches.append({
                "winner": home, "loser": away,
                "ws": int(hg), "ls": int(ag),
                "date": date_val, "comp": comp,
            })
        else:
            matches.append({
                "winner": away, "loser": home,
                "ws": int(ag), "ls": int(hg),
                "date": date_val, "comp": comp,
            })

    print(f"parsed {len(matches)} decisive matches ({skipped} draws/nulls skipped)")
    return matches


# --- manual matches ---

def load_manual_matches():
    if not MANUAL_MATCHES_PATH.exists():
        print("no manual_matches.json found, skipping")
        return []

    with open(MANUAL_MATCHES_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    matches = [m for m in raw if "winner" in m]
    print(f"loaded {len(matches)} manual match(es)")
    return matches


# --- championships ---

def load_championships():
    with open(CHAMPIONSHIPS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    champs = [c for c in raw if "team" in c]
    print(f"loaded {len(champs)} championship entries")
    return champs


# --- graph compression ---

def compress_to_best_wins(matches):
    """
    For each (winner, loser, year) triple, keep only the match with the
    highest goal margin. Preserves yearly temporal resolution for
    time-constrained transitive chains while still compressing significantly.
    """
    best = {}
    for m in matches:
        year = m["date"][:4] if m.get("date") else "unknown"
        key = (m["winner"], m["loser"], year)
        margin = m["ws"] - m["ls"]
        if key not in best or margin > best[key]["margin"]:
            best[key] = {**m, "margin": margin}

    compressed = [{k: v for k, v in m.items() if k != "margin"} for m in best.values()]
    print(f"compressed {len(matches)} matches to {len(compressed)} best-margin-per-year edges")
    return compressed


# --- output ---

def build_output(matches, championships):
    teams = set()
    for m in matches:
        teams.add(m["winner"])
        teams.add(m["loser"])
    for c in championships:
        teams.add(c["team"])

    output = {
        "meta": {
            "match_count": len(matches),
            "team_count": len(teams),
            "championship_count": len(championships),
        },
        "matches": matches,
        "championships": championships,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"wrote {OUTPUT_PATH} ({size_mb:.1f} MB)")
    print(f"  {output['meta']['match_count']} edges, {output['meta']['team_count']} teams, {output['meta']['championship_count']} championships")


# --- stats ---

def print_stats(matches, championships):
    teams = set()
    for m in matches:
        teams.add(m["winner"])
        teams.add(m["loser"])

    comps = set(m.get("comp", "Unknown") for m in matches)
    trophies = set(c["trophy"] for c in championships)

    # count by source (approximate via comp name patterns)
    us_comps = {"US Open Cup", "MLS", "MLS NEXT Pro", "USL Championship", "USL League One"}
    us_edges = sum(1 for m in matches if m.get("comp") in us_comps)

    print(f"\n--- dataset statistics ---")
    print(f"total edges (best-margin-per-year): {len(matches)}")
    print(f"unique teams:                    {len(teams)}")
    print(f"unique competitions:             {len(comps)}")
    print(f"championship entries:            {len(championships)}")
    print(f"unique trophies tracked:         {len(trophies)}")
    print(f"US-competition edges (approx):   {us_edges}")

    champ_teams = set(c["team"] for c in championships)
    in_graph = champ_teams & teams
    missing = champ_teams - teams
    print(f"championship teams in graph:     {len(in_graph)}/{len(champ_teams)}")
    if missing:
        print(f"championship teams NOT in graph: {sorted(missing)}")


# --- main ---

def main():
    parser = argparse.ArgumentParser(description="transitive champion data pipeline")
    parser.add_argument("--skip-download", action="store_true", help="use cached parquet")
    parser.add_argument("--force-download", action="store_true", help="re-download parquet")
    parser.add_argument("--stats", action="store_true", help="print stats only, no output")
    parser.add_argument("--no-transfermarkt", action="store_true", help="skip transfermarkt source")
    parser.add_argument("--no-open-cup", action="store_true", help="skip US Open Cup source")
    parser.add_argument("--no-api-football", action="store_true", help="skip API-Football cache")
    args = parser.parse_args()

    ensure_dirs()

    name_map = load_name_map()
    print(f"loaded {len(name_map)} team name mappings")

    # --- source 1: schochastics parquet ---
    if not args.skip_download:
        download_parquet(force=args.force_download)

    if not PARQUET_PATH.exists():
        print(f"ERROR: parquet file not found at {PARQUET_PATH}")
        print("run without --skip-download first")
        sys.exit(1)

    parquet_matches = parse_parquet(name_map)

    # --- source 2: transfermarkt-datasets ---
    tm_matches = []
    if not args.no_transfermarkt:
        try:
            from sources.transfermarkt import parse_matches as tm_parse
            tm_matches = tm_parse(CACHE_DIR, name_map)
        except Exception as e:
            print(f"transfermarkt-datasets: failed ({e}), skipping")

    # --- source 3: US Open Cup ---
    usoc_matches = []
    if not args.no_open_cup:
        try:
            from sources.thecup import load_matches as usoc_load
            usoc_matches = usoc_load(name_map)
        except Exception as e:
            print(f"us open cup: failed ({e}), skipping")

    # --- source 4: API-Football cache ---
    apif_matches = []
    if not args.no_api_football:
        try:
            from sources.api_football import load_matches as apif_load
            apif_matches = apif_load(name_map)
        except Exception as e:
            print(f"api-football: failed ({e}), skipping")

    # --- source 5: manual overrides ---
    manual_matches = load_manual_matches()

    # --- merge all sources ---
    # order matters: later sources can override earlier ones during compression
    # (manual matches last so they always take precedence)
    all_matches = parquet_matches + tm_matches + usoc_matches + apif_matches + manual_matches

    print(f"\nmerged sources: {len(parquet_matches)} parquet + {len(tm_matches)} transfermarkt"
          f" + {len(usoc_matches)} open cup + {len(apif_matches)} api-football"
          f" + {len(manual_matches)} manual = {len(all_matches)} total")

    # compress to best margin per edge
    compressed = compress_to_best_wins(all_matches)

    # load championships
    championships = load_championships()

    if args.stats:
        print_stats(compressed, championships)
        return

    build_output(compressed, championships)
    print_stats(compressed, championships)
    print("\ndone. copy output/graph_data.json into your React app's public/ directory.")


if __name__ == "__main__":
    main()