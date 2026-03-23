import { useState, useEffect, useMemo, useCallback, useRef } from "react";
// --- chattahooligan badge ---

const GRYPHLING_SRC = `data:image/png;base64,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`;

function ChattahooliganBadge() {
  const size = 130;
  const r = size / 2;
  const textR = r - 10;
  return (
    <div style={{
      transform: "rotate(8deg)",
      flexShrink: 0,
      width: size, height: size,
      position: "relative",
    }}>
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        {/* outer ring */}
        <circle cx={r} cy={r} r={r - 2} fill="none" stroke="#D4A843" strokeWidth="2" opacity="0.6" />
        <circle cx={r} cy={r} r={r - 6} fill="none" stroke="#D4A843" strokeWidth="0.5" opacity="0.3" />
        {/* notched edge (decorative dots around the rim) */}
        {Array.from({ length: 36 }, (_, i) => {
          const angle = (i * 10) * Math.PI / 180;
          const cx = r + (r - 4) * Math.cos(angle);
          const cy = r + (r - 4) * Math.sin(angle);
          return <circle key={i} cx={cx} cy={cy} r="1" fill="#D4A843" opacity="0.25" />;
        })}
        {/* circular text path */}
        <defs>
          <path
            id="badge-text-top"
            d={`M ${r - textR},${r} A ${textR},${textR} 0 1,1 ${r + textR},${r}`}
            fill="none"
          />
          <path
            id="badge-text-bottom"
            d={`M ${r - textR},${r} A ${textR},${textR} 0 0,1 ${r + textR},${r}`}
            fill="none"
          />
        </defs>
        <text fill="#D4A843" fontSize="7.5" fontFamily="'DM Sans', sans-serif" fontWeight="600" letterSpacing="0.5">
          <textPath href="#badge-text-top" startOffset="50%" textAnchor="middle">
            ANOTHER SILLY APP
          </textPath>
        </text>
        <text fill="#D4A843" fontSize="7" fontFamily="'DM Sans', sans-serif" fontWeight="500" letterSpacing="0.3">
          <textPath href="#badge-text-bottom" startOffset="50%" textAnchor="middle">
            BY THE CHATTAHOOLIGANS
          </textPath>
        </text>
        {/* separator dots */}
        <circle cx={r - textR} cy={r} r="2" fill="#D4A843" opacity="0.5" />
        <circle cx={r + textR} cy={r} r="2" fill="#D4A843" opacity="0.5" />
      </svg>
      {/* gryphling logo in center */}
      <img
        src={GRYPHLING_SRC}
        alt="Chattahooligan Gryphling"
        style={{
          position: "absolute",
          top: "50%", left: "50%",
          transform: "translate(-50%, -50%)",
          width: size * 0.52, height: size * 0.52,
          borderRadius: "50%",
          opacity: 0.85,
        }}
      />
    </div>
  );
}


// --- graph utilities ---

function buildGraph(matches) {
  const graph = new Map();
  for (const m of matches) {
    if (!graph.has(m.winner)) graph.set(m.winner, []);
    const edges = graph.get(m.winner);
    const margin = m.ws - m.ls;
    const existing = edges.find((e) => e.loser === m.loser);
    if (!existing) {
      edges.push({ ...m, margin });
    } else if (margin > existing.margin) {
      Object.assign(existing, { ...m, margin });
    }
  }
  return graph;
}

// BFS with permanent visited set.
// finds every reachable trophy within maxDepth hops.
// O(V+E); finishes in milliseconds regardless of team.
// stores one shortest path per trophy per year.
function discoverTrophies(graph, startTeam, champMap, maxDepth = 8) {
  const parent = new Map();
  parent.set(startTeam, null);
  const queue = [{ team: startTeam, depth: 0 }];
  const results = new Map();

  function reconstructPath(toTeam) {
    const path = [];
    let cur = toTeam;
    while (parent.get(cur)) {
      const p = parent.get(cur);
      path.unshift(p.edge);
      cur = p.from;
    }
    return path;
  }

  let head = 0;
  while (head < queue.length) {
    const { team, depth } = queue[head++];

    const trophies = champMap.get(team);
    if (trophies && team !== startTeam) {
      for (const t of trophies) {
        if (!results.has(t.trophy)) results.set(t.trophy, { trophy: t.trophy, years: {} });
        const entry = results.get(t.trophy);
        if (!entry.years[t.year]) {
          entry.years[t.year] = {
            year: t.year,
            team: t.team,
            path: reconstructPath(team),
          };
        }
      }
    }

    if (depth >= maxDepth) continue;

    for (const edge of (graph.get(team) || [])) {
      if (!parent.has(edge.loser)) {
        parent.set(edge.loser, {
          from: team,
          edge: {
            from: team, to: edge.loser,
            ws: edge.ws, ls: edge.ls,
            date: edge.date, comp: edge.comp,
          },
        });
        queue.push({ team: edge.loser, depth: depth + 1 });
      }
    }
  }

  return results;
}

