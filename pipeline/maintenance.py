"""
API-Football maintenance script.

Fetches match results from api-football.com (free tier: 100 req/day, current
season only) and writes them to pipeline/cache/api_football_matches.json.

The main pipeline can then merge this file alongside other sources.

Usage:
    # fetch current season results for all configured leagues
    python maintenance.py

    # fetch a specific league only
    python maintenance.py --league mls-next-pro

    # dry run: show what would be fetched without making requests
    python maintenance.py --dry-run

    # print request budget remaining
    python maintenance.py --status

Setup:
    1. Register at https://dashboard.api-football.com/register (free, no card)
    2. Copy your API key from the dashboard
    3. Set it: export API_FOOTBALL_KEY="your_key_here"
       Or create pipeline/.env with: API_FOOTBALL_KEY=your_key_here

League IDs must be confirmed against the API's coverage list. The defaults
below are best-effort; verify them with:
    curl -H "x-apisports-key: YOUR_KEY" \
      "https://v3.football.api-sports.io/leagues?country=USA"
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_PATH = CACHE_DIR / "api_football_matches.json"
ENV_PATH = BASE_DIR / ".env"

API_BASE = "https://v3.football.api-sports.io"
DAILY_LIMIT = 100

# --- league configuration ---
# These IDs need verification against the actual API. Run with --discover
# to query the API for US leagues and print their IDs.
#
# To find league IDs:
#   curl -H "x-apisports-key: KEY" \
#     "https://v3.football.api-sports.io/leagues?country=USA"
#
# Common US leagues (IDs may shift between seasons; verify):
LEAGUES = {
    "mls": {"id": 253, "name": "MLS", "priority": 1},
    "mls-next-pro": {"id": 909, "name": "MLS NEXT Pro", "priority": 1},
    "usl-championship": {"id": 254, "name": "USL Championship", "priority": 2},
    "usl-league-one": {"id": 255, "name": "USL League One", "priority": 2},
    "us-open-cup": {"id": 257, "name": "US Open Cup", "priority": 1},
    "leagues-cup": {"id": 910, "name": "Leagues Cup", "priority": 3},
    "concacaf-champions-cup": {"id": 16, "name": "CONCACAF Champions Cup", "priority": 3},
}

# international leagues worth backfilling if budget remains
INTL_LEAGUES = {
    "champions-league": {"id": 2, "name": "Champions League", "priority": 4},
    "europa-league": {"id": 3, "name": "Europa League", "priority": 4},
    "copa-libertadores": {"id": 13, "name": "Copa Libertadores", "priority": 5},
    "liga-mx": {"id": 262, "name": "Liga MX", "priority": 3},
}


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
    """Make a single API request. Returns parsed JSON or None on error."""
    import urllib.request
    import urllib.parse

    url = f"{API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "x-apisports-key": api_key,
        "Accept": "application/json",
    })

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        print(f"  request failed: {e}")
        return None


def check_status(api_key):
    """Print remaining daily requests."""
    data = api_request("status", {}, api_key)
    if not data or "response" not in data:
        print("could not fetch status")
        return None

    resp = data["response"]
    current = resp.get("requests", {}).get("current", 0)
    limit = resp.get("requests", {}).get("limit_day", DAILY_LIMIT)
    remaining = limit - current
    print(f"api-football status: {current}/{limit} used, {remaining} remaining")
    return remaining


def discover_leagues(api_key, country="USA"):
    """Query the API for all leagues in a country. Useful for finding IDs."""
    data = api_request("leagues", {"country": country}, api_key)
    if not data or "response" not in data:
        print(f"could not fetch leagues for {country}")
        return

    print(f"\nleagues in {country}:")
    for entry in data["response"]:
        league = entry.get("league", {})
        seasons = entry.get("seasons", [])
        latest = seasons[-1]["year"] if seasons else "?"
        print(f"  id={league['id']:>5}  {league['name']:<40}  latest_season={latest}")


def fetch_league_results(league_id, season, api_key):
    """
    Fetch all finished fixtures for a league/season.
    Returns a list of match dicts in pipeline format.
    """
    data = api_request("fixtures", {
        "league": league_id,
        "season": season,
        "status": "FT-AET-PEN",  # finished, after extra time, penalties
    }, api_key)

    if not data or "response" not in data:
        return []

    matches = []
    for fixture in data["response"]:
        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        info = fixture.get("fixture", {})

        home_name = teams.get("home", {}).get("name", "")
        away_name = teams.get("away", {}).get("name", "")
        hg = goals.get("home")
        ag = goals.get("away")

        if hg is None or ag is None or hg == ag:
            # for penalty results, check the score object
            score = fixture.get("score", {})
            # try extra time score
            et = score.get("extratime", {})
            if et.get("home") is not None and et.get("away") is not None:
                hg = et["home"]
                ag = et["away"]
            # if still tied (penalty shootout), use penalty score
            if hg is not None and ag is not None and hg == ag:
                pen = score.get("penalty", {})
                if pen.get("home") is not None and pen.get("away") is not None:
                    # give the PK winner +1 to create a directed edge
                    if pen["home"] > pen["away"]:
                        hg = (hg or 0) + 1
                    elif pen["away"] > pen["home"]:
                        ag = (ag or 0) + 1

        if hg is None or ag is None or hg == ag:
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

    return matches


def load_cached():
    """Load previously fetched matches from cache."""
    if not OUTPUT_PATH.exists():
        return []
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(matches):
    """Write matches to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2)
    print(f"saved {len(matches)} matches to {OUTPUT_PATH}")


