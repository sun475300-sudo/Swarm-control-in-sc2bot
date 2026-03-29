import 'package:flutter/material.dart';
import 'dart:async';

class BattleWidget extends StatefulWidget {
  final List<UnitData> units;
  final Function(UnitData)? onUnitTap;
  final Function(Offset)? onMapTap;

  const BattleWidget({
    super.key,
    required this.units,
    this.onUnitTap,
    this.onMapTap,
  });

  @override
  State<BattleWidget> createState() => _BattleWidgetState();
}

class _BattleWidgetState extends State<BattleWidget> {
  Offset _offset = Offset.zero;
  double _scale = 1.0;
  Offset? _lastFocalPoint;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onScaleStart: (details) {
        _lastFocalPoint = details.focalPoint;
      },
      onScaleUpdate: (details) {
        setState(() {
          _scale = (_scale * details.scale).clamp(0.5, 3.0);
          if (details.scale != 1.0) {
            _offset = Offset(
              _offset.dx + details.focalPoint.dx - (_lastFocalPoint?.dx ?? 0),
              _offset.dy + details.focalPoint.dy - (_lastFocalPoint?.dy ?? 0),
            );
            _lastFocalPoint = details.focalPoint;
          }
        });
      },
      onTapUp: (details) {
        final mapPosition = screenToMap(details.localPosition);
        widget.onMapTap?.call(mapPosition);
      },
      child: CustomPaint(
        painter: BattleFieldPainter(
          units: widget.units,
          offset: _offset,
          scale: _scale,
        ),
        size: Size.infinite,
      ),
    );
  }

  Offset screenToMap(Offset screenPos) {
    return Offset(
      (screenPos.dx - _offset.dx) / _scale,
      (screenPos.dy - _offset.dy) / _scale,
    );
  }
}

class UnitData {
  final int id;
  final String type;
  final double x;
  final double y;
  final double health;
  final double maxHealth;
  final bool isEnemy;

  const UnitData({
    required this.id,
    required this.type,
    required this.x,
    required this.y,
    required this.health,
    required this.maxHealth,
    required this.isEnemy,
  });
}

class BattleFieldPainter extends CustomPainter {
  final List<UnitData> units;
  final Offset offset;
  final double scale;

  BattleFieldPainter({
    required this.units,
    required this.offset,
    required this.scale,
  });

  @override
  void paint(Canvas canvas, Size size) {
    _drawGrid(canvas, size);
    _drawUnits(canvas);
  }

  void _drawGrid(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = Colors.green.withValues(alpha: 0.3)
      ..strokeWidth = 1.0;

    final gridSize = 32.0 * scale;
    var x = offset.dx % gridSize;
    while (x < size.width) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
      x += gridSize;
    }

    var y = offset.dy % gridSize;
    while (y < size.height) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
      y += gridSize;
    }
  }

  void _drawUnits(Canvas canvas) {
    for (final unit in units) {
      final pos = Offset(
        unit.x * scale + offset.dx,
        unit.y * scale + offset.dy,
      );

      final color = _getUnitColor(unit.type, unit.isEnemy);
      final radius = _getUnitRadius(unit.type) * scale;

      final unitPaint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;
      canvas.drawCircle(pos, radius, unitPaint);

      _drawHealthBar(canvas, pos, unit.health, unit.maxHealth, radius);
    }
  }

  Color _getUnitColor(String type, bool isEnemy) {
    if (isEnemy) return Colors.red;
    switch (type) {
      case 'DRONE': return Colors.amber;
      case 'ZERGLING': return Colors.orange;
      case 'ROACH': return Colors.brown;
      case 'HYDRALISK': return Colors.blue;
      case 'MUTALISK': return Colors.purple;
      case 'ULTRALISK': return Colors.grey;
      default: return Colors.white;
    }
  }

  double _getUnitRadius(String type) {
    switch (type) {
      case 'DRONE':
      case 'ZERGLING': return 6.0;
      case 'ROACH':
      case 'HYDRALISK': return 8.0;
      case 'MUTALISK': return 7.0;
      case 'ULTRALISK': return 12.0;
      default: return 8.0;
    }
  }

  void _drawHealthBar(Canvas canvas, Offset pos, double health, double maxHealth, double radius) {
    final barWidth = radius * 2;
    final barHeight = 4.0;
    final barY = pos.dy - radius - 8.0;

    final bgPaint = Paint()
      ..color = Colors.black54
      ..style = PaintingStyle.fill;
    canvas.drawRect(
      Rect.fromLTWH(pos.dx - barWidth / 2, barY, barWidth, barHeight),
      bgPaint,
    );

    final healthPercent = health / maxHealth;
    final healthColor = healthPercent > 0.6
        ? Colors.green
        : healthPercent > 0.3 ? Colors.yellow : Colors.red;

    final healthPaint = Paint()
      ..color = healthColor
      ..style = PaintingStyle.fill;
    canvas.drawRect(
      Rect.fromLTWH(
        pos.dx - barWidth / 2,
        barY,
        barWidth * healthPercent,
        barHeight,
      ),
      healthPaint,
    );
  }

  @override
  bool shouldRepaint(covariant BattleFieldPainter oldDelegate) {
    return units != oldDelegate.units ||
        offset != oldDelegate.offset ||
        scale != oldDelegate.scale;
  }
}