// --- tier classification ---

function trophyTier(trophy) {
  if (trophy.includes("Champions League") || trophy.includes("Champions Cup")) return 0;
  if (["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"].some((l) => trophy.includes(l))) return 1;
  if (trophy.includes("Leagues Cup") || trophy.includes("Concacaf")) return 2;
  if (trophy.includes("MLS")) return 3;
  if (trophy.includes("Eredivisie") || trophy.includes("Primeira") || trophy.includes("Scottish")) return 4;
  return 5;
}

const TIER_LABELS = ["Continental", "Top 5 League", "Concacaf / Leagues Cup", "MLS", "Other Major League", "Other"];
const TIER_COLORS = ["#D4A843", "#C0C0C0", "#E07040", "#5B8A72", "#CD7F32", "#7A8599"];

// --- component ---

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [expandedTrophy, setExpandedTrophy] = useState(null);
  const [expandedYear, setExpandedYear] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [computing, setComputing] = useState(false);
  const searchRef = useRef(null);

  const [trophyResults, setTrophyResults] = useState(null);

  // close suggestions on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // load graph data on mount
  useEffect(() => {
    fetch("/graph_data.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  const graph = useMemo(() => {
    if (!data) return null;
    return buildGraph(data.matches);
  }, [data]);

  const champMap = useMemo(() => {
    if (!data) return null;
    const m = new Map();
    for (const c of data.championships) {
      if (!m.has(c.team)) m.set(c.team, []);
      m.get(c.team).push(c);
    }
    return m;
  }, [data]);

  const teams = useMemo(() => {
    if (!data) return [];
    const s = new Set();
    data.matches.forEach((m) => { s.add(m.winner); s.add(m.loser); });
    return [...s].sort();
  }, [data]);

  const filtered = useMemo(() => {
    if (!query.trim()) return teams.slice(0, 50);
    const q = query.toLowerCase();
    return teams.filter((t) => t.toLowerCase().includes(q)).slice(0, 50);
  }, [query, teams]);

  // BFS on team select (instant)
  useEffect(() => {
    if (!selectedTeam || !graph || !champMap) {
      setTrophyResults(null);
      return;
    }
    setComputing(true);
    const timeout = setTimeout(() => {
      const discovered = discoverTrophies(graph, selectedTeam, champMap);
      const arr = [...discovered.values()].sort((a, b) => trophyTier(a.trophy) - trophyTier(b.trophy));
      setTrophyResults(arr);
      setComputing(false);
    }, 10);
    return () => clearTimeout(timeout);
  }, [selectedTeam, graph, champMap]);

  // direct championships (zero hops)
  const directTrophies = useMemo(() => {
    if (!selectedTeam || !champMap) return [];
    const raw = champMap.get(selectedTeam) || [];
    const grouped = new Map();
    for (const t of raw) {
      if (!grouped.has(t.trophy)) grouped.set(t.trophy, { trophy: t.trophy, years: [] });
      grouped.get(t.trophy).years.push(t.year);
    }
    return [...grouped.values()].map((g) => ({ ...g, years: g.years.sort((a, b) => b - a) }));
  }, [selectedTeam, champMap]);

  const selectTeam = useCallback((team) => {
    setSelectedTeam(team);
    setQuery(team);
    setShowDropdown(false);
    setExpandedTrophy(null);
    setExpandedYear(null);
  }, []);

  const totalTrophies = (trophyResults
    ? trophyResults.reduce((sum, r) => sum + Object.keys(r.years).length, 0)
    : 0) + directTrophies.reduce((sum, t) => sum + t.years.length, 0);

  // --- render ---

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: "#0B1120", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet" />
        <div style={{ textAlign: "center", fontFamily: "'DM Sans', sans-serif" }}>
          <div style={{ color: "#D4A843", fontSize: 18, marginBottom: 8 }}>Loading match data...</div>
          <div style={{ color: "#5A6577", fontSize: 13 }}>~185k edges across 8,300+ teams</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: "100vh", background: "#0B1120", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet" />
        <div style={{ textAlign: "center", fontFamily: "'DM Sans', sans-serif", maxWidth: 400, padding: 24 }}>
          <div style={{ color: "#E07040", fontSize: 16, marginBottom: 8 }}>Failed to load graph data</div>
          <div style={{ color: "#7A8599", fontSize: 13, marginBottom: 16 }}>{error}</div>
          <div style={{ color: "#5A6577", fontSize: 12 }}>
            Make sure graph_data.json is in the public/ directory.
            Run the pipeline first: <code style={{ color: "#D4A843" }}>python pipeline/pipeline.py</code>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0B1120", color: "#E8E2D6", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet" />
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::selection { background: #D4A84366; }
        .trophy-card { transition: transform 0.15s, box-shadow 0.15s; cursor: pointer; }
        .trophy-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
        .chain-step { animation: fadeIn 0.2s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateX(-8px); } to { opacity: 1; transform: translateX(0); } }
        input::placeholder { color: #7A8599; }
      `}</style>

      {/* header */}
      <div style={{ padding: "48px 24px 32px", maxWidth: 900, margin: "0 auto", display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 24 }}>
        <div>
          <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 42, fontWeight: 900, color: "#D4A843", letterSpacing: "-0.02em", lineHeight: 1.1 }}>
            Transitive Champion
          </h1>
          <p style={{ color: "#7A8599", fontSize: 14, marginTop: 8, maxWidth: 520, lineHeight: 1.5 }}>
            Select a team. Discover every championship they've "won" through transitive wins.
            If you beat a team that beat a team that won a trophy, that trophy is yours. Obviously.
          </p>
        </div>
        <ChattahooliganBadge />
      </div>

      {/* search */}
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "0 24px" }}>
        <div ref={searchRef} style={{ position: "relative" }}>
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedTeam(null);
              setShowDropdown(true);
              setExpandedTrophy(null);
              setExpandedYear(null);
            }}
            onFocus={() => {
              if (selectedTeam) {
                setSelectedTeam(null);
                setExpandedTrophy(null);
                setExpandedYear(null);
              }
              setShowDropdown(true);
            }}
            placeholder={`Search ${teams.length.toLocaleString()} teams...`}
            style={{
              width: "100%", padding: "14px 16px", background: "#151E30", border: "1px solid #1E2A42",
              borderRadius: 8, color: "#E8E2D6", fontSize: 16, outline: "none", fontFamily: "inherit"
            }}
          />
          {showDropdown && !selectedTeam && query.trim() && filtered.length > 0 && (
            <div style={{
              position: "absolute", top: "100%", left: 0, right: 0, zIndex: 10,
              background: "#151E30", border: "1px solid #1E2A42", borderRadius: "0 0 8px 8px",
              maxHeight: 260, overflowY: "auto"
            }}>
              {filtered.map((t) => (
                <div
                  key={t}
                  onClick={() => selectTeam(t)}
                  style={{
                    padding: "10px 16px", cursor: "pointer", fontSize: 14,
                    borderBottom: "1px solid #1E2A4233",
                    background: "transparent", color: "#E8E2D6"
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "#1E2A42"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                >
                  {t}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* results */}
      {selectedTeam && (
        <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 24 }}>
            <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 24, color: "#E8E2D6" }}>
              {selectedTeam}
            </h2>
            {computing ? (
              <span style={{ color: "#D4A843", fontSize: 13 }}>discovering trophies...</span>
            ) : (
              <span style={{ color: "#7A8599", fontSize: 14 }}>
                {totalTrophies} {totalTrophies === 1 ? "championship" : "championships"} claimed
              </span>
            )}
          </div>

          {/* direct trophies */}
          {directTrophies.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h3 style={{ color: "#7A8599", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
                Actual Championships
              </h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                {directTrophies.map((t, i) => (
                  <div key={i} style={{
                    background: "#151E30", border: "1px solid #D4A84344", borderRadius: 8,
                    padding: "12px 16px", fontSize: 13
                  }}>
                    <span style={{ color: "#D4A843" }}>{t.trophy}</span>
                    <span style={{ color: "#7A8599", marginLeft: 8, fontSize: 11 }}>{t.years.join(", ")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* transitive trophies */}
          {!computing && trophyResults && trophyResults.length > 0 && (
            <div>
              <h3 style={{ color: "#7A8599", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
                Transitive Championships
              </h3>

              {[0, 1, 2, 3, 4, 5].map((tier) => {
                const tierResults = trophyResults.filter((r) => trophyTier(r.trophy) === tier);
                if (tierResults.length === 0) return null;
                return (
                  <div key={tier} style={{ marginBottom: 20 }}>
                    <div style={{ color: TIER_COLORS[tier] || "#7A8599", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
                      {TIER_LABELS[tier] || "Other"}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                      {tierResults.map((r, i) => {
                        const key = r.trophy;
                        const isExpanded = expandedTrophy === key;
                        const yearEntries = Object.values(r.years).sort((a, b) => b.year - a.year);
                        const yearList = yearEntries.map((y) => y.year).join(", ");
                        return (
                          <div key={i}>
                            <div
                              className="trophy-card"
                              onClick={() => { setExpandedTrophy(isExpanded ? null : key); setExpandedYear(null); }}
                              style={{
                                background: isExpanded ? "#1A2540" : "#151E30",
                                border: `1px solid ${isExpanded ? TIER_COLORS[tier] + "66" : "#1E2A42"}`,
                                borderRadius: 8, padding: "12px 16px", fontSize: 13
                              }}
                            >
                              <span style={{ color: TIER_COLORS[tier] || "#D4A843" }}>{r.trophy}</span>
                              <span style={{ color: "#7A8599", marginLeft: 8, fontSize: 11 }}>{yearList}</span>
                              <span style={{ color: "#5A6577", marginLeft: 8, fontSize: 11 }}>
                                {isExpanded ? "▾" : "▸"}
                              </span>
                            </div>

                            {isExpanded && (
                              <div style={{
                                marginTop: 8, background: "#0D1526", border: "1px solid #1E2A42",
                                borderRadius: 8, padding: 16, maxWidth: 600
                              }}>
                                {yearEntries.map((ye) => {
                                  const yearKey = `${key}-${ye.year}`;
                                  const isYearExpanded = expandedYear === yearKey;
                                  const hopCount = ye.path.length;
                                  return (
                                    <div key={ye.year} style={{ marginBottom: 8 }}>
                                      <div
                                        onClick={() => setExpandedYear(isYearExpanded ? null : yearKey)}
                                        style={{
                                          cursor: "pointer", padding: "8px 12px", borderRadius: 6,
                                          background: isYearExpanded ? "#151E30" : "transparent",
                                          border: "1px solid #1E2A4255", fontSize: 12, color: "#B0B8C8"
                                        }}
                                      >
                                        <span style={{ color: "#D4A843" }}>{selectedTeam}</span>
                                        <span style={{ color: "#5A6577" }}> → {hopCount} {hopCount === 1 ? "hop" : "hops"} → </span>
                                        <span style={{ color: TIER_COLORS[tier] || "#D4A843" }}>{ye.team}</span>
                                        <span style={{ color: "#7A8599", marginLeft: 8, fontSize: 11 }}>{ye.year}</span>
                                        <span style={{ color: "#5A6577", marginLeft: 8 }}>{isYearExpanded ? "▾" : "▸"}</span>
                                      </div>

                                      {isYearExpanded && (
                                        <div style={{ paddingLeft: 12, marginTop: 6, borderLeft: `2px solid ${TIER_COLORS[tier] || "#D4A843"}33` }}>
                                          {ye.path.map((step, si) => (
                                            <div key={si} className="chain-step" style={{
                                              display: "flex", alignItems: "center", gap: 8,
                                              padding: "6px 0", fontSize: 12, animationDelay: `${si * 0.05}s`
                                            }}>
                                              <span style={{ color: "#E8E2D6", fontWeight: 500 }}>{step.from}</span>
                                              <span style={{
                                                color: "#0B1120", background: "#D4A843", borderRadius: 4,
                                                padding: "1px 6px", fontSize: 11, fontWeight: 600, whiteSpace: "nowrap"
                                              }}>
                                                {step.ws}:{step.ls}
                                              </span>
                                              <span style={{ color: "#E8E2D6", fontWeight: 500 }}>{step.to}</span>
                                              <span style={{ color: "#5A6577", fontSize: 10, whiteSpace: "nowrap" }}>
                                                {step.comp}, {step.date.slice(0, 4)}
                                              </span>
                                            </div>
                                          ))}
                                          <div style={{ padding: "6px 0", fontSize: 12, color: TIER_COLORS[tier] || "#D4A843", fontWeight: 600 }}>
                                            ∴ {ye.team} won {r.trophy} {ye.year}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {!computing && trophyResults && trophyResults.length === 0 && directTrophies.length === 0 && (
            <div style={{ color: "#5A6577", fontSize: 14, padding: "40px 0", textAlign: "center" }}>
              No transitive championship claims found for this team.
              <br />
              <span style={{ fontSize: 12 }}>This team needs at least one recorded win to start a chain.</span>
            </div>
          )}
        </div>
      )}

      {/* empty state */}
      {!selectedTeam && (
        <div style={{ maxWidth: 900, margin: "0 auto", padding: "60px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 64, opacity: 0.15 }}>🏆</div>
          <p style={{ color: "#5A6577", fontSize: 14, marginTop: 16 }}>
            Pick a team above to reveal their transitive trophy cabinet.
          </p>
        </div>
      )}

      {/* footer */}
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 24px 24px" }}>
        <div style={{ borderTop: "1px solid #1E2A42", paddingTop: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#3A4559", fontSize: 11 }}>
            {data.meta.match_count.toLocaleString()} edges · {data.meta.team_count.toLocaleString()} teams · {data.meta.championship_count} championships
          </span>
          <span style={{ color: "#3A4559", fontSize: 11 }}>
            Max chain depth: 8 hops
          </span>
        </div>
      </div>
    </div>
  );
}