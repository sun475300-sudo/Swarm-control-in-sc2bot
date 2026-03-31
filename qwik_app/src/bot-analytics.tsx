import {
  component$,
  useSignal,
  useStore,
  $,
  useVisibleTask$,
  useResource$,
  Resource,
} from '@builder.io/qwik';

// ── Types ──────────────────────────────────────────────────────────────────────
interface MatchRecord {
  id: string;
  date: string;
  opponent: string;
  matchup: string;   // e.g. "ZvT"
  map: string;
  result: 'Win' | 'Loss';
  duration: string;  // e.g. "12:34"
  mmrDelta: number;
}

interface BuildOrderStep {
  supply: number;
  action: string;
  timing: string;
}

interface BuildOrder {
  name: string;
  matchup: string;
  winRate: number;
  gamesPlayed: number;
  steps: BuildOrderStep[];
}

interface AnalyticsStore {
  selectedMatchup: string;
  selectedBuild: string | null;
  currentPage: number;
  pageSize: number;
  filterResult: 'All' | 'Win' | 'Loss';
  expandedBuild: string | null;
}

// ── Mock data fetchers (replace with real API calls) ──────────────────────────
const MOCK_MATCHES: MatchRecord[] = [
  { id: '1', date: '2026-03-30', opponent: 'TerranBot_v3', matchup: 'ZvT', map: 'Alcyone LE', result: 'Win',  duration: '11:42', mmrDelta: +22 },
  { id: '2', date: '2026-03-30', opponent: 'ProtossAI',    matchup: 'ZvP', map: 'Crimson Court LE', result: 'Loss', duration: '18:05', mmrDelta: -19 },
  { id: '3', date: '2026-03-29', opponent: 'ZergRush99',   matchup: 'ZvZ', map: 'Gresvan LE', result: 'Win',  duration: '08:17', mmrDelta: +25 },
  { id: '4', date: '2026-03-29', opponent: 'TerranBot_v3', matchup: 'ZvT', map: 'Neohumanity LE', result: 'Win',  duration: '14:33', mmrDelta: +18 },
  { id: '5', date: '2026-03-28', opponent: 'PsiStorm',     matchup: 'ZvP', map: 'Alcyone LE', result: 'Loss', duration: '22:11', mmrDelta: -21 },
  { id: '6', date: '2026-03-28', opponent: 'ZergRush99',   matchup: 'ZvZ', map: 'Crimson Court LE', result: 'Win',  duration: '07:55', mmrDelta: +24 },
  { id: '7', date: '2026-03-27', opponent: 'BioMech_AI',   matchup: 'ZvT', map: 'Gresvan LE', result: 'Win',  duration: '13:08', mmrDelta: +20 },
  { id: '8', date: '2026-03-27', opponent: 'VoidRay_Bot',  matchup: 'ZvP', map: 'Neohumanity LE', result: 'Win',  duration: '16:44', mmrDelta: +22 },
];

const MOCK_BUILDS: BuildOrder[] = [
  {
    name: 'Roach-Ravager All-In',
    matchup: 'ZvT',
    winRate: 68.5,
    gamesPlayed: 54,
    steps: [
      { supply: 13, action: 'Overlord', timing: '0:17' },
      { supply: 17, action: 'Hatchery (natural)', timing: '1:50' },
      { supply: 18, action: 'Extractor', timing: '2:05' },
      { supply: 18, action: 'Spawning Pool', timing: '2:10' },
      { supply: 20, action: 'Queen x2', timing: '2:55' },
      { supply: 28, action: 'Roach Warren', timing: '3:40' },
      { supply: 44, action: 'Move out with 8 Roach + 4 Ravager', timing: '5:30' },
    ],
  },
  {
    name: 'Ling-Bane-Muta',
    matchup: 'ZvT',
    winRate: 54.2,
    gamesPlayed: 89,
    steps: [
      { supply: 13, action: 'Overlord', timing: '0:17' },
      { supply: 17, action: 'Hatchery (natural)', timing: '1:50' },
      { supply: 18, action: 'Spawning Pool', timing: '2:05' },
      { supply: 22, action: 'Extractor x2', timing: '2:50' },
      { supply: 24, action: 'Baneling Nest', timing: '3:15' },
      { supply: 28, action: 'Spire', timing: '4:20' },
      { supply: 60, action: 'Engage with Ling-Bane-Muta', timing: '7:30' },
    ],
  },
  {
    name: 'Nydus-Swarm Host',
    matchup: 'ZvP',
    winRate: 61.0,
    gamesPlayed: 41,
    steps: [
      { supply: 13, action: 'Overlord', timing: '0:17' },
      { supply: 17, action: 'Hatchery (natural)', timing: '1:50' },
      { supply: 18, action: 'Spawning Pool', timing: '2:05' },
      { supply: 30, action: 'Hatchery (third)', timing: '3:30' },
      { supply: 36, action: 'Nydus Network', timing: '5:00' },
      { supply: 48, action: 'Swarm Host x4 + Nydus worm', timing: '7:00' },
    ],
  },
];

