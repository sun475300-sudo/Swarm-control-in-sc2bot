// Phase 580: SolidJS App
// SC2 Bot Control Panel — SolidJS TSX Component
// Fine-grained reactive SC2 bot dashboard using SolidJS primitives.
// Standalone-runnable: mount <BotControl /> as the root in a SolidJS project.

import {
  createSignal,
  createEffect,
  createMemo,
  For,
  Show,
  onMount,
  onCleanup,
  type Component,
  type Accessor,
} from 'solid-js';

// ─────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────

type Race          = 'Zerg' | 'Terran' | 'Protoss';
type GamePhase     = 'early' | 'mid' | 'late';
type ThreatLevel   = 'none' | 'low' | 'moderate' | 'critical';
type ActionSeverity = 'info' | 'success' | 'warning' | 'danger';
type BotMode       = 'aggressive' | 'defensive' | 'economic' | 'harassment';

interface ActionEntry {
  id:       number;
  time:     string;
  text:     string;
  severity: ActionSeverity;
}

interface EconomySnapshot {
  tick:     number;
  minerals: number;
  gas:      number;
}

interface Decision {
  action:   string;
  priority: 'high' | 'medium' | 'low';
  reason:   string;
}

// ─────────────────────────────────────────────────────────────────
// Utility helpers
// ─────────────────────────────────────────────────────────────────

let _actionCounter = 0;
const nextId = () => ++_actionCounter;

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

function rng(lo: number, hi: number): number {
  return lo + Math.random() * (hi - lo);
}

function timestamp(): string {
  return new Date().toLocaleTimeString('en-US', { hour12: false });
}

function formatSeconds(s: number): string {
  const m = Math.floor(s / 60).toString().padStart(2, '0');
  const sec = (s % 60).toString().padStart(2, '0');
  return `${m}:${sec}`;
}

// ─────────────────────────────────────────────────────────────────
// CSS-in-JS style objects
// ─────────────────────────────────────────────────────────────────

const S = {
  root: {
    background:  '#080e08',
    color:       '#b8ffb8',
    fontFamily:  "'Consolas', 'Courier New', monospace",
    minHeight:   '100vh',
    padding:     '0',
  } as const,

  header: {
    display:        'flex',
    justifyContent: 'space-between',
    alignItems:     'center',
    padding:        '0.6rem 1.5rem',
    background:     '#0b160b',
    borderBottom:   '1px solid #1a3a1a',
    flexWrap:       'wrap' as const,
    gap:            '0.5rem',
  } as const,

  logo: {
    fontSize:    '1.15rem',
    fontWeight:  'bold',
    color:       '#00ff88',
    letterSpacing: '2px',
  } as const,

  grid: {
    display:             'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap:                 '1rem',
    padding:             '1rem 1.5rem',
  } as const,

  panel: {
    background:   '#0c140c',
    border:       '1px solid #1a3a1a',
    borderRadius: '8px',
    padding:      '1rem 1.25rem',
  } as const,

  panelTitle: {
    fontSize:      '0.7rem',
    color:         '#4a7a4a',
    textTransform: 'uppercase' as const,
    letterSpacing: '2px',
    marginBottom:  '0.75rem',
    borderBottom:  '1px solid #1a3a1a',
    paddingBottom: '0.35rem',
  } as const,

  bigValue: (color = '#00ff88') => ({
    fontSize:   '2.8rem',
    fontWeight: 'bold',
    color,
    lineHeight: '1',
  } as const),

  label: {
    fontSize: '0.7rem',
    color:    '#557755',
  } as const,

  bar: (pct: number, color: string) => ({
    height:       '8px',
    borderRadius: '4px',
    background:   '#0a150a',
    border:       '1px solid #1a3a1a',
    overflow:     'hidden',
    position:     'relative' as const,
  } as const),

  barFill: (pct: number, color: string) => ({
    height:           '100%',
    width:            `${clamp(pct, 0, 100)}%`,
    background:       color,
    borderRadius:     '4px',
    transition:       'width 0.35s ease, background 0.3s',
  } as const),

  button: (variant: 'primary' | 'danger' | 'default' = 'default') => ({
    background:   variant === 'primary' ? '#003a18' : variant === 'danger' ? '#2a0008' : '#131a13',
    border:       `1px solid ${variant === 'primary' ? '#00aa44' : variant === 'danger' ? '#aa0022' : '#2a3a2a'}`,
    color:        variant === 'primary' ? '#00ff88' : variant === 'danger' ? '#ff4466' : '#88aa88',
    padding:      '4px 12px',
    borderRadius: '4px',
    cursor:       'pointer',
    fontSize:     '0.78rem',
    fontFamily:   'inherit',
  } as const),

  tag: (color: string, bg: string) => ({
    display:      'inline-block',
    padding:      '2px 8px',
    borderRadius: '4px',
    fontSize:     '0.72rem',
    color,
    background:   bg,
    border:       `1px solid ${color}44`,
  } as const),
};

