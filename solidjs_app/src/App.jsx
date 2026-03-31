import { createSignal, createResource, Show, For } from 'solid-js';

// Async fetch for ladder statistics
async function fetchLadderStats(matchup) {
  const res = await fetch(`/api/ladder?matchup=${matchup}`);
  if (!res.ok) throw new Error('Failed to fetch ladder stats');
  return res.json();
}

// Color-code win rate
function winRateColor(rate) {
  if (rate >= 55) return '#22c55e';
  if (rate >= 45) return '#eab308';
  return '#ef4444';
}

export default function App() {
  const [matchup, setMatchup] = createSignal('ZvT');
  const [selectedPlayer, setSelectedPlayer] = createSignal(null);

  // Reactive resource: re-fetches whenever matchup() changes
  const [stats, { refetch }] = createResource(matchup, fetchLadderStats);

  // Derived win rate percentage
  const winRatePct = () => {
    const data = stats();
    if (!data || !data.summary) return null;
    const { wins, losses } = data.summary;
    const total = wins + losses;
    if (total === 0) return null;
    return ((wins / total) * 100).toFixed(1);
  };

  return (
    <div class="app">
      <h1>SC2 Zerg Ladder Stats</h1>

      {/* Matchup selector */}
      <div class="matchup-bar">
        <For each={['ZvT', 'ZvZ', 'ZvP']}>
          {(mu) => (
            <button
              class={matchup() === mu ? 'active' : ''}
              onClick={() => setMatchup(mu)}
            >
              {mu}
            </button>
          )}
        </For>
        <button onClick={refetch} class="refresh">Refresh</button>
      </div>

      {/* Summary win rate */}
      <Show when={winRatePct() !== null} fallback={<p class="loading">Loading stats…</p>}>
        <div class="summary">
          <span>Win Rate: </span>
          <span style={{ color: winRateColor(parseFloat(winRatePct())) }}>
            {winRatePct()}%
          </span>
          <span> ({stats()?.summary?.wins}W / {stats()?.summary?.losses}L)</span>
        </div>
      </Show>

      {/* Leaderboard */}
      <Show when={stats()} fallback={<p class="loading">Fetching leaderboard…</p>}>
        <table class="leaderboard">
          <thead>
            <tr><th>Rank</th><th>Player</th><th>MMR</th><th>W</th><th>L</th><th>Win%</th></tr>
          </thead>
          <tbody>
            <For each={stats()?.leaderboard ?? []}>
              {(entry, i) => {
                const pct = ((entry.wins / (entry.wins + entry.losses)) * 100).toFixed(1);
                return (
                  <tr
                    class={selectedPlayer() === entry.name ? 'selected' : ''}
                    onClick={() => setSelectedPlayer(entry.name)}
                  >
                    <td>{i() + 1}</td>
                    <td>{entry.name}</td>
                    <td>{entry.mmr}</td>
                    <td style={{ color: '#22c55e' }}>{entry.wins}</td>
                    <td style={{ color: '#ef4444' }}>{entry.losses}</td>
                    <td style={{ color: winRateColor(parseFloat(pct)) }}>{pct}%</td>
                  </tr>
                );
              }}
            </For>
          </tbody>
        </table>
      </Show>

      {/* Selected player detail */}
      <Show when={selectedPlayer()}>
        <div class="detail">Selected: <strong>{selectedPlayer()}</strong></div>
      </Show>
    </div>
  );
}