// ── Win-rate bar component ─────────────────────────────────────────────────────
export const WinRateBar = component$<{ rate: number; label?: string }>((props) => {
  const color =
    props.rate >= 60 ? '#22c55e' : props.rate >= 50 ? '#eab308' : '#ef4444';
  return (
    <div class="winrate-bar-container">
      {props.label && <span class="winrate-label">{props.label}</span>}
      <div class="winrate-track">
        <div
          class="winrate-fill"
          style={{ width: `${props.rate}%`, background: color }}
        />
      </div>
      <span class="winrate-value" style={{ color }}>
        {props.rate.toFixed(1)}%
      </span>
    </div>
  );
});

// ── Build Order Accordion ──────────────────────────────────────────────────────
export const BuildOrderAccordion = component$<{
  build: BuildOrder;
  isOpen: boolean;
  onToggle$: () => void;
}>((props) => {
  return (
    <div class="build-accordion">
      <div class="build-header" onClick$={props.onToggle$}>
        <div class="build-title">
          <span class="build-name">{props.build.name}</span>
          <span class="build-matchup">{props.build.matchup}</span>
        </div>
        <div class="build-meta">
          <WinRateBar rate={props.build.winRate} />
          <span class="build-games">{props.build.gamesPlayed} games</span>
          <span class="accordion-arrow">{props.isOpen ? '▲' : '▼'}</span>
        </div>
      </div>
      {props.isOpen && (
        <div class="build-steps">
          <table class="steps-table">
            <thead>
              <tr>
                <th>Supply</th>
                <th>Action</th>
                <th>Timing</th>
              </tr>
            </thead>
            <tbody>
              {props.build.steps.map((step) => (
                <tr key={step.action + step.timing}>
                  <td class="supply-cell">[{step.supply}]</td>
                  <td>{step.action}</td>
                  <td class="timing-cell">{step.timing}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
});

// ── Match History Table ────────────────────────────────────────────────────────
export const MatchHistoryTable = component$<{
  matches: MatchRecord[];
  page: number;
  pageSize: number;
  filterResult: string;
  onPageChange$: (p: number) => void;
  onFilterChange$: (f: string) => void;
}>((props) => {
  const filtered = props.matches.filter(
    (m) => props.filterResult === 'All' || m.result === props.filterResult
  );
  const totalPages = Math.ceil(filtered.length / props.pageSize);
  const paged = filtered.slice(
    props.page * props.pageSize,
    (props.page + 1) * props.pageSize
  );

  return (
    <div class="match-history">
      <div class="match-controls">
        <h3>Match History</h3>
        <div class="filter-buttons">
          {(['All', 'Win', 'Loss'] as const).map((f) => (
            <button
              key={f}
              class={props.filterResult === f ? 'active' : ''}
              onClick$={() => props.onFilterChange$(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <table class="match-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Opponent</th>
            <th>Matchup</th>
            <th>Map</th>
            <th>Result</th>
            <th>Duration</th>
            <th>MMR Δ</th>
          </tr>
        </thead>
        <tbody>
          {paged.map((match) => (
            <tr key={match.id} class={match.result === 'Win' ? 'win-row' : 'loss-row'}>
              <td class="date-cell">{match.date}</td>
              <td>{match.opponent}</td>
              <td class="matchup-cell">{match.matchup}</td>
              <td class="map-cell">{match.map}</td>
              <td>
                <span class={`result-badge ${match.result === 'Win' ? 'win' : 'loss'}`}>
                  {match.result}
                </span>
              </td>
              <td>{match.duration}</td>
              <td
                style={{
                  color: match.mmrDelta > 0 ? '#22c55e' : '#ef4444',
                  fontWeight: 'bold',
                }}
              >
                {match.mmrDelta > 0 ? `+${match.mmrDelta}` : match.mmrDelta}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {totalPages > 1 && (
        <div class="pagination">
          <button
            onClick$={() => props.onPageChange$(Math.max(0, props.page - 1))}
            disabled={props.page === 0}
          >
            Prev
          </button>
          <span>
            {props.page + 1} / {totalPages}
          </span>
          <button
            onClick$={() => props.onPageChange$(Math.min(totalPages - 1, props.page + 1))}
            disabled={props.page === totalPages - 1}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
});

// ── Summary Stats Card ─────────────────────────────────────────────────────────
export const SummaryCard = component$<{
  matches: MatchRecord[];
  matchup: string;
}>((props) => {
  const filtered =
    props.matchup === 'All'
      ? props.matches
      : props.matches.filter((m) => m.matchup === props.matchup);

  const wins = filtered.filter((m) => m.result === 'Win').length;
  const total = filtered.length;
  const winRate = total > 0 ? (wins / total) * 100 : 0;
  const totalMmr = filtered.reduce((acc, m) => acc + m.mmrDelta, 0);

  return (
    <div class="summary-cards">
      <div class="stat-card">
        <div class="stat-label">Total Games</div>
        <div class="stat-value">{total}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Wins</div>
        <div class="stat-value win">{wins}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Losses</div>
        <div class="stat-value loss">{total - wins}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Win Rate</div>
        <div class="stat-value" style={{ color: winRate >= 50 ? '#22c55e' : '#ef4444' }}>
          {winRate.toFixed(1)}%
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Net MMR</div>
        <div class="stat-value" style={{ color: totalMmr >= 0 ? '#22c55e' : '#ef4444' }}>
          {totalMmr > 0 ? `+${totalMmr}` : totalMmr}
        </div>
      </div>
    </div>
  );
});

// ── Root Analytics Component ───────────────────────────────────────────────────
export const BotAnalytics = component$(() => {
  // Signals for lightweight reactive values
  const activeTab = useSignal<'overview' | 'history' | 'builds'>('overview');
  const selectedMatchup = useSignal('All');
  const expandedBuild = useSignal<string | null>(null);

  // Store for complex mutable state
  const state = useStore<AnalyticsStore>({
    selectedMatchup: 'All',
    selectedBuild: null,
    currentPage: 0,
    pageSize: 5,
    filterResult: 'All',
    expandedBuild: null,
  });

  // useVisibleTask$: runs only in the browser after hydration (resumability)
  useVisibleTask$(() => {
    // Set up polling for real-time updates — only runs client-side
    const interval = setInterval(() => {
      // In a real app: fetch new match data and update store
      console.log('[BotAnalytics] Polling for new match data...');
    }, 30_000);
    return () => clearInterval(interval);
  });

  // Serializable event handlers using $()
  const handleTabChange = $((tab: 'overview' | 'history' | 'builds') => {
    activeTab.value = tab;
  });

  const handleMatchupChange = $((mu: string) => {
    selectedMatchup.value = mu;
    state.selectedMatchup = mu;
    state.currentPage = 0;
  });

  const handlePageChange = $((p: number) => {
    state.currentPage = p;
  });

  const handleFilterChange = $((f: string) => {
    state.filterResult = f as AnalyticsStore['filterResult'];
    state.currentPage = 0;
  });

  const handleBuildToggle = $((buildName: string) => {
    expandedBuild.value = expandedBuild.value === buildName ? null : buildName;
  });

  const filteredBuilds =
    selectedMatchup.value === 'All'
      ? MOCK_BUILDS
      : MOCK_BUILDS.filter((b) => b.matchup === selectedMatchup.value);

  return (
    <div class="bot-analytics">
      {/* Header */}
      <header class="analytics-header">
        <h1>SC2 Bot Analytics</h1>
        <p class="subtitle">Real-time performance dashboard — powered by Qwik resumability</p>
      </header>

      {/* Matchup filter */}
      <nav class="matchup-nav">
        {['All', 'ZvT', 'ZvZ', 'ZvP'].map((mu) => (
          <button
            key={mu}
            class={selectedMatchup.value === mu ? 'active' : ''}
            onClick$={() => handleMatchupChange(mu)}
          >
            {mu}
          </button>
        ))}
      </nav>

      {/* Tab navigation */}
      <div class="tab-bar">
        {(['overview', 'history', 'builds'] as const).map((tab) => (
          <button
            key={tab}
            class={activeTab.value === tab ? 'tab active' : 'tab'}
            onClick$={() => handleTabChange(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div class="tab-content">
        {activeTab.value === 'overview' && (
          <section class="overview-section">
            <SummaryCard matches={MOCK_MATCHES} matchup={selectedMatchup.value} />
            <div class="per-matchup-rates">
              <h3>Win Rate by Matchup</h3>
              {['ZvT', 'ZvZ', 'ZvP'].map((mu) => {
                const ms = MOCK_MATCHES.filter((m) => m.matchup === mu);
                const w = ms.filter((m) => m.result === 'Win').length;
                const rate = ms.length > 0 ? (w / ms.length) * 100 : 0;
                return (
                  <WinRateBar key={mu} rate={rate} label={mu} />
                );
              })}
            </div>
          </section>
        )}

        {activeTab.value === 'history' && (
          <MatchHistoryTable
            matches={
              selectedMatchup.value === 'All'
                ? MOCK_MATCHES
                : MOCK_MATCHES.filter((m) => m.matchup === selectedMatchup.value)
            }
            page={state.currentPage}
            pageSize={state.pageSize}
            filterResult={state.filterResult}
            onPageChange$={handlePageChange}
            onFilterChange$={handleFilterChange}
          />
        )}

        {activeTab.value === 'builds' && (
          <section class="builds-section">
            <h3>Build Order Analysis</h3>
            {filteredBuilds.map((build) => (
              <BuildOrderAccordion
                key={build.name}
                build={build}
                isOpen={expandedBuild.value === build.name}
                onToggle$={() => handleBuildToggle(build.name)}
              />
            ))}
          </section>
        )}
      </div>
    </div>
  );
});

export default BotAnalytics;
