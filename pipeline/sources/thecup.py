"""
US Open Cup data source.

Loads match results from pipeline/data/us_open_cup.json, a manually maintained
file of US Open Cup results. This is the primary way to capture cross-tier wins
(D3/D4 teams beating higher-division opponents, and vice versa) which form the
critical bridge edges in the transitive graph.

TheCup.us (https://thecup.us) is the definitive source for these results.
Results are published in article prose; there is no structured API or feed.
The JSON file must be maintained by hand after each round.

The format mirrors manual_matches.json:
  {
    "winner": "Chattanooga FC",
    "loser": "Corpus Christi FC",
    "ws": 4,
    "ls": 1,
    "date": "2025-03-19",
    "comp": "US Open Cup"
  }

Penalty shootout wins: record the score at end of extra time. If the match was
a draw after ET, record one side as winner with the same score (since we only
care about who advanced, and draws are dropped from the graph anyway, the
convention is to give the advancing team +1 to their goal tally so the edge
exists). Example: a 1-1 draw won on pens by Team A becomes ws:2, ls:1.
This is a pragmatic choice; the transitive chain needs a directed edge.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
US_OPEN_CUP_PATH = DATA_DIR / "us_open_cup.json"


def load_matches(name_map=None):
    """
    Load US Open Cup results from the JSON file.

    Returns a list of match dicts: {winner, loser, ws, ls, date, comp}
    """
    if not US_OPEN_CUP_PATH.exists():
        print("us open cup: no us_open_cup.json found, skipping")
        return []

    with open(US_OPEN_CUP_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if name_map is None:
        name_map = {}

    matches = []
    for entry in raw:
        if "winner" not in entry:
            continue
        m = {
            "winner": name_map.get(entry["winner"], entry["winner"]),
            "loser": name_map.get(entry["loser"], entry["loser"]),
            "ws": entry["ws"],
            "ls": entry["ls"],
            "date": entry.get("date", "unknown"),
            "comp": entry.get("comp", "US Open Cup"),
        }
        matches.append(m)

    print(f"us open cup: loaded {len(matches)} match(es)")
    return matches
