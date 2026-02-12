# -*- coding: utf-8 -*-
"""
Situational Awareness Module
Aggregates high-level game state into a structured SITREP (Situation Report)
for strategic decision-making and LLM context.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import json
import time

try:
    from strategy.strategy_manager_v2 import StrategyManagerV2, WinCondition
except ImportError:
    try:
        from strategy_manager_v2 import StrategyManagerV2, WinCondition
    except ImportError:
        StrategyManagerV2 = None
        WinCondition = None

class ThreatLevel(Enum):
    NONE = "none"           # 평화
    LOW = "low"             # 정찰/소규모 견제
    MEDIUM = "medium"       # 일반적인 교전 가능성
    HIGH = "high"           # 대규모 공격/치명적 러시 임박
    CRITICAL = "critical"   # 기지 피격 중/엘리 위기

class OpportunityIndex(Enum):
    NONE = "none"           # 기회 없음
    LOW = "low"             # 소규모 빈틈 (일꾼 견제 등)
    MEDIUM = "medium"       # 확장/테크 격차 발생
    HIGH = "high"           # 병력 공백/주요 업그레이드 타이밍
    GAME_ENDING = "finish"  # 킬각

class SituationalAwareness:
    """
    Central hub for high-level situational awareness.
    Generates reliable SITREPs by aggregating:
    - Blackboard (Raw Data)
    - StrategyManagerV2 (Win conditions, Scores)
    - IntelManager (Enemy Intelligence)
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger if hasattr(bot, "logger") else None
        
        # State tracking
        self.last_sitrep: Dict[str, Any] = {}
        self.last_update_time = 0.0
        self.update_interval = 2.0  # 2 seconds (doesn't need to be every frame)
        
        # Metrics
        self.threat_level = ThreatLevel.NONE
        self.opportunity_index = OpportunityIndex.NONE
        
        # History
        self.threat_history: List[ThreatLevel] = []
        self.sitrep_history: List[Dict[str, Any]] = []

    def on_step(self, iteration: int):
        """Execute on every step (throttled)"""
        game_time = getattr(self.bot, "time", 0.0)
        
        # Throttle updates
        if game_time - self.last_update_time < self.update_interval:
            return

        self.last_update_time = game_time
        self.update_sitrep()

    def update_sitrep(self):
        """Generate and update current Situation Report"""
        
        # 1. Gather component data
        win_condition = "UNKNOWN"
        strategy_scores = {}
        
        if hasattr(self.bot, "strategy_manager") and StrategyManagerV2 and isinstance(self.bot.strategy_manager, StrategyManagerV2):
             win_condition = self.bot.strategy_manager.current_win_condition.name
             strategy_scores = self.bot.strategy_manager.strategy_scores
        
        # 2. Assess Threat Level
        self.threat_level = self._assess_threat_level()
        
        # 3. Assess Opportunity
        self.opportunity_index = self._assess_opportunity()
        
        # 4. Construct SITREP object
        sitrep = {
            "timestamp": getattr(self.bot, "time", 0.0),
            "frame": getattr(self.bot, "iteration", 0),
            "game_phase": self._get_game_phase(),
            "status": {
                "win_condition": win_condition,
                "threat_level": self.threat_level.name,
                "opportunity": self.opportunity_index.name,
            },
            "economy": {
                "minerals": getattr(self.bot, "minerals", 0),
                "vespene": getattr(self.bot, "vespene", 0),
                "supply": f"{getattr(self.bot, 'supply_used', 0)}/{getattr(self.bot, 'supply_cap', 0)}",
                "workers": getattr(self.bot, "workers", []).amount if hasattr(self.bot, "workers") else 0,
                "bases": getattr(self.bot, "townhalls", []).amount if hasattr(self.bot, "townhalls") else 0,
            },
            "military": {
                "army_count": getattr(self.bot, "units", []).amount if hasattr(self.bot, "units") else 0,
                "strategy_scores": strategy_scores
            },
            "intelligence": self._get_intel_summary()
        }
        
        self.last_sitrep = sitrep
        self.sitrep_history.append(sitrep)
        
        # Keep history manageable (last 5 mins approx)
        if len(self.sitrep_history) > 150:
            self.sitrep_history.pop(0)

        # Update Blackboard if available
        if hasattr(self.bot, "blackboard") and self.bot.blackboard:
            self.bot.blackboard.set("sitrep", sitrep)

        # Log significant changes
        # self._log_changes(sitrep)

    def get_latest_sitrep(self) -> Dict[str, Any]:
        """Return the most recent SITREP"""
        return self.last_sitrep

    def _assess_threat_level(self) -> ThreatLevel:
        """Determine current threat level using blackboard and game state"""
        # Default
        level = ThreatLevel.NONE
        
        # Check explicit threats from Blackboard
        if hasattr(self.bot, "blackboard") and self.bot.blackboard:
            # If Defcon or existing threat logic is present
            if hasattr(self.bot.blackboard, "threat"):
                # Map existing threat to local enum if needed
                pass

        # Check for immediate danger (Attacked notifications)
        # Note: This is simplified. Real logic would verify unit proximity.
        # if self.bot.Client.debug_text... (Not accessible)
        
        # Base under attack check (Simplified)
        if hasattr(self.bot, "townhalls"):
            for base in self.bot.townhalls:
                if base.health_percentage < 0.9:
                    # Is it actually under attack now? 
                    # Checking if enemies are near
                    if hasattr(self.bot, "enemy_units") and self.bot.enemy_units:
                         enemies_near = self.bot.enemy_units.closer_than(15, base)
                         if enemies_near.exists:
                             return ThreatLevel.CRITICAL

        # Supply block check causing vulnerability?
        
        return level

    def _assess_opportunity(self) -> OpportunityIndex:
        """Determine offensive opportunities"""
        # Default
        index = OpportunityIndex.NONE
        
        # Army advantage?
        if hasattr(self.bot, "strategy_manager") and isinstance(self.bot.strategy_manager, StrategyManagerV2):
             if self.bot.strategy_manager.current_win_condition.name in ["WINNING_ARMY", "WINNING_ECONOMY"]:
                 index = OpportunityIndex.HIGH
        
        # Enemy stunned/no units?
        
        return index

    def _get_game_phase(self) -> str:
        """Get text representation of game phase"""
        if hasattr(self.bot, "strategy_manager") and hasattr(self.bot.strategy_manager, "current_build_phase"):
            return self.bot.strategy_manager.current_build_phase.name
        
        # Fallback time-based
        t = getattr(self.bot, "time", 0.0)
        if t < 300: return "OPENING"
        if t < 600: return "MIDGAME"
        return "LATEGAME"

    def _get_intel_summary(self) -> Dict[str, Any]:
        """Summarize enemy intel including detected threats"""
        if hasattr(self.bot, "enemy_race"):
            race = str(self.bot.enemy_race)
        else:
            race = "Unknown"

        # Threat detection logic
        detected_threats = []
        enemy_structures = getattr(self.bot, "enemy_structures", [])
        enemy_units = getattr(self.bot, "enemy_units", [])

        # 1. Cloak Detection
        cloak_tech = {
            "DARKSHRINE", "GHOSTACADEMY", "LURKERDEN", "LURKERDENMP"
        }
        if any(s.type_id.name.upper() in cloak_tech for s in enemy_structures):
            detected_threats.append("CLOAK_TECH")

        # 2. Air Threat
        air_tech = {
            "STARGATE", "STARPORT", "SPIRE", "GREATERSPIRE", "FLEETBEACON"
        }
        if any(s.type_id.name.upper() in air_tech for s in enemy_structures) or \
           any(u.is_flying and not u.is_structure for u in enemy_units):
            detected_threats.append("AIR_THREAT")

        # 3. Splash Damage
        splash_tech = {
            "BANELINGNEST", "ROBOTICSBAY", "TEMPLARARCHIVE", "FUSIONCORE"
        }
        if any(s.type_id.name.upper() in splash_tech for s in enemy_structures):
            detected_threats.append("SPLASH_DAMAGE")

        # 4. Hidden Bases
        # MapMemory might be better for this, but simplistic check here:
        known_bases = [s for s in enemy_structures if s.is_structure and s.type_id.name.upper() in {"NEXUS", "COMMANDCENTER", "ORBITALCOMMAND", "PLANETARYFORTRESS", "HATCHERY", "LAIR", "HIVE"}]
        
        return {
            "race": race,
            "threats": detected_threats,
            "detected_bases_count": len(known_bases),
            "last_seen_threat_frame": getattr(self.bot, "iteration", 0) if detected_threats else 0
        }
