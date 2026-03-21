# Transitive Champion

Select any soccer team. Discover every championship they've "won" through transitive wins. If you beat a team that beat a team that won a trophy, that trophy is yours. Obviously.

Built with React + Vite. Backed by 185,000+ match results across 8,300+ teams from 226 competitions (1888 to 2023).

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
│   └── App.jsx             # main app component (search, DFS, display)
└── pipeline/
    ├── pipeline.py          # data ingestion script
    └── data/
        ├── manual_matches.json   # manually maintained results (CFC, etc.)
        ├── championships.json    # trophy winners (chain endpoints)
        └── team_name_map.json    # normalizes team name variants
```

## How It Works

The app loads `graph_data.json` at runtime (fetched from `public/`, not bundled). When you select a team, it runs a depth-first search through the win graph, capped at 8 hops, finding every path to a championship-holding team. Results are grouped by trophy and sorted by tier.

## Data Pipeline

The graph data comes from the [schochastics/football-data](https://github.com/schochastics/football-data) parquet file (1.2M+ matches), compressed to one edge per winner/loser pair (keeping the highest margin). Manually maintained results in `pipeline/data/manual_matches.json` fill in teams below the dataset's coverage floor (e.g. MLS NEXT Pro).

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
