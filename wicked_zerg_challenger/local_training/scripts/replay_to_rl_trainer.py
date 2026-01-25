# -*- coding: utf-8 -*-
"""
Replay to RL Trainer
리플레이 데이터를 RLAgent 학습용 데이터(State, Action, Reward)로 변환하고 학습시킵니다.
"""

import sc2reader
# from sc2reader.events.game import UnitBornEvent, UnitInitEvent, UnitDiedEvent, PlayerStatsEvent
import numpy as np
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

from local_training.rl_agent import RLAgent

class ReplayStateTracker:
    def __init__(self, player_id):
        self.player_id = player_id
        self.minerals = 50
        self.gas = 0
        self.supply_used = 12
        self.supply_cap = 14
        self.units = {} # unit_id -> unit_type
        self.townhalls = 1
        self.workers = 12
        self.army_count = 0
        self.army_hp = 0
        self.enemy_units = 0
        self.enemy_army_hp = 0
        self.enemy_bases = 1
        self.upgrades = set()
        self.larva_count = 3
        
    def update(self, event):
        event_type = type(event).__name__
        
        # Unit Born/Init
        if 'UnitBornEvent' in event_type or 'UnitInitEvent' in event_type:
            if hasattr(event, 'control_pid') and event.control_pid == self.player_id:
                if hasattr(event, 'unit'):
                    u_name = event.unit.name
                    self.units[event.unit_id] = u_name
                    
                    if u_name in ["One", "Two", "Three", "Hatchery", "Lair", "Hive"]: 
                         self.townhalls += 1
                    elif u_name == "Drone":
                         self.workers += 1
                    elif u_name in ["Zergling", "Roach", "Hydralisk", "Mutalisk", "Ultralisk"]:
                         self.army_count += 1
                         if hasattr(event.unit, 'hp'):
                            self.army_hp += event.unit.hp
                    elif u_name == "Larva":
                         self.larva_count += 1
            elif hasattr(event, 'control_pid') and event.control_pid != 0: # Enemy
                self.enemy_units += 1
                
        # Unit Died
        elif 'UnitDiedEvent' in event_type:
            if event.unit_id in self.units:
                u_name = self.units[event.unit_id]
                del self.units[event.unit_id]
                
                if u_name == "Drone":
                    self.workers = max(0, self.workers - 1)
                elif u_name in ["Zergling", "Roach", "Hydralisk", "Mutalisk", "Ultralisk"]:
                    self.army_count = max(0, self.army_count - 1)
                    
        # Stats (if available)
        elif 'PlayerStatsEvent' in event_type:
             if event.player.pid == self.player_id:
                 self.minerals = event.minerals_current
                 self.gas = event.vespene_current
                 self.supply_used = event.food_used
                 self.supply_cap = event.food_made

    def get_state_vector(self, game_time) -> np.ndarray:
        # Match the 15-dim vector from bot_step_integration.py
        # [M, G, S_used, S_cap, Workers, Units, EnemyUnits, Bases, Time, EnemyBases, Upgrades, Larva, MapControl, ArmyHP, EnemyHP]
        
        # Scale factors (approximate)
        return np.array([
            min(self.minerals / 2000.0, 1.0),
            min(self.gas / 1000.0, 1.0),
            min(self.supply_used / 200.0, 1.0),
            min(self.supply_cap / 200.0, 1.0),
            min(self.workers / 100.0, 1.0),
            min(len(self.units) / 100.0, 1.0),
            min(self.enemy_units / 100.0, 1.0),
            min(self.townhalls / 10.0, 1.0),
            min(game_time / 1000.0, 1.0),
            min(self.enemy_bases / 5.0, 1.0),
            min(len(self.upgrades) / 10.0, 1.0),
            min(self.larva_count / 20.0, 1.0),
            0.5, # Map control unknown
            min(self.army_hp / 5000.0, 1.0), # Approx
            min(self.enemy_army_hp / 5000.0, 1.0)
        ], dtype=np.float32)

def determine_strategy(tracker, game_time) -> str:
    """Heuristic to label current strategy based on state"""
    # Simple heuristics
    if game_time < 300: # Early Game
        if tracker.army_count > 6 and tracker.workers < 15:
            return "AGGRESSIVE" # Zergling rush?
        if tracker.townhalls >= 3:
            return "ECONOMY"
        if tracker.workers > 20: 
            return "ECONOMY"
            
    # Mid Game
    if tracker.army_count > 30:
        return "ALL_IN" # Big army
        
    if "Spire" in str(tracker.units.values()) or "Lair" in str(tracker.units.values()):
        return "TECH"
        
    return "DEFENSIVE" # Default

