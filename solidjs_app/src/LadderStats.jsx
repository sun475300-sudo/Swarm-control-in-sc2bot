import { createSignal, createStore } from 'solid-js';
import { createResource, Show, For, createMemo } from 'solid-js';

// ── Fetch helpers ──────────────────────────────────────────────────────────────
async function fetchRankings(league) {
  const res = await fetch(`/api/rankings?league=${league}`);
  if (!res.ok) throw new Error('Failed to fetch rankings');
  return res.json();
}

async function fetchPlayerHistory(playerId) {
  const res = await fetch(`/api/player/${playerId}/history`);
  if (!res.ok) throw new Error('Failed to fetch player history');
  return res.json();
}

// ── Utility ────────────────────────────────────────────────────────────────────
function mmrColor(mmr) {
  if (mmr >= 6000) return '#ff6b35';   // Grandmaster
  if (mmr >= 5000) return '#a855f7';   // Master
  if (mmr >= 4000) return '#3b82f6';   // Diamond
  if (mmr >= 3000) return '#22c55e';   // Platinum
  return '#6b7280';                     // Gold and below
}

function leagueBadge(mmr) {
  if (mmr >= 6000) return 'GM';
  if (mmr >= 5000) return 'M';
  if (mmr >= 4000) return 'D';
  if (mmr >= 3000) return 'P';
  return 'G';
}

function formatDelta(delta) {
  if (delta > 0) return `+${delta}`;
  return `${delta}`;
}

// ── Sub-component: MMR Trend Sparkline ────────────────────────────────────────
function MmrSparkline(props) {
  const points = () => {
    const history = props.history ?? [];
    if (history.length < 2) return '';
    const max = Math.max(...history);
    const min = Math.min(...history);
    const range = max - min || 1;
    const w = 80;
    const h = 24;
    return history
      .map((v, i) => {
        const x = (i / (history.length - 1)) * w;
        const y = h - ((v - min) / range) * h;
        return `${x},${y}`;
      })
      .join(' ');
  };

  return (
    <svg width="80" height="24" style={{ display: 'block' }}>
      <polyline
        points={points()}
        fill="none"
        stroke={props.color ?? '#3b82f6'}
        stroke-width="1.5"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
    </svg>
  );
}

// ── Sub-component: Player Detail Card ─────────────────────────────────────────
function PlayerCard(props) {
  const [historyData] = createResource(() => props.playerId, fetchPlayerHistory);

  const recentGames = createMemo(() => historyData()?.recentGames ?? []);
  const mmrHistory = createMemo(() => historyData()?.mmrHistory ?? []);

  return (
    <div class="player-card">
      <div class="card-header">
        <h3>{props.name}</h3>
        <span class="league-badge" style={{ background: mmrColor(props.mmr) }}>
          {leagueBadge(props.mmr)}
        </span>
      </div>

      <div class="card-stats">
        <div class="stat-item">
          <span class="stat-label">MMR</span>
          <span class="stat-value" style={{ color: mmrColor(props.mmr) }}>
            {props.mmr}
          </span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Win%</span>
          <span class="stat-value">{props.winRate}%</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Games</span>
          <span class="stat-value">{props.gamesPlayed}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Streak</span>
          <span
            class="stat-value"
            style={{ color: props.streak >= 0 ? '#22c55e' : '#ef4444' }}
          >
            {formatDelta(props.streak)}
          </span>
        </div>
      </div>

      <Show when={mmrHistory().length > 1}>
        <div class="sparkline-row">
          <span class="stat-label">MMR Trend</span>
          <MmrSparkline history={mmrHistory()} color={mmrColor(props.mmr)} />
        </div>
      </Show>

      <Show when={recentGames().length > 0}>
        <div class="recent-games">
          <h4>Recent Games</h4>
          <For each={recentGames().slice(0, 5)}>
            {(game) => (
              <div class={`game-row ${game.result === 'Win' ? 'win' : 'loss'}`}>
                <span class="game-result">{game.result}</span>
                <span class="game-matchup">{game.matchup}</span>
                <span class="game-map">{game.map}</span>
                <span class="game-duration">{game.duration}</span>
                <span class="game-delta" style={{ color: game.mmrDelta >= 0 ? '#22c55e' : '#ef4444' }}>
                  {formatDelta(game.mmrDelta)}
                </span>
              </div>
            )}
          </For>
        </div>
      </Show>

      <button class="close-btn" onClick={props.onClose}>Close</button>
    </div>
  );
}