// ─────────────────────────────────────────────────────────────────
// Sub-components (fine-grained: each reads only its own signals)
// ─────────────────────────────────────────────────────────────────

/** ResourcePanel — shows minerals, gas, economy rate */
const ResourcePanel: Component<{
  minerals: Accessor<number>;
  gas:      Accessor<number>;
  ecoRate:  Accessor<number>;
}> = (props) => (
  <div style={S.panel}>
    <div style={S.panelTitle}>Economy</div>
    <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '0.75rem' }}>
      <div>
        <div style={{ ...S.bigValue('#44aaff'), fontSize: '1.8rem' }}>
          {Math.round(props.minerals()).toLocaleString()}
        </div>
        <div style={S.label}>◆ Minerals</div>
      </div>
      <div>
        <div style={{ ...S.bigValue('#44ffaa'), fontSize: '1.8rem' }}>
          {Math.round(props.gas()).toLocaleString()}
        </div>
        <div style={S.label}>⬡ Vespene</div>
      </div>
      <div>
        <div style={{ ...S.bigValue('#ffdd44'), fontSize: '1.8rem' }}>
          {Math.round(props.ecoRate())}
        </div>
        <div style={S.label}>★ Eco Rate</div>
      </div>
    </div>
    {/* Minerals bar */}
    <div style={{ marginBottom: '4px', ...S.bar(0, '') }}>
      <div style={S.barFill((props.minerals() / 9999) * 100, '#44aaff')} />
    </div>
    {/* Gas bar */}
    <div style={S.bar(0, '')}>
      <div style={S.barFill((props.gas() / 9999) * 100, '#44ffaa')} />
    </div>
  </div>
);

/** ThreatIndicator — circular threat gauge */
const ThreatIndicator: Component<{
  threat:      Accessor<number>;
  threatLabel: Accessor<ThreatLevel>;
}> = (props) => {
  const color = createMemo(() => {
    const t = props.threat();
    return t > 70 ? '#ff2244' : t > 40 ? '#ffaa00' : '#00ff88';
  });

  const circumference = 2 * Math.PI * 38;
  const dashLen = createMemo(() =>
    ((props.threat() / 100) * circumference).toFixed(1)
  );

  return (
    <div style={S.panel}>
      <div style={S.panelTitle}>Threat Level</div>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <svg viewBox="0 0 100 100" style={{ width: '100px', height: '100px' }}>
          <circle cx="50" cy="50" r="38" fill="none" stroke="#111a11" stroke-width="9" />
          <circle
            cx="50" cy="50" r="38"
            fill="none"
            stroke={color()}
            stroke-width="9"
            stroke-dasharray={`${dashLen()} ${circumference}`}
            stroke-dashoffset={circumference * 0.25}
            stroke-linecap="round"
            style="transition: stroke-dasharray 0.4s ease, stroke 0.4s;"
          />
          <text
            x="50" y="56"
            text-anchor="middle"
            style={{ fontFamily: 'inherit', fontSize: '20px', fontWeight: 'bold', fill: color() }}
          >
            {Math.round(props.threat())}
          </text>
        </svg>
      </div>
      <div style={{
        textAlign:     'center',
        color:         color(),
        fontSize:      '0.8rem',
        fontWeight:    'bold',
        letterSpacing: '2px',
        marginTop:     '0.3rem',
        textTransform: 'uppercase',
      }}>
        {props.threatLabel()}
      </div>
    </div>
  );
};

