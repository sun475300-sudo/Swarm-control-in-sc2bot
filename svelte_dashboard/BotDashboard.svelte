<!-- Phase 579: Svelte Dashboard -->
<!-- SC2 Bot Real-Time Dashboard — Svelte Component -->
<!-- Standalone-runnable: paste into a SvelteKit or Svelte app's +page.svelte -->

<script>
  import { onMount, onDestroy } from 'svelte';
  import { fade, fly, scale } from 'svelte/transition';
  import { tweened } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';

  // ─────────────────────────────────────────────
  // Reactive state
  // ─────────────────────────────────────────────
  let gameState     = 'IDLE';      // IDLE | IN_GAME | VICTORY | DEFEAT
  let minerals      = 50;
  let gas           = 0;
  let supply        = 12;
  let supplyMax     = 15;
  let winRate       = 0.0;
  let apm           = 0;
  let gameTime      = 0;           // seconds
  let threatLevel   = 0;           // 0-100
  let race          = 'Zerg';
  let opponentRace  = 'Terran';
  let mapName       = 'Blackburn LE';
  let gamesPlayed   = 0;
  let wins          = 0;

  /** @type {{ time: number, minerals: number, gas: number }[]} */
  let economyHistory = [];
  const MAX_HISTORY  = 60;

  /** @type {{ ts: string, text: string, type: 'info'|'warning'|'danger'|'success' }[]} */
  let actionLog = [];
  const MAX_LOG = 20;

  // Tweened values for smooth gauge animations
  const tweenedWinRate  = tweened(0, { duration: 600, easing: cubicOut });
  const tweenedThreat   = tweened(0, { duration: 400, easing: cubicOut });
  const tweenedAPM      = tweened(0, { duration: 300, easing: cubicOut });

  // ─────────────────────────────────────────────
  // Derived reactive statements
  // ─────────────────────────────────────────────
  $: supplyPercent   = Math.min(100, (supply / supplyMax) * 100);
  $: isSupplyBlocked = supply >= supplyMax;
  $: economyRate     = minerals + gas * 1.5;  // weighted economy score
  $: threatColor     = $tweenedThreat > 70 ? '#ff2244'
                     : $tweenedThreat > 40 ? '#ffaa00'
                     : '#00ff88';
  $: gameTimeFormatted = formatTime(gameTime);
  $: winRatePct        = ($tweenedWinRate * 100).toFixed(1);

  // Update tweened stores whenever reactive sources change
  $: tweenedWinRate.set(winRate);
  $: tweenedThreat.set(threatLevel);
  $: tweenedAPM.set(apm);

  // ─────────────────────────────────────────────
  // Utility helpers
  // ─────────────────────────────────────────────
  function formatTime(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function addLog(text, type = 'info') {
    const ts = new Date().toLocaleTimeString('en-US', { hour12: false });
    actionLog = [{ ts, text, type }, ...actionLog].slice(0, MAX_LOG);
  }

  function randomIn(lo, hi) {
    return lo + Math.random() * (hi - lo);
  }

  // ─────────────────────────────────────────────
  // Simulated WebSocket connection
  // ─────────────────────────────────────────────
  let ws = null;
  let wsStatus = 'disconnected';

  function connectWebSocket() {
    // In production: ws = new WebSocket('ws://localhost:8765/bot-state');
    // Here we simulate the WS lifecycle.
    wsStatus = 'connecting';
    addLog('Connecting to bot WebSocket…', 'info');

    setTimeout(() => {
      wsStatus = 'connected';
      addLog('WebSocket connected — streaming bot telemetry', 'success');
      gameState = 'IN_GAME';
      startGame();
    }, 800);
  }

  function disconnectWebSocket() {
    if (ws) { ws.close(); ws = null; }
    wsStatus = 'disconnected';
    addLog('WebSocket disconnected', 'warning');
  }

  // ─────────────────────────────────────────────
  // Interval-based simulation — mimics bot telemetry stream
  // ─────────────────────────────────────────────
  let simInterval  = null;
  let tickInterval = null;

  function startGame() {
    const maps    = ['Blackburn LE', 'Submarine LE', 'Crimson Court', 'Ancient Cistern LE'];
    const races   = ['Terran', 'Zerg', 'Protoss'];
    mapName       = maps[Math.floor(Math.random() * maps.length)];
    opponentRace  = races[Math.floor(Math.random() * races.length)];
    gameTime      = 0;
    minerals      = 50;
    gas           = 0;
    supply        = 12;
    supplyMax     = 15;
    threatLevel   = 0;
    economyHistory = [];
    addLog(`Game started on ${mapName} vs ${opponentRace}`, 'info');

    // Game clock — ticks every 1s
    tickInterval = setInterval(() => {
      gameTime += 1;
    }, 1000);

    // State updates — every 500ms
    simInterval = setInterval(() => {
      if (gameState !== 'IN_GAME') return;

      // Economy simulation
      const mRate = randomIn(50, 120);
      const gRate = randomIn(0, 60);
      minerals    = clamp(minerals + mRate - randomIn(0, 80), 0, 9999);
      gas         = clamp(gas + gRate - randomIn(0, 40), 0, 9999);

      // Supply creep
      if (supply < supplyMax - 2 && Math.random() < 0.3) {
        supply = clamp(supply + Math.ceil(randomIn(1, 4)), 0, supplyMax);
      }
      if (supplyMax < 200 && Math.random() < 0.15) {
        supplyMax = Math.min(200, supplyMax + 8);
      }

      // APM simulation (peaks in mid game)
      const targetAPM = gameTime < 120 ? randomIn(80, 150)
                      : gameTime < 600 ? randomIn(150, 280)
                      : randomIn(120, 220);
      apm = Math.round(targetAPM + randomIn(-15, 15));

      // Threat level
      const threatDelta = randomIn(-8, 12) * (Math.random() < 0.2 ? 2 : 1);
      threatLevel = clamp(threatLevel + threatDelta, 0, 100);

      // Economy history snapshot
      economyHistory = [
        ...economyHistory,
        { time: gameTime, minerals: Math.round(minerals), gas: Math.round(gas) }
      ].slice(-MAX_HISTORY);

      // Periodic action log entries
      if (Math.random() < 0.12) {
        const actions = [
          ['Building Spawning Pool', 'info'],
          ['Sending scout drone', 'info'],
          ['Producing 4 Zerglings', 'info'],
          ['Expanding to natural', 'success'],
          ['Enemy spotted! 6-pool rush incoming', 'danger'],
          ['Rallying army to front', 'warning'],
          ['Lair upgrade started', 'success'],
          ['Overlord spotted near main', 'warning'],
          ['Roach Warren complete', 'success'],
          ['Baneling nest started', 'info'],
          ['Retreating — army outmatched', 'danger'],
        ];
        const [text, type] = actions[Math.floor(Math.random() * actions.length)];
        addLog(text, type);
      }

      // Threat spike events
      if (threatLevel > 80 && Math.random() < 0.05) {
        addLog('CRITICAL: Enemy army at main base!', 'danger');
      }

      // Win/loss event after 3–8 minutes
      if (gameTime > randomIn(180, 480) && Math.random() < 0.008) {
        const won = Math.random() < (winRate > 0 ? winRate + 0.05 : 0.5);
        endGame(won);
      }
    }, 500);
  }

  function endGame(won) {
    clearInterval(simInterval);
    clearInterval(tickInterval);
    simInterval  = null;
    tickInterval = null;

    gameState = won ? 'VICTORY' : 'DEFEAT';
    gamesPlayed++;
    if (won) wins++;
    winRate = gamesPlayed > 0 ? wins / gamesPlayed : 0;

    addLog(
      won ? `VICTORY on ${mapName}! (${formatTime(gameTime)})` : `DEFEAT on ${mapName}. Analyzing…`,
      won ? 'success' : 'danger'
    );

    // Auto-restart after 3s
    setTimeout(() => {
      if (wsStatus === 'connected') {
        gameState = 'IN_GAME';
        startGame();
      }
    }, 3000);
  }

  function handleResetStats() {
    gamesPlayed = 0;
    wins        = 0;
    winRate     = 0;
    addLog('Stats reset by operator', 'warning');
  }

  // ─────────────────────────────────────────────
  // Lifecycle
  // ─────────────────────────────────────────────
  onMount(() => {
    addLog('SC2 Bot Dashboard initialised', 'info');
    connectWebSocket();
  });

  onDestroy(() => {
    clearInterval(simInterval);
    clearInterval(tickInterval);
    disconnectWebSocket();
  });
</script>

<!-- ─────────────────────────────────────────── -->
<!-- Template                                     -->
<!-- ─────────────────────────────────────────── -->

<main class="dashboard">
  <!-- Header -->
  <header class="header">
    <div class="header-left">
      <span class="logo">⬡ SC2 BOT</span>
      <span class="race-badge">{race}</span>
      <span class="ws-dot" class:connected={wsStatus === 'connected'}></span>
      <span class="ws-label">{wsStatus.toUpperCase()}</span>
    </div>
    <div class="header-center">
      <span class="map-label">{mapName}</span>
      <span class="vs-label">vs {opponentRace}</span>
      <span class="game-clock">{gameTimeFormatted}</span>
    </div>
    <div class="header-right">
      <span
        class="state-badge"
        class:victory={gameState === 'VICTORY'}
        class:defeat={gameState === 'DEFEAT'}
        class:ingame={gameState === 'IN_GAME'}
      >{gameState}</span>
      <button class="btn-reset" on:click={handleResetStats}>Reset Stats</button>
    </div>
  </header>

  <!-- Main grid -->
  <div class="grid">

    <!-- Economy Panel -->
    <section class="panel economy-panel" in:fly="{{ y: -20, duration: 400 }}">
      <h2 class="panel-title">Economy</h2>
      <div class="resource-row">
        <div class="resource mineral">
          <span class="res-icon">◆</span>
          <span class="res-value">{Math.round(minerals).toLocaleString()}</span>
          <span class="res-label">Minerals</span>
        </div>
        <div class="resource gas">
          <span class="res-icon">⬡</span>
          <span class="res-value">{Math.round(gas).toLocaleString()}</span>
          <span class="res-label">Vespene</span>
        </div>
        <div class="resource eco-score">
          <span class="res-icon">★</span>
          <span class="res-value">{Math.round(economyRate)}</span>
          <span class="res-label">Eco Score</span>
        </div>
      </div>

      <!-- Economy Chart (SVG sparkline) -->
      <div class="chart-wrapper">
        <svg class="sparkline" viewBox="0 0 300 60" preserveAspectRatio="none">
          {#if economyHistory.length > 1}
            <!-- Minerals line -->
            <polyline
              class="line-minerals"
              points={economyHistory.map((d, i) => {
                const x = (i / (economyHistory.length - 1)) * 300;
                const y = 60 - (d.minerals / 9999) * 58;
                return `${x},${y}`;
              }).join(' ')}
              fill="none"
              stroke="#44aaff"
              stroke-width="1.5"
            />
            <!-- Gas line -->
            <polyline
              class="line-gas"
              points={economyHistory.map((d, i) => {
                const x = (i / (economyHistory.length - 1)) * 300;
                const y = 60 - (d.gas / 9999) * 58;
                return `${x},${y}`;
              }).join(' ')}
              fill="none"
              stroke="#44ffaa"
              stroke-width="1.5"
            />
          {/if}
        </svg>
        <div class="chart-legend">
          <span class="legend-dot mineral-dot">◆ Minerals</span>
          <span class="legend-dot gas-dot">⬡ Gas</span>
        </div>
      </div>
    </section>

    <!-- Army Supply Meter -->
    <section class="panel supply-panel" in:fly="{{ y: -20, duration: 500 }}">
      <h2 class="panel-title">Army Supply</h2>
      <div class="supply-numbers">
        <span class="supply-current" class:blocked={isSupplyBlocked}>{supply}</span>
        <span class="supply-sep">/</span>
        <span class="supply-max">{supplyMax}</span>
      </div>
      <div class="supply-bar-track">
        <div
          class="supply-bar-fill"
          style="width: {supplyPercent}%; background: {isSupplyBlocked ? '#ff2244' : '#00ff88'};"
        ></div>
      </div>
      {#if isSupplyBlocked}
        <p class="supply-alert" in:scale="{{ duration: 200 }}">⚠ SUPPLY BLOCKED</p>
      {/if}
      <div class="supply-tiers">
        {#each [25, 50, 75, 100, 125, 150, 175, 200] as tier}
          <span
            class="tier-mark"
            class:active={supply >= tier}
            style="left: {(tier / 200) * 100}%"
          >{tier}</span>
        {/each}
      </div>
    </section>

    <!-- Win Rate Gauge -->
    <section class="panel gauge-panel" in:fly="{{ y: -20, duration: 600 }}">
      <h2 class="panel-title">Win Rate</h2>
      <div class="gauge-container">
        <svg class="gauge-svg" viewBox="0 0 120 80">
          <!-- Background arc -->
          <path
            d="M 10 70 A 50 50 0 0 1 110 70"
            fill="none" stroke="#1a2a1a" stroke-width="10"
          />
          <!-- Value arc — stroke-dasharray driven by win rate -->
          <path
            d="M 10 70 A 50 50 0 0 1 110 70"
            fill="none"
            stroke={$tweenedWinRate >= 0.55 ? '#00ff88' : $tweenedWinRate >= 0.40 ? '#ffaa00' : '#ff2244'}
            stroke-width="10"
            stroke-dasharray="{($tweenedWinRate * 157).toFixed(1)} 157"
            stroke-linecap="round"
          />
          <text x="60" y="66" text-anchor="middle" class="gauge-text">{winRatePct}%</text>
        </svg>
      </div>
      <div class="gauge-stats">
        <span>{wins}W / {gamesPlayed - wins}L</span>
        <span>{gamesPlayed} games</span>
      </div>
    </section>

    <!-- APM Counter -->
    <section class="panel apm-panel" in:fly="{{ x: 20, duration: 400 }}">
      <h2 class="panel-title">Actions Per Minute</h2>
      <div class="apm-display">
        <span
          class="apm-value"
          class:apm-high={$tweenedAPM > 200}
          class:apm-low={$tweenedAPM < 100}
        >{Math.round($tweenedAPM)}</span>
        <span class="apm-label">APM</span>
      </div>
      <div class="apm-bar-track">
        <div
          class="apm-bar-fill"
          style="width: {Math.min(100, ($tweenedAPM / 400) * 100)}%"
        ></div>
      </div>
      <div class="apm-tier-labels">
        <span>0</span><span>100</span><span>200</span><span>300</span><span>400</span>
      </div>
    </section>

    <!-- Threat Indicator -->
    <section class="panel threat-panel" in:fly="{{ x: -20, duration: 400 }}">
      <h2 class="panel-title">Threat Level</h2>
      <div class="threat-ring-wrapper">
        <svg class="threat-ring" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#1a1a2a" stroke-width="8"/>
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke={threatColor}
            stroke-width="8"
            stroke-dasharray="{(($tweenedThreat / 100) * 251).toFixed(1)} 251"
            stroke-dashoffset="62.75"
            stroke-linecap="round"
          />
          <text x="50" y="55" text-anchor="middle" class="threat-text">
            {Math.round($tweenedThreat)}
          </text>
        </svg>
      </div>
      <div class="threat-label" style="color: {threatColor}">
        {$tweenedThreat > 70 ? 'CRITICAL' : $tweenedThreat > 40 ? 'MODERATE' : 'LOW'}
      </div>
    </section>

    <!-- Action Log -->
    <section class="panel log-panel" in:fade="{{ duration: 600 }}">
      <h2 class="panel-title">Action Log</h2>
      <ul class="action-log">
        {#each actionLog as entry (entry.ts + entry.text)}
          <li
            class="log-entry {entry.type}"
            in:fly="{{ y: -10, duration: 250 }}"
          >
            <span class="log-ts">{entry.ts}</span>
            <span class="log-text">{entry.text}</span>
          </li>
        {/each}
        {#if actionLog.length === 0}
          <li class="log-empty">Waiting for bot actions…</li>
        {/if}
      </ul>
    </section>

  </div><!-- /grid -->
</main>


<!-- ─────────────────────────────────────────── -->
<!-- Scoped Styles — Dark theme, neon accents    -->
<!-- ─────────────────────────────────────────── -->

<style>
  /* ── Reset / Base ── */
  :global(*) { box-sizing: border-box; margin: 0; padding: 0; }

  .dashboard {
    background: #0a0f0a;
    color: #c8ffc8;
    font-family: 'Consolas', 'Courier New', monospace;
    min-height: 100vh;
    padding: 0 0 2rem;
  }

  /* ── Header ── */
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1.5rem;
    background: #0d1a0d;
    border-bottom: 1px solid #1a4a1a;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .header-left, .header-center, .header-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .logo {
    font-size: 1.2rem;
    font-weight: bold;
    color: #00ff88;
    letter-spacing: 2px;
  }
  .race-badge {
    background: #00ff8822;
    border: 1px solid #00ff8855;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.8rem;
    color: #00ff88;
  }
  .ws-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #ff4444;
    transition: background 0.4s;
  }
  .ws-dot.connected { background: #00ff88; box-shadow: 0 0 6px #00ff88; }
  .ws-label { font-size: 0.75rem; color: #668866; }

  .map-label { font-size: 0.9rem; color: #aaffaa; }
  .vs-label  { font-size: 0.8rem; color: #88aa88; }
  .game-clock {
    font-size: 1.1rem;
    color: #44ffaa;
    letter-spacing: 1px;
    font-weight: bold;
  }

  .state-badge {
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
    background: #1a2a1a;
    border: 1px solid #2a4a2a;
    color: #aaaaaa;
  }
  .state-badge.ingame  { background: #002a10; border-color: #00aa44; color: #00ff88; }
  .state-badge.victory { background: #003300; border-color: #00ff00; color: #88ff88; }
  .state-badge.defeat  { background: #2a0000; border-color: #ff2244; color: #ff8888; }

  .btn-reset {
    background: #1a1a2a;
    border: 1px solid #334;
    color: #88aacc;
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
    font-family: inherit;
    transition: background 0.2s;
  }
  .btn-reset:hover { background: #222244; color: #aaccff; }

  /* ── Grid ── */
  .grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: auto auto;
    gap: 1rem;
    padding: 1rem 1.5rem;
  }
  @media (max-width: 900px) {
    .grid { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 600px) {
    .grid { grid-template-columns: 1fr; }
  }

  /* ── Panel base ── */
  .panel {
    background: #0d150d;
    border: 1px solid #1a3a1a;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    position: relative;
  }
  .panel-title {
    font-size: 0.75rem;
    color: #557755;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid #1a3a1a;
    padding-bottom: 0.4rem;
  }

  /* ── Economy Panel ── */
  .economy-panel { grid-column: span 2; }
  .resource-row {
    display: flex;
    gap: 2rem;
    margin-bottom: 0.75rem;
  }
  .resource {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }
  .res-icon  { font-size: 1rem; }
  .res-value { font-size: 1.6rem; font-weight: bold; line-height: 1.1; }
  .res-label { font-size: 0.7rem; color: #668866; }
  .mineral .res-icon, .mineral .res-value { color: #44aaff; }
  .gas     .res-icon, .gas     .res-value { color: #44ffaa; }
  .eco-score .res-icon, .eco-score .res-value { color: #ffdd44; }

  .chart-wrapper {
    position: relative;
    height: 60px;
    border: 1px solid #1a3a1a;
    border-radius: 4px;
    overflow: hidden;
    background: #080d08;
  }
  .sparkline { width: 100%; height: 100%; }
  .chart-legend {
    position: absolute;
    top: 4px; right: 8px;
    font-size: 0.65rem;
    display: flex;
    gap: 0.75rem;
  }
  .mineral-dot { color: #44aaff; }
  .gas-dot     { color: #44ffaa; }

  /* ── Supply Panel ── */
  .supply-numbers {
    display: flex;
    align-items: baseline;
    gap: 0.25rem;
    margin-bottom: 0.6rem;
  }
  .supply-current {
    font-size: 2.5rem;
    font-weight: bold;
    color: #00ff88;
    transition: color 0.3s;
  }
  .supply-current.blocked { color: #ff2244; }
  .supply-sep  { font-size: 1.2rem; color: #446644; }
  .supply-max  { font-size: 1.8rem; color: #88aa88; }

  .supply-bar-track {
    height: 10px;
    background: #0a180a;
    border-radius: 5px;
    overflow: hidden;
    margin-bottom: 0.4rem;
    border: 1px solid #1a4a1a;
  }
  .supply-bar-fill {
    height: 100%;
    border-radius: 5px;
    transition: width 0.4s ease, background 0.3s;
  }
  .supply-alert {
    font-size: 0.85rem;
    font-weight: bold;
    color: #ff2244;
    text-align: center;
    animation: blink 0.8s step-start infinite;
  }
  @keyframes blink {
    50% { opacity: 0; }
  }
  .supply-tiers {
    position: relative;
    height: 16px;
    margin-top: 0.2rem;
  }
  .tier-mark {
    position: absolute;
    transform: translateX(-50%);
    font-size: 0.6rem;
    color: #334433;
    transition: color 0.3s;
  }
  .tier-mark.active { color: #00ff8888; }

  /* ── Win Rate Gauge ── */
  .gauge-container { display: flex; justify-content: center; }
  .gauge-svg { width: 140px; height: 95px; }
  .gauge-text {
    font-family: 'Consolas', monospace;
    font-size: 18px;
    font-weight: bold;
    fill: #00ff88;
  }
  .gauge-stats {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #668866;
    margin-top: 0.4rem;
  }

  /* ── APM Panel ── */
  .apm-display {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.6rem;
  }
  .apm-value {
    font-size: 3rem;
    font-weight: bold;
    color: #44aaff;
    transition: color 0.4s;
    line-height: 1;
  }
  .apm-value.apm-high { color: #00ff88; }
  .apm-value.apm-low  { color: #888888; }
  .apm-label { font-size: 1rem; color: #446688; }

  .apm-bar-track {
    height: 8px;
    background: #0a0a18;
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid #1a1a4a;
    margin-bottom: 0.25rem;
  }
  .apm-bar-fill {
    height: 100%;
    background: linear-gradient(to right, #1144ff, #44aaff, #00ff88);
    border-radius: 4px;
    transition: width 0.3s ease;
  }
  .apm-tier-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.6rem;
    color: #334455;
  }

  /* ── Threat Panel ── */
  .threat-ring-wrapper { display: flex; justify-content: center; }
  .threat-ring { width: 100px; height: 100px; }
  .threat-text {
    font-family: 'Consolas', monospace;
    font-size: 22px;
    font-weight: bold;
    fill: currentColor;
  }
  .threat-label {
    text-align: center;
    font-size: 0.85rem;
    font-weight: bold;
    letter-spacing: 2px;
    margin-top: 0.4rem;
    transition: color 0.4s;
  }

  /* ── Action Log ── */
  .log-panel { grid-column: span 2; }
  .action-log {
    list-style: none;
    max-height: 220px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: #1a4a1a #080d08;
  }
  .action-log::-webkit-scrollbar { width: 6px; }
  .action-log::-webkit-scrollbar-track { background: #080d08; }
  .action-log::-webkit-scrollbar-thumb { background: #1a4a1a; border-radius: 3px; }

  .log-entry {
    display: flex;
    gap: 0.75rem;
    padding: 3px 0;
    border-bottom: 1px solid #0d180d;
    font-size: 0.8rem;
    align-items: baseline;
  }
  .log-ts   { color: #335533; flex-shrink: 0; font-size: 0.7rem; }
  .log-text { color: #aaccaa; }

  .log-entry.info    .log-text { color: #88aacc; }
  .log-entry.success .log-text { color: #44ff88; }
  .log-entry.warning .log-text { color: #ffaa44; }
  .log-entry.danger  .log-text { color: #ff4455; font-weight: bold; }

  .log-empty { color: #335533; font-size: 0.8rem; padding: 0.5rem 0; }
</style>