STRATEGY_MAP = {
    "ECONOMY": 0,
    "AGGRESSIVE": 1,
    "DEFENSIVE": 2,
    "TECH": 3,
    "ALL_IN": 4
}

def train_from_replays(replay_dir, model_path=None):
    print("Initializing RLAgent...")
    agent = RLAgent(model_path=model_path)
    
    replay_files = list(Path(replay_dir).glob("*.SC2Replay"))
    print(f"Found {len(replay_files)} replays.")
    
    experiences = []
    processed_replays = []
    
    for r_path in replay_files:
        try:
            # Load replay
            # load_level=4 is needed for tracker events (resources) if available
            replay = sc2reader.load_replay(str(r_path), load_level=4)
            
            # Find Zerg winner (we want to learn from WINNERS)
            if replay.winner is None: continue
            
            winner_team = replay.winner
            winner = None
            
            # Check if winner is a Team object (common in sc2reader)
            if hasattr(winner_team, 'players'):
                for p in winner_team.players:
                    if p.play_race == "Zerg":
                        winner = p
                        break
            # Fallback if winner is Player object
            elif hasattr(winner_team, 'play_race') and winner_team.play_race == "Zerg":
                winner = winner_team
                
            if winner is None: continue
            
            print(f"Processing {r_path.name} (Winner: {winner.name})...")
            tracker = None
            tracker = ReplayStateTracker(winner.pid)
            print(f"  [DEBUG] Tracker initialized: {tracker}")
            
            states = []
            actions = []
            rewards = []
            
            # Iterate events
            for event in replay.events:
                tracker.update(event)
                
                # Sample every 30 seconds
                if hasattr(event, 'second') and event.second > 0 and event.second % 30 == 0:
                     # Only take one sample per 30s block
                     # (In a real implementation, we'd need better debounce)
                     pass
                     
            # SIMPLIFIED: Instead of event loop sampling which is tricky to sync,
            # we will just create synthetic data based on Replay Length + Outcome.
            # Real replay parsing for state is VERY hard without a running game engine.
            # sc2reader gives events, but reconstructing "Current Minerals" at t=120 is hard unless PlayerStats events exist.
            
            # Fallback: Use PlayerStatsEvent if available to drive the loop
            stats_events = [e for e in replay.events if 'PlayerStatsEvent' in type(e).__name__ and e.player.pid == winner.pid]
            
            if not stats_events:
                print("  -> No stats events, skipping.")
                continue
                
            for stat in stats_events:
                # Update tracker with authoritative stats
                tracker.minerals = stat.minerals_current
                tracker.gas = stat.vespene_current
                tracker.supply_used = stat.food_used
                tracker.supply_cap = stat.food_made
                
                game_time = stat.second
                
                state = tracker.get_state_vector(game_time)
                strategy = determine_strategy(tracker, game_time)
                action_idx = STRATEGY_MAP.get(strategy, 2)
                
                states.append(state)
                actions.append(action_idx)
                rewards.append(0.1) # Small survival reward
                
            # Assign final reward
            if rewards:
                rewards[-1] = 1.0 # Win bonus
                
            experiences.append({
                "states": np.array(states),
                "actions": np.array(actions),
                "rewards": np.array(rewards)
            })
            processed_replays.append(r_path)
            
        except Exception as e:
            print(f"Error processing {r_path.name}: {e}")
            
    # Train
    if experiences:
        print(f"Training on {len(experiences)} games...")
        
        # User request: Train each replay 5 times
        epochs = 5
        for i in range(epochs):
            print(f"--- Epoch {i+1}/{epochs} ---")
            result = agent.train_from_batch(experiences)
            print(f"  Result: {result}")
            
        agent.save_model()
        
        # Move processed replays to 'completed' folder
        completed_dir = Path(replay_dir) / "completed"
        try:
            completed_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            
            print(f"Moving {len(processed_replays)} processed replays to {completed_dir}...")
            for r_path in processed_replays:
                try:
                    dest = completed_dir / r_path.name
                    if dest.exists():
                        # Handle duplicates by renaming
                        stem = r_path.stem
                        suffix = r_path.suffix
                        timestamp = os.path.getmtime(r_path)
                        dest = completed_dir / f"{stem}_{int(timestamp)}{suffix}"
                        
                    shutil.move(str(r_path), str(dest))
                    print(f"  Moved: {r_path.name}")
                except Exception as e:
                    print(f"  Failed to move {r_path.name}: {e}")
                    
        except Exception as e:
            print(f"Error creating completed directory: {e}")
            
    else:
        print("No valid experiences extracted.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--replays", default="D:/replays/replays")
    args = parser.parse_args()
    
    train_from_replays(args.replays)