/** ActionHistory — scrollable log of bot decisions */
const ActionHistory: Component<{
  log: Accessor<ActionEntry[]>;
}> = (props) => {
  const severityColors: Record<ActionSeverity, string> = {
    info:    '#88aacc',
    success: '#44ff88',
    warning: '#ffaa44',
    danger:  '#ff4455',
  };

  return (
    <div style={{ ...S.panel, gridColumn: 'span 2' }}>
      <div style={S.panelTitle}>Action Log</div>
      <div style={{
        maxHeight:   '200px',
        overflowY:   'auto',
        fontSize:    '0.78rem',
      }}>
        <For each={props.log()} fallback={
          <div style={{ color: '#335533', padding: '0.5rem 0' }}>
            Waiting for bot activity…
          </div>
        }>
          {(entry) => (
            <div style={{
              display:       'flex',
              gap:           '0.75rem',
              padding:       '3px 0',
              borderBottom:  '1px solid #0d180d',
              alignItems:    'baseline',
            }}>
              <span style={{ color: '#335533', flexShrink: '0', fontSize: '0.68rem' }}>
                {entry.time}
              </span>
              <span style={{ color: severityColors[entry.severity] }}>
                {entry.text}
              </span>
            </div>
          )}
        </For>
      </div>
    </div>
  );
};

