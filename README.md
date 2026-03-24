# Transitive Champion

Select any soccer team. Discover every championship they've "won" through transitive wins. If you beat a team that beat a team that won a trophy, that trophy is yours. Obviously.

Built with React + Vite. Backed by 185,000+ match results across 8,300+ teams from 226 competitions (1888 to present).

## Quick Start

```bash
npm install
npm run dev
```

Open http://localhost:5173 and search for a team.

## Project Structure

```
├── index.html              # Vite entry point
├── vite.config.js
├── package.json
├── public/
│   └── graph_data.json     # match graph (~18 MB raw, ~3 MB gzipped by host)
├── src/
│   ├── main.jsx            # React mount
│   └── App.jsx             # main app component (search, BFS, display)
└── pipeline/
    ├── pipeline.py          # data ingestion script
    ├── maintenance.py       # API-Football cache maintenance
    ├── data/
    │   ├── manual_matches.json   # manually maintained results (CFC, etc.)
    │   ├── championships.json    # trophy winners (chain endpoints)
    │   └── team_name_map.json    # normalizes team name variants
    └── sources/
        ├── transfermarkt.py      # transfermarkt-datasets parser
        ├── thecup.py             # US Open Cup results
        └── api_football.py       # API-Football cached results
```

## How It Works

The app loads `graph_data.json` at runtime (fetched from `public/`, not bundled). When you select a team, it runs a time-constrained BFS through the win graph, capped at 8 hops, finding every path to a championship-holding team. Each hop must use a match date equal to or earlier than the previous hop, and the final hop must postdate the championship year. Results are grouped by trophy and sorted by tier.

## Data Pipeline

The graph is built from multiple sources, merged in order of priority:

1. [schochastics/football-data](https://github.com/schochastics/football-data) parquet file (1.2M+ matches)
2. transfermarkt-datasets (~80k European/international matches)
3. US Open Cup results
4. API-Football cached results
5. Manual overrides from `pipeline/data/manual_matches.json`

Later sources take precedence during compression. The compressor keeps one edge per (winner, loser, year) triple, retaining the highest goal margin for each.

### Rebuilding the data

```bash
# prerequisites: python 3.8+, pyarrow, git-lfs
pip install pyarrow

# full run (clones repo via git LFS, builds graph_data.json)
cd pipeline
python pipeline.py

# then copy the output
cp output/graph_data.json ../public/
```

### Pipeline options

```
--skip-download      use cached parquet instead of re-downloading
--force-download     re-download parquet even if cached
--stats              print dataset statistics only, no output file
--no-transfermarkt   skip transfermarkt source
--no-open-cup        skip US Open Cup source
--no-api-football    skip API-Football cache
```

### Adding match results

Edit `pipeline/data/manual_matches.json`. Only wins matter:

```json
{
  "winner": "Chattanooga FC",
  "loser": "Atlanta United 2",
  "ws": 3,
  "ls": 1,
  "date": "2024-06-15",
  "comp": "MLS NEXT Pro"
}
```

### Adding championships

Edit `pipeline/data/championships.json`:

```json
{"team": "Real Madrid", "trophy": "UEFA Champions League", "year": 2024}
```

## Deploy to Vercel

1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com), sign in with GitHub
3. Import the repo; Vercel auto-detects Vite
4. Deploy (the `public/graph_data.json` is served gzip-compressed automatically)

## Data Attribution

Match data from [schochastics/football-data](https://github.com/schochastics/football-data), provided under the [Open Data Commons Attribution License](https://opendatacommons.org/licenses/by/1-0/index.html).

## License

MIT