def dedupe(matches):
    """Remove duplicate matches based on (winner, loser, date, comp)."""
    seen = set()
    unique = []
    for m in matches:
        key = (m["winner"], m["loser"], m["date"], m["comp"])
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique


def main():
    parser = argparse.ArgumentParser(description="API-Football maintenance script")
    parser.add_argument("--league", type=str, help="fetch a specific league key only")
    parser.add_argument("--season", type=int, default=2025, help="season year (default: 2025)")
    parser.add_argument("--dry-run", action="store_true", help="show plan without fetching")
    parser.add_argument("--status", action="store_true", help="print request budget and exit")
    parser.add_argument("--discover", type=str, metavar="COUNTRY", help="list leagues for a country")
    parser.add_argument("--include-intl", action="store_true", help="also fetch international leagues")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        print("ERROR: no API key found.")
        print("set API_FOOTBALL_KEY env var or create pipeline/.env")
        print("register free at https://dashboard.api-football.com/register")
        sys.exit(1)

    if args.status:
        check_status(api_key)
        return

    if args.discover:
        # costs 1 request
        discover_leagues(api_key, args.discover)
        return

    # build fetch plan, sorted by priority
    targets = dict(LEAGUES)
    if args.include_intl:
        targets.update(INTL_LEAGUES)

    if args.league:
        if args.league not in targets:
            print(f"unknown league key: {args.league}")
            print(f"available: {', '.join(sorted(targets.keys()))}")
            sys.exit(1)
        targets = {args.league: targets[args.league]}

    ordered = sorted(targets.items(), key=lambda x: x[1]["priority"])

    if args.dry_run:
        print(f"would fetch {len(ordered)} league(s) for season {args.season}:")
        for key, info in ordered:
            print(f"  {key:<25} id={info['id']:<6} {info['name']}")
        print(f"estimated requests: {len(ordered)} (1 per league)")
        return

    # check budget
    remaining = check_status(api_key)
    if remaining is not None and remaining < len(ordered):
        print(f"warning: {remaining} requests remain, need {len(ordered)}")
        print("fetching what we can in priority order...")

    # fetch
    existing = load_cached()
    new_matches = []
    requests_made = 0

    for key, info in ordered:
        if remaining is not None and requests_made >= remaining:
            print(f"  budget exhausted, stopping at {key}")
            break

        print(f"fetching {info['name']} (id={info['id']}, season={args.season})...")
        results = fetch_league_results(info["id"], args.season, api_key)
        requests_made += 1

        if results:
            print(f"  got {len(results)} decisive matches")
            new_matches.extend(results)
        else:
            print(f"  no results (league may not be covered on free plan)")

        # be polite
        time.sleep(1)

    # merge with existing cache
    combined = dedupe(existing + new_matches)
    save_cache(combined)

    print(f"\nsummary: {requests_made} API calls, {len(new_matches)} new matches")
    print(f"total cached: {len(combined)} matches")
    print(f"\nto integrate into the main pipeline, run:")
    print(f"  python pipeline.py --skip-download")


if __name__ == "__main__":
    main()