/** DecisionEngine — derived state panel showing bot's next intended actions */
const DecisionEngine: Component<{
  decisions: Accessor<Decision[]>;
  mode:      Accessor<BotMode>;
}> = (props) => {
  const priorityColor = (p: Decision['priority']) =>
    p === 'high' ? '#ff4466' : p === 'medium' ? '#ffaa44' : '#44aa88';

  return (
    <div style={S.panel}>
      <div style={S.panelTitle}>Decision Engine</div>
      <div style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={S.label}>Mode:</span>
        <span style={S.tag('#00ff88', '#003318')}>{props.mode().toUpperCase()}</span>
      </div>
      <For each={props.decisions()}>
        {(d) => (
          <div style={{
            padding:      '4px 0',
            borderBottom: '1px solid #0d180d',
            fontSize:     '0.78rem',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#aaccaa', fontWeight: 'bold' }}>{d.action}</span>
              <span style={{
                ...S.tag(priorityColor(d.priority), `${priorityColor(d.priority)}11`),
                fontSize: '0.65rem',
              }}>
                {d.priority.toUpperCase()}
              </span>
            </div>
            <div style={{ color: '#557755', fontSize: '0.68rem', marginTop: '1px' }}>
              {d.reason}
            </div>
          </div>
        )}
      </For>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────
// Root BotControl component
// ─────────────────────────────────────────────────────────────────

const BotControl: Component = () => {

  // ── Core signals ──────────────────────────────────────────────
  const [gameRunning, setGameRunning] = createSignal(false);
  const [gameTime,    setGameTime]    = createSignal(0);
  const [minerals,    setMinerals]    = createSignal(50);
  const [gas,         setGas]         = createSignal(0);
  const [supply,      setSupply]      = createSignal(12);
  const [supplyMax,   setSupplyMax]   = createSignal(15);
  const [army,        setArmy]        = createSignal(0);
  const [workers,     setWorkers]     = createSignal(12);
  const [threat,      setThreat]      = createSignal(0);
  const [apm,         setApm]         = createSignal(0);
  const [winRate,     setWinRate]     = createSignal(0.0);
  const [wins,        setWins]        = createSignal(0);
  const [totalGames,  setTotalGames]  = createSignal(0);
  const [botMode,     setBotMode]     = createSignal<BotMode>('economic');
  const [race,        ]               = createSignal<Race>('Zerg');
  const [oppRace,     setOppRace]     = createSignal<Race>('Terran');
  const [mapName,     setMapName]     = createSignal('Blackburn LE');
  const [actionLog,   setActionLog]   = createSignal<ActionEntry[]>([]);
  const [ecoHistory,  setEcoHistory]  = createSignal<EconomySnapshot[]>([]);

  // ── Derived / memo state ──────────────────────────────────────
  const supplyPct    = createMemo(() => (supply()  / supplyMax()) * 100);
  const supplyBlocked = createMemo(() => supply() >= supplyMax());
  const ecoRate      = createMemo(() => minerals() + gas() * 1.5);
  const armyPct      = createMemo(() => Math.min(100, (army() / 200) * 100));
  const gamePhase    = createMemo((): GamePhase => {
    const t = gameTime();
    return t < 300 ? 'early' : t < 900 ? 'mid' : 'late';
  });
  const threatLabel  = createMemo((): ThreatLevel => {
    const t = threat();
    return t > 70 ? 'critical' : t > 40 ? 'moderate' : t > 15 ? 'low' : 'none';
  });
  const winRatePct   = createMemo(() => (winRate() * 100).toFixed(1));

  /** Decision engine: derived from reactive signals — only re-runs when inputs change */
  const decisions = createMemo((): Decision[] => {
    const m = minerals();
    const g = gas();
    const a = army();
    const th = threat();
    const s = supply();
    const sMax = supplyMax();
    const phase = gamePhase();
    const mode = botMode();

    const out: Decision[] = [];

    if (s >= sMax - 2) {
      out.push({
        action:   'Build Overlord',
        priority: 'high',
        reason:   `Supply ${s}/${sMax} — blocked or near-blocked`,
      });
    }

    if (m >= 300 && workers() < 70 && phase !== 'late') {
      out.push({
        action:   'Produce Drone',
        priority: 'medium',
        reason:   `Only ${workers()} workers — economy below target`,
      });
    }

    if (m >= 400 && phase !== 'early' && ecoHistory().length > 5) {
      out.push({
        action:   'Expand to next base',
        priority: 'medium',
        reason:   `Minerals saturating at ${Math.round(m)} — expand for income`,
      });
    }

    if (th > 50 || mode === 'defensive') {
      out.push({
        action:   'Rally army to defend',
        priority: th > 70 ? 'high' : 'medium',
        reason:   `Threat level ${Math.round(th)} — pull units back`,
      });
    }

    if (mode === 'aggressive' && a >= 80 && phase === 'mid') {
      out.push({
        action:   'Attack enemy natural',
        priority: 'high',
        reason:   `Army supply ${a} sufficient for aggressive push`,
      });
    }

    if (m >= 200 && g >= 100 && a < 60) {
      out.push({
        action:   'Produce Roaches / Hydralisks',
        priority: 'medium',
        reason:   `Resources available (${Math.round(m)}m/${Math.round(g)}g) — build army`,
      });
    }

    if (g < 50 && phase !== 'early') {
      out.push({
        action:   'Assign drones to gas',
        priority: 'low',
        reason:   `Gas income low (${Math.round(g)}) — tech upgrades blocked`,
      });
    }

    return out.length > 0
      ? out
      : [{ action: 'Hold position', priority: 'low', reason: 'No urgent actions required' }];
  });

  // ── Effects ───────────────────────────────────────────────────

  /** Auto-switch bot mode based on game phase and threat */
  createEffect(() => {
    const phase = gamePhase();
    const th    = threat();
    if (th > 65) {
      setBotMode('defensive');
    } else if (phase === 'early') {
      setBotMode('economic');
    } else if (phase === 'mid' && army() > 80) {
      setBotMode('aggressive');
    } else if (phase === 'late') {
      setBotMode('harassment');
    }
  });

  /** Log supply-blocked state transitions */
  createEffect(() => {
    if (supplyBlocked() && gameRunning()) {
      addLog('⚠ Supply blocked!', 'warning');
    }
  });

  /** Log critical threat */
  createEffect(() => {
    if (threatLabel() === 'critical' && gameRunning()) {
      addLog('CRITICAL: Enemy attacking!', 'danger');
    }
  });

  // ── Helpers ───────────────────────────────────────────────────
  function addLog(text: string, severity: ActionSeverity = 'info') {
    setActionLog(prev =>
      [{ id: nextId(), time: timestamp(), text, severity }, ...prev].slice(0, 25)
    );
  }

  // ── Simulation intervals ──────────────────────────────────────
  let gameTimerHandle: ReturnType<typeof setInterval> | null = null;
  let stateHandle:     ReturnType<typeof setInterval> | null = null;
  let endCheckHandle:  ReturnType<typeof setInterval> | null = null;

  function clearAllIntervals() {
    if (gameTimerHandle) clearInterval(gameTimerHandle);
    if (stateHandle)     clearInterval(stateHandle);
    if (endCheckHandle)  clearInterval(endCheckHandle);
    gameTimerHandle = stateHandle = endCheckHandle = null;
  }

  function startGame() {
    const maps  = ['Blackburn LE', 'Submarine LE', 'Crimson Court', 'Ancient Cistern LE', 'Goldenaura LE'];
    const races = ['Terran', 'Zerg', 'Protoss'] as Race[];
    setMapName(maps[Math.floor(Math.random() * maps.length)]);
    setOppRace(races[Math.floor(Math.random() * races.length)]);
    setGameTime(0);
    setMinerals(50); setGas(0);
    setSupply(12);   setSupplyMax(15);
    setArmy(0);      setWorkers(12);
    setThreat(0);    setApm(0);
    setEcoHistory([]);
    setGameRunning(true);

    addLog(`Game started on ${mapName()} vs ${oppRace()}`, 'info');

    // Game clock
    gameTimerHandle = setInterval(() => setGameTime(t => t + 1), 1000);

    // State updates (500ms)
    stateHandle = setInterval(() => {
      const t = gameTime();

      // Economy
      setMinerals(m => clamp(m + rng(40, 110) - rng(0, 70), 0, 9999));
      setGas(g      => clamp(g + rng(0, 55) - rng(0, 35), 0, 9999));

      // Supply
      if (supply() < supplyMax() - 2 && Math.random() < 0.25)
        setSupply(s => clamp(s + Math.ceil(rng(1, 4)), 0, supplyMax()));
      if (supplyMax() < 200 && Math.random() < 0.12)
        setSupplyMax(sm => Math.min(200, sm + 8));

      // Army / workers
      if (supply() > 14 && Math.random() < 0.2)
        setArmy(a => clamp(a + Math.ceil(rng(0, 6)), 0, 200));
      if (workers() < 80 && Math.random() < 0.15)
        setWorkers(w => w + 1);

      // APM
      const target = t < 120 ? rng(80, 140) : t < 600 ? rng(150, 280) : rng(120, 220);
      setApm(Math.round(target + rng(-10, 10)));

      // Threat
      const delta = rng(-6, 10) * (Math.random() < 0.15 ? 2 : 1);
      setThreat(th => clamp(th + delta, 0, 100));

      // Economy history snapshot
      setEcoHistory(prev =>
        [...prev, { tick: t, minerals: Math.round(minerals()), gas: Math.round(gas()) }].slice(-60)
      );

      // Random action log entries
      if (Math.random() < 0.10) {
        const picks: [string, ActionSeverity][] = [
          ['Spawning Pool complete',        'success'],
          ['Scout drone en route',          'info'],
          ['Hatchery construction started', 'info'],
          ['Zergling speed research begun', 'info'],
          ['Expanding to third base',       'success'],
          ['Enemy army detected near ramp', 'warning'],
          ['Roach Warren complete',         'success'],
          ['Retreating injured units',      'warning'],
          ['Baneling nest started',         'info'],
          ['Lair upgrade in progress',      'info'],
          ['Inject larvae cycle complete',  'success'],
        ];
        const [text, sev] = picks[Math.floor(Math.random() * picks.length)];
        addLog(text, sev);
      }
    }, 500);

    // Game end check (every 2s)
    endCheckHandle = setInterval(() => {
      if (gameTime() > rng(120, 480) && Math.random() < 0.015) {
        endGame(Math.random() < (winRate() > 0 ? winRate() + 0.05 : 0.50));
      }
    }, 2000);
  }

  function endGame(won: boolean) {
    clearAllIntervals();
    setGameRunning(false);
    setTotalGames(n => n + 1);
    if (won) setWins(w => w + 1);
    setWinRate(wins() / (totalGames() + (won ? 0 : 0)));
    // Recompute after state updates settle
    setTimeout(() => setWinRate(wins() / totalGames()), 10);

    addLog(
      won ? `VICTORY on ${mapName()}! (${formatSeconds(gameTime())})` :
            `DEFEAT on ${mapName()}. Reviewing…`,
      won ? 'success' : 'danger'
    );

    // Auto-restart after 3 seconds
    setTimeout(() => startGame(), 3000);
  }

  function handleModeChange(mode: BotMode) {
    setBotMode(mode);
    addLog(`Bot mode set to: ${mode.toUpperCase()}`, 'info');
  }

  // ── Mount / Cleanup ───────────────────────────────────────────
  onMount(() => {
    addLog('SC2 Bot Control Panel online', 'success');
    startGame();
  });

  onCleanup(() => {
    clearAllIntervals();
  });

  // ── Render ─────────────────────────────────────────────────────
  return (
    <div style={S.root}>

      {/* Header */}
      <header style={S.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={S.logo}>⬡ SC2 BOT CONTROL</span>
          <span style={S.tag('#00ff88', '#003318')}>{race()}</span>
          <span style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: gameRunning() ? '#00ff88' : '#ff4444',
            boxShadow: gameRunning() ? '0 0 6px #00ff88' : 'none',
            display: 'inline-block',
            transition: 'background 0.4s',
          }} />
          <span style={{ fontSize: '0.72rem', color: '#557755' }}>
            {gameRunning() ? 'LIVE' : 'STANDBY'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ color: '#88aa88', fontSize: '0.85rem' }}>{mapName()}</span>
          <span style={{ color: '#557755', fontSize: '0.8rem' }}>vs {oppRace()}</span>
          <span style={{
            fontWeight: 'bold', fontSize: '1.05rem', color: '#44ffaa',
            letterSpacing: '1px', fontFamily: 'inherit',
          }}>
            {formatSeconds(gameTime())}
          </span>
          <span style={S.tag(
            gamePhase() === 'early' ? '#44aaff' : gamePhase() === 'mid' ? '#ffaa44' : '#ff4466',
            '#0a0a1a',
          )}>
            {gamePhase().toUpperCase()} GAME
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' as const }}>
          <span style={{ fontSize: '0.72rem', color: '#557755' }}>W/R:</span>
          <span style={{ color: winRate() >= 0.55 ? '#00ff88' : winRate() >= 0.40 ? '#ffaa44' : '#ff4466', fontWeight: 'bold' }}>
            {winRatePct()}%
          </span>
          <span style={{ fontSize: '0.7rem', color: '#445544' }}>
            ({wins()}W / {totalGames() - wins()}L)
          </span>
        </div>
      </header>

      {/* Main grid */}
      <div style={S.grid}>

        {/* Resource Panel — only re-renders when minerals/gas/ecoRate change */}
        <ResourcePanel
          minerals={minerals}
          gas={gas}
          ecoRate={ecoRate}
        />

        {/* Army Supply */}
        <div style={S.panel}>
          <div style={S.panelTitle}>Army Supply</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem', marginBottom: '0.6rem' }}>
            <span style={{
              ...S.bigValue(supplyBlocked() ? '#ff2244' : '#00ff88'),
              transition: 'color 0.3s',
            }}>
              {supply()}
            </span>
            <span style={{ color: '#446644', fontSize: '1.2rem' }}>/</span>
            <span style={{ ...S.bigValue('#88aa88'), fontSize: '1.8rem' }}>{supplyMax()}</span>
          </div>
          <div style={{ ...S.bar(supplyPct(), ''), marginBottom: '4px' }}>
            <div style={S.barFill(supplyPct(), supplyBlocked() ? '#ff2244' : '#00ff88')} />
          </div>
          <Show when={supplyBlocked()}>
            <div style={{
              textAlign: 'center', color: '#ff2244', fontWeight: 'bold',
              fontSize: '0.8rem', marginTop: '0.4rem',
              animation: 'sc2blink 0.8s step-start infinite',
            }}>
              ⚠ SUPPLY BLOCKED
            </div>
          </Show>
          <div style={{ marginTop: '0.75rem' }}>
            <div style={{ ...S.panelTitle, marginBottom: '0.5rem' }}>Army Units</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem', marginBottom: '0.4rem' }}>
              <span style={S.bigValue('#ff8844')}>{army()}</span>
              <span style={S.label}>/ 200 army supply</span>
            </div>
            <div style={S.bar(armyPct(), '')}>
              <div style={S.barFill(armyPct(), 'linear-gradient(to right, #ff4400, #ff8844)')} />
            </div>
          </div>
        </div>

        {/* APM + Win Rate */}
        <div style={S.panel}>
          <div style={S.panelTitle}>Performance</div>
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ ...S.bigValue(apm() > 200 ? '#00ff88' : apm() > 100 ? '#44aaff' : '#888'), transition: 'color 0.3s' }}>
              {apm()}
            </div>
            <div style={S.label}>ACTIONS PER MINUTE</div>
            <div style={{ ...S.bar(0, ''), marginTop: '0.4rem' }}>
              <div style={S.barFill((apm() / 400) * 100, 'linear-gradient(to right, #1144ff, #44aaff, #00ff88)')} />
            </div>
          </div>
          <div>
            <div style={S.label}>WIN RATE</div>
            <div style={{
              fontSize: '2rem', fontWeight: 'bold',
              color: winRate() >= 0.55 ? '#00ff88' : winRate() >= 0.40 ? '#ffaa44' : '#ff4466',
              transition: 'color 0.4s',
            }}>
              {winRatePct()}%
            </div>
            <div style={{ ...S.bar(0, ''), marginTop: '0.4rem' }}>
              <div style={S.barFill(winRate() * 100, winRate() >= 0.55 ? '#00ff88' : '#ffaa44')} />
            </div>
          </div>
        </div>

        {/* Threat Indicator — isolated component, only re-renders on threat change */}
        <ThreatIndicator
          threat={threat}
          threatLabel={threatLabel}
        />

        {/* Bot Mode Controls */}
        <div style={S.panel}>
          <div style={S.panelTitle}>Bot Mode</div>
          <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: '0.5rem', marginBottom: '0.75rem' }}>
            <For each={['economic', 'aggressive', 'defensive', 'harassment'] as BotMode[]}>
              {(mode) => (
                <button
                  style={{
                    ...S.button(botMode() === mode ? 'primary' : 'default'),
                    background: botMode() === mode ? '#003a18' : '#131a13',
                    borderColor: botMode() === mode ? '#00aa44' : '#2a3a2a',
                    color:       botMode() === mode ? '#00ff88' : '#88aa88',
                  }}
                  onClick={() => handleModeChange(mode)}
                >
                  {mode.toUpperCase()}
                </button>
              )}
            </For>
          </div>
          <div style={S.label}>Workers</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#ddaa44' }}>
            {workers()}
          </div>
          <div style={{ ...S.bar(0, ''), marginTop: '4px' }}>
            <div style={S.barFill((workers() / 90) * 100, '#ddaa44')} />
          </div>
        </div>

        {/* Decision Engine — derived memo, only updates when relevant signals change */}
        <DecisionEngine decisions={decisions} mode={botMode} />

        {/* Action History — spans 2 cols */}
        <ActionHistory log={actionLog} />

      </div>
    </div>
  );
};

export default BotControl;

// ─────────────────────────────────────────────────────────────────
// Entry point (for direct mounting)
// ─────────────────────────────────────────────────────────────────

/*
  To run standalone in a SolidJS project:

  // src/index.tsx
  import { render } from 'solid-js/web';
  import BotControl from './BotControl';

  const root = document.getElementById('root');
  render(() => <BotControl />, root!);

  // index.html — add blink keyframe animation:
  // <style>
  //   @keyframes sc2blink { 50% { opacity: 0; } }
  // </style>
*/