// ── Main Component: LadderStats ────────────────────────────────────────────────
export default function LadderStats() {
  // Signals for filter/sort state
  const [league, setLeague] = createSignal('master');
  const [sortField, setSortField] = createSignal('mmr');
  const [sortAsc, setSortAsc] = createSignal(false);
  const [searchQuery, setSearchQuery] = createSignal('');
  const [selectedPlayer, setSelectedPlayer] = createSignal(null);
  const [page, setPage] = createSignal(0);
  const PAGE_SIZE = 15;

  // Store for live MMR delta highlights
  const [highlights, setHighlights] = createStore({});

  // Reactive resource tied to league signal
  const [rankings, { refetch }] = createResource(league, fetchRankings);

  // Derived: filter + sort
  const filteredRankings = createMemo(() => {
    const data = rankings()?.players ?? [];
    const q = searchQuery().toLowerCase();
    const filtered = q ? data.filter((p) => p.name.toLowerCase().includes(q)) : data;
    const field = sortField();
    const asc = sortAsc();
    return [...filtered].sort((a, b) => {
      const diff = (a[field] ?? 0) - (b[field] ?? 0);
      return asc ? diff : -diff;
    });
  });

  const pagedRankings = createMemo(() => {
    const start = page() * PAGE_SIZE;
    return filteredRankings().slice(start, start + PAGE_SIZE);
  });

  const totalPages = createMemo(() =>
    Math.ceil(filteredRankings().length / PAGE_SIZE)
  );

  function toggleSort(field) {
    if (sortField() === field) {
      setSortAsc(!sortAsc());
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  }

  function sortIndicator(field) {
    if (sortField() !== field) return '↕';
    return sortAsc() ? '↑' : '↓';
  }

  function openPlayer(player) {
    setSelectedPlayer(player);
  }

  return (
    <div class="ladder-stats">
      <h2>SC2 Ladder Rankings</h2>

      {/* League selector */}
      <div class="league-bar">
        <For each={['grandmaster', 'master', 'diamond', 'platinum', 'gold']}>
          {(lg) => (
            <button
              class={league() === lg ? 'active' : ''}
              onClick={() => { setLeague(lg); setPage(0); }}
            >
              {lg.charAt(0).toUpperCase() + lg.slice(1)}
            </button>
          )}
        </For>
        <button class="refresh-btn" onClick={refetch}>Refresh</button>
      </div>

      {/* Search */}
      <div class="search-row">
        <input
          type="text"
          placeholder="Search player..."
          value={searchQuery()}
          onInput={(e) => { setSearchQuery(e.target.value); setPage(0); }}
        />
        <span class="result-count">
          {filteredRankings().length} players
        </span>
      </div>

      {/* Rankings table */}
      <Show when={!rankings.loading} fallback={<p class="loading">Loading rankings...</p>}>
        <Show when={rankings.error} fallback={null}>
          <p class="error">Error: {rankings.error?.message}</p>
        </Show>
        <table class="rankings-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Player</th>
              <th onClick={() => toggleSort('mmr')} class="sortable">
                MMR {sortIndicator('mmr')}
              </th>
              <th onClick={() => toggleSort('winRate')} class="sortable">
                Win% {sortIndicator('winRate')}
              </th>
              <th onClick={() => toggleSort('gamesPlayed')} class="sortable">
                Games {sortIndicator('gamesPlayed')}
              </th>
              <th onClick={() => toggleSort('streak')} class="sortable">
                Streak {sortIndicator('streak')}
              </th>
              <th>Race</th>
            </tr>
          </thead>
          <tbody>
            <For each={pagedRankings()}>
              {(player, localIdx) => {
                const globalRank = () => page() * PAGE_SIZE + localIdx() + 1;
                const pct = () =>
                  typeof player.winRate === 'number'
                    ? player.winRate.toFixed(1)
                    : '—';
                const isHighlighted = () => !!highlights[player.id];

                return (
                  <tr
                    class={isHighlighted() ? 'highlighted' : ''}
                    onClick={() => openPlayer(player)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>{globalRank()}</td>
                    <td class="player-name">
                      <span
                        class="league-dot"
                        style={{ background: mmrColor(player.mmr) }}
                      />
                      {player.name}
                    </td>
                    <td style={{ color: mmrColor(player.mmr), fontWeight: 'bold' }}>
                      {player.mmr}
                    </td>
                    <td
                      style={{
                        color:
                          player.winRate >= 55
                            ? '#22c55e'
                            : player.winRate >= 45
                            ? '#eab308'
                            : '#ef4444',
                      }}
                    >
                      {pct()}%
                    </td>
                    <td>{player.gamesPlayed}</td>
                    <td
                      style={{
                        color: player.streak > 0 ? '#22c55e' : player.streak < 0 ? '#ef4444' : '#6b7280',
                      }}
                    >
                      {formatDelta(player.streak ?? 0)}
                    </td>
                    <td class="race-icon">{player.race ?? '?'}</td>
                  </tr>
                );
              }}
            </For>
          </tbody>
        </table>

        {/* Pagination */}
        <Show when={totalPages() > 1}>
          <div class="pagination">
            <button onClick={() => setPage(Math.max(0, page() - 1))} disabled={page() === 0}>
              Prev
            </button>
            <span>
              Page {page() + 1} / {totalPages()}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages() - 1, page() + 1))}
              disabled={page() === totalPages() - 1}
            >
              Next
            </button>
          </div>
        </Show>
      </Show>

      {/* Player detail overlay */}
      <Show when={selectedPlayer()}>
        <div class="overlay" onClick={() => setSelectedPlayer(null)}>
          <div class="overlay-content" onClick={(e) => e.stopPropagation()}>
            <PlayerCard
              playerId={selectedPlayer().id}
              name={selectedPlayer().name}
              mmr={selectedPlayer().mmr}
              winRate={selectedPlayer().winRate?.toFixed(1)}
              gamesPlayed={selectedPlayer().gamesPlayed}
              streak={selectedPlayer().streak ?? 0}
              onClose={() => setSelectedPlayer(null)}
            />
          </div>
        </div>
      </Show>
    </div>
  );
}