class DashboardApp extends StatelessWidget {
  const DashboardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SC2 Battle Dashboard',
      theme: ThemeData.dark(),
      home: const DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final List<UnitData> _units = [];
  Timer? _updateTimer;

  @override
  void initState() {
    super.initState();
    _generateSampleUnits();
    _updateTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _updateUnitPositions();
    });
  }

  void _generateSampleUnits() {
    _units.addAll([
      const UnitData(id: 1, type: 'DRONE', x: 30, y: 40, health: 40, maxHealth: 40, isEnemy: false),
      const UnitData(id: 2, type: 'DRONE', x: 35, y: 42, health: 40, maxHealth: 40, isEnemy: false),
      const UnitData(id: 3, type: 'ZERGLING', x: 50, y: 50, health: 35, maxHealth: 35, isEnemy: false),
      const UnitData(id: 4, type: 'ZERGLING', x: 52, y: 48, health: 35, maxHealth: 35, isEnemy: false),
      const UnitData(id: 5, type: 'ROACH', x: 45, y: 55, health: 90, maxHealth: 90, isEnemy: false),
      const UnitData(id: 10, type: 'ENEMY_MARINE', x: 80, y: 60, health: 45, maxHealth: 45, isEnemy: true),
      const UnitData(id: 11, type: 'ENEMY_MARINE', x: 82, y: 58, health: 45, maxHealth: 45, isEnemy: true),
      const UnitData(id: 12, type: 'ENEMY_TANK', x: 85, y: 55, health: 150, maxHealth: 150, isEnemy: true),
    ]);
  }

  void _updateUnitPositions() {
    setState(() {
      for (var i = 0; i < _units.length; i++) {
        final unit = _units[i];
        final dx = (i.isEven ? 0.5 : -0.5);
        final dy = (i % 3 == 0 ? 0.5 : -0.3);
        _units[i] = UnitData(
          id: unit.id,
          type: unit.type,
          x: (unit.x + dx).clamp(0, 200),
          y: (unit.y + dy).clamp(0, 150),
          health: unit.health,
          maxHealth: unit.maxHealth,
          isEnemy: unit.isEnemy,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('🐜 Wicked Zerg Battle Control'),
        backgroundColor: Colors.black87,
      ),
      body: Column(
        children: [
          Expanded(
            flex: 3,
            child: BattleWidget(
              units: _units,
              onUnitTap: (unit) {
                debugPrint('Tapped: ${unit.type}');
              },
              onMapTap: (pos) {
                debugPrint('Map tap: $pos');
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.black87,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStatCard('Units', '${_units.where((u) => !u.isEnemy).length}', Colors.green),
                _buildStatCard('Enemies', '${_units.where((u) => u.isEnemy).length}', Colors.red),
                _buildStatCard('APM', '147', Colors.blue),
                _buildStatCard('Supply', '42/200', Colors.purple),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String label, String value, Color color) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: Colors.white70)),
        const SizedBox(height: 4),
        Text(value, style: TextStyle(color: color, fontSize: 24, fontWeight: FontWeight.bold)),
      ],
    );
  }

  @override
  void dispose() {
    _updateTimer?.cancel();
    super.dispose();
  }
}

void main() {
  runApp(const DashboardApp());
}
