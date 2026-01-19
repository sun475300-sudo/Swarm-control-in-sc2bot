#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test build order extraction with detailed debugging"""

import sc2reader

extractor = ReplayBuildOrderExtractor()
replay_files = extractor.scan_replays()

print(f"Found {len(replay_files)} replay files")
if replay_files:
    replay_path = replay_files[0]
    print(f"Testing first replay: {replay_path.name}")

 # First, check if Zerg player exists
 replay = sc2reader.load_replay(str(replay_path), load_map=True)
    zerg_players = [p for p in replay.players if hasattr(p, 'play_race') and str(p.play_race).lower() == 'zerg']
    print(f"  Zerg players found: {len(zerg_players)}")
 if zerg_players:
     zerg_pid = zerg_players[0].pid
     print(f"  Zerg player PID: {zerg_pid}")

 # Count UnitBornEvents for Zerg
 zerg_units = 0
 for event in replay.events:
     if hasattr(event, '__class__') and 'UnitBorn' in str(event.__class__):
             pass
     if hasattr(event, 'control_pid') and event.control_pid == zerg_pid:
         pass
     zerg_units += 1
 if zerg_units <= 5:
     unit_name = event.unit.name if hasattr(event, 'unit') and hasattr(event.unit, 'name') else 'Unknown'
     print(f"    Unit #{zerg_units}: {unit_name}")
     print(f"  Total Zerg UnitBornEvents: {zerg_units}")

 # Now try extraction
 build_order = extractor.extract_build_order(replay_path)

 if build_order:
     print(f"[OK] Build order extracted")
     print(f"  Player: {build_order.get('player_name', 'Unknown')}")
     print(f"  Timings: {len(build_order.get('timings', {}))}")
     for param, data in build_order.get('timings', {}).items():
         pass
     print(f"    {param}: supply={data.get('supply', 0)}, time={data.get('time', 0):.1f}s")
 else:
     print("[FAIL] Build order extraction returned None")
     print("  This means no timings were extracted from the replay")
