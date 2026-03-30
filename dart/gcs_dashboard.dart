// gcs_dashboard.dart
// Ground Control Station dashboard logic for a StarCraft II Zerg bot.
// Connects to the bot via WebSocket, parses live telemetry, and exposes
// a ViewModel that can be consumed by a Flutter UI widget tree.
//
// Usage:
//   final vm = DashboardViewModel();
//   await vm.connect('ws://localhost:8765');
//   // Bind vm.state to your StreamBuilder / ChangeNotifier

import 'dart:async';
import 'dart:convert';

// ─────────────────────────────────────────────────────────────────────────────
// Data Model
// ─────────────────────────────────────────────────────────────────────────────

/// Game phase labels that mirror the bot's internal phase enum.
enum GamePhase { early, mid, late, victory, defeat }

/// Snapshot of the bot's current in-game metrics.
class BotState {
  final int     minerals;
  final int     gas;
  final int     armySupply;
  final int     workerCount;
  final double  winRate;       // 0.0 – 1.0 from win_predictor
  final GamePhase phase;
  final int     baseCount;
  final double  timeMinutes;
  final String  lastAction;    // human-readable last decision

  const BotState({
    required this.minerals,
    required this.gas,
    required this.armySupply,
    required this.workerCount,
    required this.winRate,
    required this.phase,
    required this.baseCount,
    required this.timeMinutes,
    required this.lastAction,
  });

  /// Construct an idle / pre-game state.
  factory BotState.idle() => const BotState(
    minerals    : 50,
    gas         : 0,
    armySupply  : 0,
    workerCount : 12,
    winRate     : 0.5,
    phase       : GamePhase.early,
    baseCount   : 1,
    timeMinutes : 0.0,
    lastAction  : 'Waiting for game start',
  );

  /// Parse a JSON telemetry packet sent by the bot over WebSocket.
  factory BotState.fromJson(Map<String, dynamic> json) => BotState(
    minerals    : (json['minerals']     as num).toInt(),
    gas         : (json['gas']          as num).toInt(),
    armySupply  : (json['army_supply']  as num).toInt(),
    workerCount : (json['worker_count'] as num).toInt(),
    winRate     : (json['win_rate']     as num).toDouble(),
    phase       : GamePhase.values.firstWhere(
                    (e) => e.name == (json['phase'] as String),
                    orElse: () => GamePhase.early),
    baseCount   : (json['base_count']   as num).toInt(),
    timeMinutes : (json['time_minutes'] as num).toDouble(),
    lastAction  : json['last_action']   as String? ?? '',
  );

  /// Serialise to JSON for logging / replay.
  Map<String, dynamic> toJson() => {
    'minerals'    : minerals,
    'gas'         : gas,
    'army_supply' : armySupply,
    'worker_count': workerCount,
    'win_rate'    : winRate,
    'phase'       : phase.name,
    'base_count'  : baseCount,
    'time_minutes': timeMinutes,
    'last_action' : lastAction,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// ViewModel
// ─────────────────────────────────────────────────────────────────────────────

/// ViewModel that manages the WebSocket connection and exposes a stream of
/// [BotState] updates for the Flutter UI.
class DashboardViewModel {
  // Internal state
  BotState _current = BotState.idle();
  bool     _connected = false;

  // Public stream so Flutter widgets can listen for updates.
  final StreamController<BotState> _stateController =
      StreamController<BotState>.broadcast();

  Stream<BotState>  get stateStream  => _stateController.stream;
  BotState          get currentState => _current;
  bool              get isConnected  => _connected;

  /// Connect to the bot's WebSocket telemetry server.
  Future<void> connect(String wsUrl) async {
    // In a real Flutter app, use package:web_socket_channel.
    // Here we simulate the connection pattern for portability.
    print('[Dashboard] Connecting to $wsUrl …');
    _connected = true;
    print('[Dashboard] Connected.');

    // Simulate receiving periodic telemetry packets (replace with real WS).
    _simulateTelemetry();
  }

  /// Update the dashboard with a raw JSON telemetry packet from the bot.
  void update(Map<String, dynamic> json) {
    _current = BotState.fromJson(json);
    _stateController.add(_current);
  }

  /// Build a human-readable multi-line status string for overlays / logs.
  String formatStatus() {
    final s = _current;
    final pct = (s.winRate * 100).toStringAsFixed(1);
    return '''
┌─── SC2 Zerg Bot Dashboard ──────────────┐
│ Phase      : ${s.phase.name.padRight(28)}│
│ Time       : ${s.timeMinutes.toStringAsFixed(1).padRight(28)}min │
│ Minerals   : ${s.minerals.toString().padRight(28)}│
│ Gas        : ${s.gas.toString().padRight(28)}│
│ Workers    : ${s.workerCount.toString().padRight(28)}│
│ Army Supply: ${s.armySupply.toString().padRight(28)}│
│ Bases      : ${s.baseCount.toString().padRight(28)}│
│ Win Rate   : ${pct.padRight(27)}% │
│ Last Action: ${s.lastAction.padRight(28)}│
└─────────────────────────────────────────┘''';
  }

  /// Disconnect and clean up resources.
  void dispose() {
    _stateController.close();
    _connected = false;
    print('[Dashboard] Disconnected.');
  }

  // ── Simulation helpers (replace with real WebSocket in production) ─────────

  void _simulateTelemetry() {
    final packets = [
      {'minerals':300,'gas':100,'army_supply':20,'worker_count':22,
       'win_rate':0.52,'phase':'early','base_count':2,'time_minutes':6.5,
       'last_action':'Expanding to third base'},
      {'minerals':450,'gas':220,'army_supply':40,'worker_count':28,
       'win_rate':0.65,'phase':'mid','base_count':3,'time_minutes':11.2,
       'last_action':'Producing Roaches + Hydralisks'},
      {'minerals':200,'gas':80,'army_supply':60,'worker_count':30,
       'win_rate':0.78,'phase':'late','base_count':4,'time_minutes':17.4,
       'last_action':'Attack: 4th base push'},
    ];

    var i = 0;
    Timer.periodic(const Duration(seconds: 2), (timer) {
      if (i >= packets.length) { timer.cancel(); return; }
      update(packets[i++]);
      print(formatStatus());
    });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Entry point (standalone test — remove when embedding in Flutter app)
// ─────────────────────────────────────────────────────────────────────────────

void main() async {
  print('=== SC2 Zerg Bot GCS Dashboard (Dart) ===\n');
  final vm = DashboardViewModel();
  await vm.connect('ws://localhost:8765');
  // Keep process alive long enough to receive simulated packets.
  await Future.delayed(const Duration(seconds: 8));
  vm.dispose();
}
