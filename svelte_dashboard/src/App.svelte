<script>
  import { onMount, onDestroy } from 'svelte';
  import { writable, derived } from 'svelte/store';
  import Chart from 'chart.js/auto';

  // Reactive stores for game state
  const gameState = writable({ phase: 'early', supply: 0, minerals: 0, gas: 0 });
  const unitCounts = writable({ zergling: 0, roach: 0, hydralisk: 0, mutalisk: 0, ultralisk: 0 });
  const winHistory = writable([]);
  const selectedMatchup = writable('ZvT');
  const connected = writable(false);

  // Derived win rate
  const winRate = derived(winHistory, ($wh) => {
    if ($wh.length === 0) return 0;
    const wins = $wh.filter(r => r === 'win').length;
    return ((wins / $wh.length) * 100).toFixed(1);
  });

  let ws;
  let chartCanvas;
  let winRateChart;
  let refreshInterval;
  const matchups = ['ZvT', 'ZvZ', 'ZvP'];

  function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8765');
    ws.onopen = () => connected.set(true);
    ws.onclose = () => connected.set(false);
    ws.onerror = () => connected.set(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.gameState) gameState.set(data.gameState);
      if (data.unitCounts) unitCounts.set(data.unitCounts);
      if (data.result) winHistory.update(h => [...h.slice(-49), data.result]);
    };
  }

  function updateChart(history) {
    if (!winRateChart) return;
    const labels = history.map((_, i) => `G${i + 1}`);
    const cumWinRate = history.map((_, i) => {
      const wins = history.slice(0, i + 1).filter(r => r === 'win').length;
      return ((wins / (i + 1)) * 100).toFixed(1);
    });
    winRateChart.data.labels = labels;
    winRateChart.data.datasets[0].data = cumWinRate;
    winRateChart.update();
  }

  onMount(() => {
    connectWebSocket();

    winRateChart = new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Win Rate %',
          data: [],
          borderColor: '#a855f7',
          backgroundColor: 'rgba(168,85,247,0.15)',
          tension: 0.4,
          fill: true,
        }]
      },
      options: { responsive: true, scales: { y: { min: 0, max: 100 } } }
    });

    refreshInterval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping', matchup: $selectedMatchup }));
      }
    }, 2000);

    winHistory.subscribe(updateChart);
  });

  onDestroy(() => {
    clearInterval(refreshInterval);
    if (ws) ws.close();
  });

  let $unitCounts, $gameState, $winRate, $connected, $selectedMatchup, $winHistory;
  unitCounts.subscribe(v => $unitCounts = v);
  gameState.subscribe(v => $gameState = v);
  winRate.subscribe(v => $winRate = v);
  connected.subscribe(v => $connected = v);
  selectedMatchup.subscribe(v => $selectedMatchup = v);
  winHistory.subscribe(v => $winHistory = v);
</script>

<main>
  <h1>SC2 Zerg Bot Dashboard</h1>
  <div class="status">
    <span class:online={$connected} class:offline={!$connected}>
      {$connected ? 'CONNECTED' : 'DISCONNECTED'}
    </span>
    <span>Phase: {$gameState.phase} | Supply: {$gameState.supply} | Win Rate: {$winRate}%</span>
  </div>

  <div class="matchup-selector">
    {#each matchups as mu}
      <button class:active={$selectedMatchup === mu} on:click={() => selectedMatchup.set(mu)}>{mu}</button>
    {/each}
  </div>

  <div class="units">
    <h2>Live Unit Counts</h2>
    {#each Object.entries($unitCounts) as [unit, count]}
      <div class="unit-row"><span>{unit}</span><span>{count}</span></div>
    {/each}
  </div>

  <div class="chart-section">
    <h2>Win Rate — {$selectedMatchup} ({$winHistory.length} games)</h2>
    <canvas bind:this={chartCanvas}></canvas>
  </div>
</main>

<style>
  main { font-family: monospace; background: #0d0d1a; color: #c0c0ff; padding: 1rem; }
  h1 { color: #a855f7; }
  .status { display: flex; gap: 1rem; margin-bottom: 1rem; }
  .online { color: #22c55e; } .offline { color: #ef4444; }
  .matchup-selector button { margin: 0.25rem; padding: 0.4rem 1rem; background: #1e1e3a; color: #c0c0ff; border: 1px solid #4444aa; cursor: pointer; }
  .matchup-selector button.active { background: #a855f7; color: #fff; }
  .unit-row { display: flex; justify-content: space-between; padding: 0.2rem 0.5rem; border-bottom: 1px solid #1e1e3a; }
  .chart-section { margin-top: 1.5rem; }
</style>
