# -*- coding: utf-8 -*-
"""
Build Order Execution Tracker

Tracks build order execution timing, compares actual vs target times,
and analyzes delay causes.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        SPAWNINGPOOL = "SPAWNINGPOOL"
        EXTRACTOR = "EXTRACTOR"
        HATCHERY = "HATCHERY"
        OVERLORD = "OVERLORD"
        DRONE = "DRONE"
        ZERGLING = "ZERGLING"


@dataclass
class BuildOrderEvent:
    """Single build order event"""
    action: str
    unit_type: str
    target_supply: float
    target_time: float
    actual_supply: float
    actual_time: float
    delay_seconds: float = 0.0
    delay_reason: str = ""
    status: str = "pending"  # pending, completed, delayed, failed


class BuildOrderTracker:
    """
    Tracks build order execution and compares with target timings
    """
    
    def __init__(self, bot: Any, log_file: Optional[Path] = None):
        self.bot = bot
        self.events: List[BuildOrderEvent] = []
        self.current_events: Dict[str, BuildOrderEvent] = {}
        
        # Log file for persistence
        if log_file is None:
            script_dir = Path(__file__).parent.parent
            log_file = script_dir / "local_training" / "scripts" / "build_order_log.json"
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load learned parameters for target timings
        self._load_target_parameters()
    
    def _load_target_parameters(self):
        """Load target parameters from learned_build_orders.json"""
        try:
            script_dir = Path(__file__).parent.parent
            learned_file = script_dir / "local_training" / "scripts" / "learned_build_orders.json"
            
            if learned_file.exists():
                with open(learned_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                learned_params = data.get("learned_parameters", {})
                self.target_params = {
                    "spawning_pool_supply": learned_params.get("spawning_pool_supply", 17.0),
                    "gas_supply": learned_params.get("gas_supply", 17.0),
                    "natural_expansion_supply": learned_params.get("natural_expansion_supply", 31.0),
                    "roach_warren_supply": learned_params.get("roach_warren_supply", 54.0),
                    "hydralisk_den_supply": learned_params.get("hydralisk_den_supply", 124.0),
                    "lair_supply": learned_params.get("lair_supply", 12.0),
                    "hive_supply": learned_params.get("hive_supply", 12.0),
                }
            else:
                self.target_params = {}
        except Exception as e:
            print(f"[BUILD TRACKER] Failed to load target parameters: {e}")
            self.target_params = {}
    
    def start_tracking(self, action: str, unit_type: str, target_supply: float):
        """
        Start tracking a build order action
        
        Args:
            action: Action name (e.g., "Build Spawning Pool")
            unit_type: Unit type (e.g., "SPAWNINGPOOL")
            target_supply: Target supply when this should be built
        """
        # Calculate target time (rough estimate: 1 supply = 1.5 seconds)
        target_time = target_supply * 1.5
        
        event = BuildOrderEvent(
            action=action,
            unit_type=unit_type,
            target_supply=target_supply,
            target_time=target_time,
            actual_supply=0.0,
            actual_time=0.0,
            status="pending"
        )
        
        key = f"{unit_type}_{target_supply}"
        self.current_events[key] = event
        
        if self.bot.iteration % 50 == 0:
            print(f"[BUILD TRACKER] Started tracking: {action} (target: supply {target_supply}, time {target_time:.1f}s)")
    
    def check_completion(self):
        """Check if any tracked events have completed"""
        b = self.bot
        current_time = getattr(b, "time", 0.0)
        current_supply = getattr(b, "supply_used", 0)
        
        # Map unit types to check
        unit_type_map = {
            "SPAWNINGPOOL": UnitTypeId.SPAWNINGPOOL,
            "EXTRACTOR": UnitTypeId.EXTRACTOR,
            "HATCHERY": UnitTypeId.HATCHERY,
            "OVERLORD": UnitTypeId.OVERLORD,
        }
        
        completed_keys = []
        for key, event in self.current_events.items():
            if event.status != "pending":
                continue
            
            unit_type_id = unit_type_map.get(event.unit_type)
            if unit_type_id:
                # Check if structure/unit exists
                structures = b.structures(unit_type_id) if hasattr(b, "structures") else []
                units = b.units(unit_type_id) if hasattr(b, "units") else []
                
                if (structures.exists if hasattr(structures, "exists") else len(list(structures)) > 0) or \
                   (units.exists if hasattr(units, "exists") else len(list(units)) > 0):
                    # Completed!
                    event.actual_time = current_time
                    event.actual_supply = current_supply
                    event.delay_seconds = current_time - event.target_time
                    event.status = "completed" if event.delay_seconds <= 5 else "delayed"
                    
                    # Analyze delay reason
                    if event.delay_seconds > 5:
                        event.delay_reason = self._analyze_delay_reason(event)
                    
                    self.events.append(event)
                    completed_keys.append(key)
                    
                    # Log completion
                    delay_str = f" (delay: {event.delay_seconds:.1f}s)" if event.delay_seconds > 5 else ""
                    print(f"[BUILD TRACKER] Completed: {event.action} at {current_time:.1f}s (target: {event.target_time:.1f}s){delay_str}")
                    if event.delay_reason:
                        print(f"[BUILD TRACKER] Delay reason: {event.delay_reason}")
        
        # Remove completed events
        for key in completed_keys:
            del self.current_events[key]
    
    def _analyze_delay_reason(self, event: BuildOrderEvent) -> str:
        """Analyze why a build order step was delayed"""
        b = self.bot
        reasons = []
        
        # Check supply block
        supply_left = getattr(b, "supply_left", 0)
        if supply_left < 1 and event.actual_supply > event.target_supply:
            reasons.append("supply_block")
        
        # Check resources
        minerals = getattr(b, "minerals", 0)
        vespene = getattr(b, "vespene", 0)
        
        # Estimate required resources
        required_minerals = 0
        required_gas = 0
        
        if event.unit_type == "SPAWNINGPOOL":
            required_minerals = 200
        elif event.unit_type == "EXTRACTOR":
            required_minerals = 25
        elif event.unit_type == "HATCHERY":
            required_minerals = 300
        
        if minerals < required_minerals * 0.8:
            reasons.append("insufficient_minerals")
        if vespene < required_gas * 0.8 and required_gas > 0:
            reasons.append("insufficient_gas")
        
        # Check larvae availability
        if event.unit_type in ["DRONE", "ZERGLING", "OVERLORD"]:
            larvae = b.units(UnitTypeId.LARVA) if hasattr(b, "units") else []
            if not (larvae.exists if hasattr(larvae, "exists") else len(list(larvae)) > 0):
                reasons.append("no_larvae")
        
        return ", ".join(reasons) if reasons else "unknown"
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of build order execution"""
        if not self.events:
            return {
                "total_events": 0,
                "completed": 0,
                "delayed": 0,
                "average_delay": 0.0,
                "on_time_percentage": 0.0
            }
        
        completed = [e for e in self.events if e.status == "completed"]
        delayed = [e for e in self.events if e.status == "delayed"]
        
        total_delay = sum(e.delay_seconds for e in delayed)
        avg_delay = total_delay / len(delayed) if delayed else 0.0
        
        on_time = len(completed)
        on_time_pct = (on_time / len(self.events) * 100) if self.events else 0.0
        
        return {
            "total_events": len(self.events),
            "completed": len(completed),
            "delayed": len(delayed),
            "average_delay": avg_delay,
            "on_time_percentage": on_time_pct,
            "events": [
                {
                    "action": e.action,
                    "target_time": e.target_time,
                    "actual_time": e.actual_time,
                    "delay": e.delay_seconds,
                    "reason": e.delay_reason
                }
                for e in self.events
            ]
        }
    
    def save_log(self):
        """Save build order log to file"""
        try:
            summary = self.get_summary()
            summary["timestamp"] = datetime.now().isoformat()
            
            # Load existing log
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            else:
                log_data = {"sessions": []}
            
            # Append current session
            log_data["sessions"].append(summary)
            
            # Keep only last 100 sessions
            if len(log_data["sessions"]) > 100:
                log_data["sessions"] = log_data["sessions"][-100:]
            
            # Save
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[BUILD TRACKER] Failed to save log: {e}")
