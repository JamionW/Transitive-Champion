"""
API-Football cached data loader.

Reads the cached match results produced by maintenance.py and returns them
as match dicts for the main pipeline.
"""

import json
from pathlib import Path

CACHE_PATH = Path(__file__).parent.parent / "cache" / "api_football_matches.json"


def load_matches(name_map=None):
    """
    Load cached API-Football results.

    Returns a list of match dicts: {winner, loser, ws, ls, date, comp}
    """
    if not CACHE_PATH.exists():
        print("api-football: no cached data found (run maintenance.py first)")
        return []

    if name_map is None:
        name_map = {}

    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    matches = []
    for m in raw:
        matches.append({
            "winner": name_map.get(m["winner"], m["winner"]),
            "loser": name_map.get(m["loser"], m["loser"]),
            "ws": m["ws"],
            "ls": m["ls"],
            "date": m.get("date", "unknown"),
            "comp": m.get("comp", "Unknown"),
        })

    print(f"api-football: loaded {len(matches)} cached match(es)")
    return matches
