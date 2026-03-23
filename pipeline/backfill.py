"""
API-Football bulk backfill script.

Fetches match results across all configured leagues and seasons, with
checkpointing and budget management. Designed for the $10/mo plan
(7,500 requests/day, all seasons unlocked).

Usage:
    python backfill.py                  # run until budget exhausted
    python backfill.py --resume         # pick up where you left off (default)
    python backfill.py --reset          # clear checkpoint file and start over
    python backfill.py --plan           # show what would be fetched, no requests
    python backfill.py --budget 5000    # stop after 5000 requests (default: 7400)

Checkpoint: pipeline/cache/backfill_checkpoint.json
Output: pipeline/cache/api_football_matches.json (same file maintenance.py uses)

The script saves after every successful league/season fetch, so it's safe
to kill at any time. On next run it skips completed pairs.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
CHECKPOINT_PATH = CACHE_DIR / "backfill_checkpoint.json"
OUTPUT_PATH = CACHE_DIR / "api_football_matches.json"
ENV_PATH = BASE_DIR / ".env"

API_BASE = "https://v3.football.api-sports.io"
BUDGET_BUFFER = 100  # stop this many requests before the hard limit

# seasons to backfill (newest first so the most relevant data comes first)
SEASONS = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018]

# --- league registry ---
# priority 1: direct CFC connections and US pyramid
# priority 2: CONCACAF / Liga MX bridge
# priority 3: top 5 European leagues
# priority 4: European cups (cross-league bridges)
# priority 5: other major leagues and cups
# priority 6: secondary European leagues
# priority 7: everything else that adds graph depth

LEAGUES = [
    # priority 1: US pyramid
    {"id": 253, "name": "MLS", "priority": 1},
    {"id": 909, "name": "MLS NEXT Pro", "priority": 1},
    {"id": 257, "name": "US Open Cup", "priority": 1},
    {"id": 255, "name": "USL Championship", "priority": 1},
    {"id": 489, "name": "USL League One", "priority": 1},
    {"id": 256, "name": "USL League Two", "priority": 2},
    {"id": 1118, "name": "NPSL", "priority": 2},

    # priority 2: CONCACAF / Liga MX
    {"id": 16, "name": "CONCACAF Champions Cup", "priority": 2},
    {"id": 262, "name": "Liga MX", "priority": 2},
    {"id": 910, "name": "Leagues Cup", "priority": 2},
    {"id": 263, "name": "Liga MX Apertura", "priority": 3},
    {"id": 264, "name": "Liga MX Clausura", "priority": 3},

    # priority 3: top 5 European leagues
    {"id": 39, "name": "Premier League", "priority": 3},
    {"id": 140, "name": "La Liga", "priority": 3},
    {"id": 78, "name": "Bundesliga", "priority": 3},
    {"id": 135, "name": "Serie A", "priority": 3},
    {"id": 61, "name": "Ligue 1", "priority": 3},

    # priority 4: European cups
    {"id": 2, "name": "Champions League", "priority": 4},
    {"id": 3, "name": "Europa League", "priority": 4},
    {"id": 848, "name": "Europa Conference League", "priority": 4},
    {"id": 531, "name": "UEFA Super Cup", "priority": 5},

    # priority 4: domestic cups (cross-tier bridges within countries)
    {"id": 45, "name": "FA Cup", "priority": 4},
    {"id": 48, "name": "League Cup (EFL)", "priority": 5},
    {"id": 143, "name": "Copa del Rey", "priority": 5},
    {"id": 81, "name": "DFB Pokal", "priority": 5},
    {"id": 137, "name": "Coppa Italia", "priority": 5},
    {"id": 66, "name": "Coupe de France", "priority": 5},

    # priority 5: other major European leagues
    {"id": 40, "name": "Championship (England 2)", "priority": 5},
    {"id": 88, "name": "Eredivisie", "priority": 5},
    {"id": 94, "name": "Primeira Liga (Portugal)", "priority": 5},
    {"id": 179, "name": "Scottish Premiership", "priority": 5},
    {"id": 144, "name": "Belgian Pro League", "priority": 5},
    {"id": 203, "name": "Super Lig (Turkey)", "priority": 5},
    {"id": 235, "name": "Russian Premier Liga", "priority": 6},
    {"id": 207, "name": "Swiss Super League", "priority": 6},
    {"id": 218, "name": "Austrian Bundesliga", "priority": 6},
    {"id": 113, "name": "Allsvenskan (Sweden)", "priority": 6},
    {"id": 103, "name": "Eliteserien (Norway)", "priority": 6},
    {"id": 119, "name": "Danish Superliga", "priority": 6},

    # priority 5: South America
    {"id": 13, "name": "Copa Libertadores", "priority": 5},
    {"id": 11, "name": "Copa Sudamericana", "priority": 5},
    {"id": 71, "name": "Serie A (Brazil)", "priority": 5},
    {"id": 128, "name": "Liga Profesional (Argentina)", "priority": 5},

    # priority 5: international tournaments
    {"id": 1, "name": "World Cup", "priority": 5},
    {"id": 4, "name": "Euro Championship", "priority": 5},
    {"id": 9, "name": "Copa America", "priority": 5},
    {"id": 29, "name": "AFC Asian Cup", "priority": 6},
    {"id": 6, "name": "Africa Cup of Nations", "priority": 6},
    {"id": 15, "name": "FIFA Club World Cup", "priority": 5},

    # priority 6: second tier European (more graph edges)
    {"id": 41, "name": "League One (England 3)", "priority": 6},
    {"id": 42, "name": "League Two (England 4)", "priority": 6},
    {"id": 79, "name": "2. Bundesliga", "priority": 6},
    {"id": 141, "name": "La Liga 2", "priority": 6},
    {"id": 136, "name": "Serie B (Italy)", "priority": 6},
    {"id": 62, "name": "Ligue 2 (France)", "priority": 6},

    # priority 6: other Americas
    {"id": 239, "name": "MLS Canada", "priority": 6},
    {"id": 72, "name": "Serie B (Brazil)", "priority": 6},
    {"id": 129, "name": "Primera Nacional (Argentina)", "priority": 7},

    # priority 7: Asia, Africa, Oceania (long-range bridges)
    {"id": 169, "name": "J1 League (Japan)", "priority": 7},
    {"id": 292, "name": "K League 1 (South Korea)", "priority": 7},
    {"id": 307, "name": "Saudi Pro League", "priority": 7},
    {"id": 233, "name": "Premier League (Egypt)", "priority": 7},
    {"id": 200, "name": "Premiership (South Africa)", "priority": 7},
    {"id": 188, "name": "A-League (Australia)", "priority": 7},
]


def load_api_key():
    key = os.environ.get("API_FOOTBALL_KEY")
    if key:
        return key
    if ENV_PATH.exists():
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("API_FOOTBALL_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def api_request(endpoint, params, api_key):
    import urllib.request
    import urllib.parse

    url = f"{API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "x-apisports-key": api_key,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    request error: {e}")
        return None


def check_budget(api_key):
    data = api_request("status", {}, api_key)
    if not data or "response" not in data:
        return None
    resp = data["response"]
    if isinstance(resp, list):
        resp = resp[0] if resp else {}
    current = resp.get("requests", {}).get("current", 0)
    limit = resp.get("requests", {}).get("limit_day", 7500)
    return limit - current


def load_checkpoint():
    if CHECKPOINT_PATH.exists():
        with open(CHECKPOINT_PATH, "r") as f:
            return json.load(f)
    return {"completed": [], "errors": [], "requests_total": 0}


def save_checkpoint(cp):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(cp, f, indent=2)


def load_cached_matches():
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r") as f:
            return json.load(f)
    return []


def save_matches(matches):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(matches, f)


def dedupe(matches):
    seen = set()
    unique = []
    for m in matches:
        key = (m["winner"], m["loser"], m["date"], m["comp"])
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique


def fetch_league_season(league_id, season, api_key):
    """Fetch finished fixtures. Returns (match_list, had_error)."""
    data = api_request("fixtures", {
        "league": league_id,
        "season": season,
    }, api_key)

    if not data:
        return [], True

    if data.get("errors"):
        err = data["errors"]
        if isinstance(err, dict) and "plan" in err:
            return [], False  # season not available, not an error
        if isinstance(err, dict):
            return [], True
        return [], True

    if not data.get("response"):
        return [], False

    matches = []
    for fixture in data["response"]:
        status = fixture.get("fixture", {}).get("status", {}).get("short", "")
        if status not in ("FT", "AET", "PEN"):
            continue

        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        info = fixture.get("fixture", {})

        home_name = teams.get("home", {}).get("name", "")
        away_name = teams.get("away", {}).get("name", "")
        hg = goals.get("home")
        ag = goals.get("away")

        if hg is None or ag is None:
            continue

        # handle draws decided by penalties
        if hg == ag:
            score = fixture.get("score", {})
            pen = score.get("penalty", {})
            if pen.get("home") is not None and pen.get("away") is not None:
                if pen["home"] > pen["away"]:
                    hg += 1
                elif pen["away"] > pen["home"]:
                    ag += 1
            if hg == ag:
                continue

        date_str = (info.get("date") or "")[:10]
        league_info = fixture.get("league", {})
        comp = league_info.get("name", "Unknown")

        if hg > ag:
            matches.append({
                "winner": home_name, "loser": away_name,
                "ws": int(hg), "ls": int(ag),
                "date": date_str, "comp": comp,
            })
        else:
            matches.append({
                "winner": away_name, "loser": home_name,
                "ws": int(ag), "ls": int(hg),
                "date": date_str, "comp": comp,
            })

    return matches, False


def build_plan(checkpoint):
    """Build the list of (league, season) pairs to fetch, sorted by priority."""
    completed = set(tuple(x) for x in checkpoint["completed"])
    plan = []
    for league in LEAGUES:
        for season in SEASONS:
            key = (league["id"], season)
            if key in completed:
                continue
            plan.append({
                "league_id": league["id"],
                "league_name": league["name"],
                "season": season,
                "priority": league["priority"],
            })

    # sort by priority, then by season descending (newest first)
    plan.sort(key=lambda x: (x["priority"], -x["season"]))
    return plan


def main():
    parser = argparse.ArgumentParser(description="API-Football bulk backfill")
    parser.add_argument("--reset", action="store_true", help="clear checkpoint, start fresh")
    parser.add_argument("--plan", action="store_true", help="show plan without fetching")
    parser.add_argument("--budget", type=int, default=7400, help="max requests to use (default: 7400)")
    parser.add_argument("--resume", action="store_true", default=True, help="resume from checkpoint (default)")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        print("ERROR: no API key. Set API_FOOTBALL_KEY env var.")
        sys.exit(1)

    if args.reset:
        if CHECKPOINT_PATH.exists():
            CHECKPOINT_PATH.unlink()
            print("checkpoint cleared")

    cp = load_checkpoint()
    plan = build_plan(cp)

    total_pairs = len(LEAGUES) * len(SEASONS)
    completed_count = len(cp["completed"])

    print(f"backfill plan: {len(plan)} remaining of {total_pairs} total league/season pairs")
    print(f"  already completed: {completed_count}")
    print(f"  budget limit: {args.budget} requests")
    print()

    if args.plan:
        by_priority = {}
        for item in plan:
            p = item["priority"]
            if p not in by_priority:
                by_priority[p] = []
            by_priority[p].append(item)

        for p in sorted(by_priority.keys()):
            items = by_priority[p]
            print(f"priority {p}: {len(items)} pairs")
            seen_leagues = set()
            for item in items:
                if item["league_name"] not in seen_leagues:
                    seasons_for = [x["season"] for x in items if x["league_name"] == item["league_name"]]
                    print(f"  {item['league_name']}: seasons {sorted(seasons_for)}")
                    seen_leagues.add(item["league_name"])
        print(f"\ntotal requests needed: {len(plan)} (+1 for status check)")
        return

    # check budget
    remaining = check_budget(api_key)
    if remaining is None:
        print("could not check budget, proceeding cautiously")
        remaining = args.budget
    else:
        print(f"api budget: {remaining} requests remaining today")

    usable = min(remaining - BUDGET_BUFFER, args.budget)
    if usable <= 0:
        print("no budget remaining. try again tomorrow.")
        return

    print(f"will use up to {usable} requests this run")
    print()

    # load existing matches
    all_matches = load_cached_matches()
    requests_used = 0
    matches_added = 0
    errors = 0

    for item in plan:
        if requests_used >= usable:
            print(f"\nbudget limit reached ({requests_used} requests used)")
            break

        lid = item["league_id"]
        season = item["season"]
        name = item["league_name"]

        print(f"[{requests_used+1}/{usable}] {name} {season} (id={lid})...", end=" ", flush=True)

        new_matches, had_error = fetch_league_season(lid, season, api_key)
        requests_used += 1

        if had_error:
            print("ERROR")
            cp["errors"].append([lid, season])
            errors += 1
        elif new_matches:
            print(f"{len(new_matches)} matches")
            all_matches.extend(new_matches)
            matches_added += len(new_matches)
        else:
            print("no data")

        # mark completed regardless (don't retry empty seasons)
        cp["completed"].append([lid, season])
        cp["requests_total"] = cp.get("requests_total", 0) + 1

        # checkpoint after every fetch
        save_checkpoint(cp)
        if new_matches:
            all_matches = dedupe(all_matches)
            save_matches(all_matches)

        # polite delay
        time.sleep(0.5)

    # final save
    all_matches = dedupe(all_matches)
    save_matches(all_matches)
    save_checkpoint(cp)

    print(f"\n{'='*50}")
    print(f"requests used this run:  {requests_used}")
    print(f"matches added:           {matches_added}")
    print(f"errors:                  {errors}")
    print(f"total cached matches:    {len(all_matches)}")
    print(f"total completed pairs:   {len(cp['completed'])}/{total_pairs}")
    print(f"remaining pairs:         {total_pairs - len(cp['completed'])}")

    if total_pairs - len(cp["completed"]) > 0:
        print(f"\nrun again tomorrow to continue backfill.")
    else:
        print(f"\nbackfill complete!")

    print(f"\nto rebuild the graph:")
    print(f"  cd pipeline && python pipeline.py --skip-download")
    print(f"  cp output/graph_data.json ../public/")


if __name__ == "__main__":
    main()