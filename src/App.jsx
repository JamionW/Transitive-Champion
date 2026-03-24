import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { Analytics } from "@vercel/analytics/react";
// --- graph utilities ---

function buildGraph(matches) {
  const graph = new Map();
  for (const m of matches) {
    if (!graph.has(m.winner)) graph.set(m.winner, []);
    const edges = graph.get(m.winner);
    const year = m.date ? m.date.slice(0, 4) : "unknown";
    const margin = m.ws - m.ls;
    const existing = edges.find((e) => e.loser === m.loser && e.year === year);
    if (!existing) {
      edges.push({ ...m, margin, year });
    } else if (margin > existing.margin) {
      Object.assign(existing, { ...m, margin, year });
    }
  }
  return graph;
}

// time-constrained BFS.
// chain validity: d1 >= d2 >= ... >= dk >= championship year.
// each hop going deeper must use an older (or equal) date than the
// hop that reached the current node, and the hop reaching a champion
// must postdate the championship year.
// state: (team, ceiling_date). a team is re-explored only if a new
// arrival offers a strictly higher ceiling than any previous visit.
// paths carried inline (max length 8, so memory is fine).
function discoverTrophies(graph, startTeam, champMap, maxDepth = 8) {
  const bestCeiling = new Map();
  bestCeiling.set(startTeam, "9999-12-31");

  const queue = [{ team: startTeam, depth: 0, ceiling: "9999-12-31", path: [] }];
  const results = new Map();

  let head = 0;
  while (head < queue.length) {
    const { team, depth, ceiling, path } = queue[head++];

    // check trophies at this node
    const trophies = champMap.get(team);
    if (trophies && path.length > 0) {
      const arrivalDate = path[path.length - 1].date;
      for (const t of trophies) {
        // arrival date's year must be >= championship year
        if (arrivalDate >= String(t.year)) {
          if (!results.has(t.trophy)) results.set(t.trophy, { trophy: t.trophy, years: {} });
          const entry = results.get(t.trophy);
          if (!entry.years[t.year]) {
            entry.years[t.year] = { year: t.year, team: t.team, path: [...path] };
          }
        }
      }
    }

    if (depth >= maxDepth) continue;

    for (const edge of (graph.get(team) || [])) {
      const edgeDate = edge.date;
      // temporal constraint: this edge must predate (or equal) the ceiling
      if (edgeDate > ceiling) continue;

      // dominance: skip if we already reached this team with a higher ceiling
      const prev = bestCeiling.get(edge.loser);
      if (prev !== undefined && prev >= edgeDate) continue;
      bestCeiling.set(edge.loser, edgeDate);

      queue.push({
        team: edge.loser,
        depth: depth + 1,
        ceiling: edgeDate,
        path: [...path, {
          from: team, to: edge.loser,
          ws: edge.ws, ls: edge.ls,
          date: edgeDate, comp: edge.comp,
        }],
      });
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
          <div style={{ color: "#D4A843", fontSize: 18, marginBottom: 8 }}>Loading match data... hang tight!</div>
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
        @keyframes pulse { 0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); } 40% { opacity: 1; transform: scale(1); } }
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
        <a href="https://chattahooligan.com/" target="_blank" rel="noopener noreferrer">
          <img
            src="/silly-app.png"
            alt="Another silly app brought to you by the Chattahooligans"
            style={{ width: 130, height: "auto", flexShrink: 0, borderRadius: 8, transform: "translateY(-6px) rotate(4deg)" }}
          />
        </a>
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
          <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 24, color: "#E8E2D6", marginBottom: 24 }}>
            {selectedTeam}
          </h2>

          {computing && (
            <div style={{ display: "flex", gap: 6, justifyContent: "center", padding: "48px 0" }}>
              {[0, 1, 2].map((i) => (
                <div key={i} style={{
                  width: 10, height: 10, borderRadius: "50%", background: "#D4A843",
                  animation: "pulse 1.2s ease-in-out infinite",
                  animationDelay: `${i * 0.15}s`,
                }} />
              ))}
            </div>
          )}

          {!computing && (<>
            <div style={{ color: "#7A8599", fontSize: 14, marginBottom: 16 }}>
              {totalTrophies} {totalTrophies === 1 ? "championship" : "championships"} claimed
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
            {trophyResults && trophyResults.length > 0 && (
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

            {trophyResults && trophyResults.length === 0 && directTrophies.length === 0 && (
              <div style={{ color: "#5A6577", fontSize: 14, padding: "40px 0", textAlign: "center" }}>
                No transitive championship claims found for this team.
                <br />
                <span style={{ fontSize: 12 }}>This team needs at least one recorded win to start a chain.</span>
              </div>
            )}
          </>)}
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
        <div style={{ textAlign: "center", paddingTop: 16 }}>
          <a
            href="https://www.zeffy.com/donation-form/support-the-chattahooligans"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: "#D4A843", fontSize: 13, fontFamily: "inherit",
              textDecoration: "underline", textUnderlineOffset: 3,
            }}
          >
            Want to support this app, and the Chattahooligans? Click here!
          </a>
        </div>
      </div>
      <Analytics />
    </div>
  );
}