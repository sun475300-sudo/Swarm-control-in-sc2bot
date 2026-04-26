# -*- coding: utf-8 -*-
"""
Racial Counter Manager - Race-specific unit composition counter logic

Extracted from strategy_manager.py to reduce complexity and improve maintainability.
Handles dynamic unit ratio adjustments based on detected enemy compositions.

Usage:
    counter_mgr = RacialCounterManager(bot, blackboard, logger)
    counter_mgr.update(enemy_race, game_phase, game_time, enemy_composition)
"""

from typing import Dict, List, Tuple
from config.config_loader import ConfigLoader


class RacialCounterManager:
    """
    Race-specific counter build logic.

    Analyzes enemy composition and returns recommended unit ratios.
    All thresholds are config-driven via strategy_config.json -> counter_build.
    """

    def __init__(self, bot, blackboard=None, logger=None):
        self.bot = bot
        self.blackboard = blackboard
        self.logger = logger

        # Counter config from JSON
        self._counter_cfg = ConfigLoader.get_counter_build_config()

        # Log spam prevention
        self._log_flags: Dict[str, bool] = {}
        self._last_log_times: Dict[str, float] = {}
        self.log_cooldown = 5.0

    def update(
        self,
        enemy_race: str,
        game_phase: str,
        game_time: float,
        enemy_composition: Dict[str, int],
        current_ratios: Dict[str, float],
        request_building_fn=None,
    ) -> Dict[str, float]:
        """
        Analyze enemy composition and return adjusted unit ratios.

        Args:
            enemy_race: "Terran", "Protoss", "Zerg", or "Unknown"
            game_phase: Current game phase string
            game_time: Current game time in seconds
            enemy_composition: Dict of {unit_type_name: count}
            current_ratios: Current unit production ratios
            request_building_fn: Callback for requesting defensive buildings

        Returns:
            Updated unit ratio dict (normalized to sum=1.0)
        """
        ratios = dict(current_ratios)

        if enemy_race == "Terran":
            ratios = self._counter_terran(game_time, enemy_composition, ratios, request_building_fn)
        elif enemy_race == "Protoss":
            ratios = self._counter_protoss(game_time, enemy_composition, ratios, request_building_fn)
        elif enemy_race == "Zerg":
            ratios = self._counter_zerg(game_time, enemy_composition, ratios, request_building_fn)

        # High-value threat scan (merged from DynamicCounterSystem)
        self.scan_high_threats(enemy_composition, game_time)

        return self._normalize(ratios)

    # ------------------------------------------------------------------
    # Terran counters
    # ------------------------------------------------------------------

    def _counter_terran(
        self, game_time: float, comp: Dict[str, int],
        ratios: Dict[str, float], req_building=None,
    ) -> Dict[str, float]:
        marine = comp.get("MARINE", 0)
        marauder = comp.get("MARAUDER", 0)
        medivac = comp.get("MEDIVAC", 0)
        tank = comp.get("SIEGETANK", 0) + comp.get("SIEGETANKSIEGED", 0)
        thor = comp.get("THOR", 0) + comp.get("THORAP", 0)
        hellion = comp.get("HELLION", 0) + comp.get("HELLIONTANK", 0)
        banshee = comp.get("BANSHEE", 0)
        battlecruiser = comp.get("BATTLECRUISER", 0)
        liberator = comp.get("LIBERATOR", 0) + comp.get("LIBERATORAG", 0)

        bio = marine + marauder

        # Bio (marine 6+ or medivac drop): baneling + zergling surround
        if bio >= 6 or (medivac >= 2 and bio >= 4):
            self._set(ratios, "baneling", 0.25)
            self._set(ratios, "zergling", 0.30)
            self._set(ratios, "roach", 0.20)
            self._set(ratios, "hydralisk", 0.15)
            self._set(ratios, "ravager", 0.10)
            self._log_once("zvt_bio", game_time, 300,
                           f"[{int(game_time)}s] ZvT BIO -> Baneling+Ling priority")

        # Mech (tanks/thors): ravager bile + flank
        if tank >= 2 or thor >= 1:
            self._set(ratios, "ravager", 0.30)
            self._set(ratios, "roach", 0.25)
            self._set(ratios, "hydralisk", 0.20)
            self._set(ratios, "zergling", 0.15)
            self._set(ratios, "corruptor", 0.10)
            self._log_once("zvt_mech", game_time, 300,
                           f"[{int(game_time)}s] ZvT MECH -> Ravager bile + Roach")

        # Air (banshee/BC/liberator): hydra + corruptor
        if banshee >= 1 or battlecruiser >= 1 or liberator >= 2:
            self._set(ratios, "hydralisk", 0.35)
            self._set(ratios, "corruptor", 0.25)
            self._set(ratios, "roach", 0.20)
            self._set(ratios, "queen", 0.10)
            self._set(ratios, "zergling", 0.10)
            if req_building:
                req_building(spore=True)
            self._log_once("zvt_air", game_time, 300,
                           f"[{int(game_time)}s] ZvT AIR -> Hydra+Corruptor+Spore")

        # Hellion rush (early game): queen + roach
        if hellion >= 3 and game_time < 300:
            self._set(ratios, "queen", 0.20)
            self._set(ratios, "roach", 0.40)
            self._set(ratios, "zergling", 0.30)
            self._set(ratios, "ravager", 0.10)

        return ratios

    # ------------------------------------------------------------------
    # Protoss counters
    # ------------------------------------------------------------------

    def _counter_protoss(
        self, game_time: float, comp: Dict[str, int],
        ratios: Dict[str, float], req_building=None,
    ) -> Dict[str, float]:
        immortal = comp.get("IMMORTAL", 0)
        colossus = comp.get("COLOSSUS", 0)
        voidray = comp.get("VOIDRAY", 0)
        disruptor = comp.get("DISRUPTOR", 0)
        high_templar = comp.get("HIGHTEMPLAR", 0)
        archon = comp.get("ARCHON", 0)
        carrier = comp.get("CARRIER", 0)
        stalker = comp.get("STALKER", 0)

        # DT/Oracle tech alert response
        intel = getattr(self.bot, "intel", None)
        if intel and hasattr(intel, "has_tech_alert"):
            if intel.has_tech_alert("DT_INCOMING"):
                if not self._log_flags.get("dt_response"):
                    self._log_flags["dt_response"] = True
                    if req_building:
                        req_building(spore=True)
                    if self.logger:
                        self.logger.warning(f"[{int(game_time)}s] DT INCOMING! Spore + Overseer PRIORITY")
                    if self.blackboard:
                        self.blackboard.set("urgent_overseer", True)

            if intel.has_tech_alert("AIR_INCOMING"):
                if not self._log_flags.get("air_response"):
                    self._log_flags["air_response"] = True
                    if req_building:
                        req_building(spore=True)
                    if self.logger:
                        self.logger.warning(f"[{int(game_time)}s] STARGATE TECH! Spore + Queen PRIORITY")

        # Immortal 2+ -> ravager bile + zergling surround
        if immortal >= 2:
            self._set(ratios, "ravager", 0.35)
            self._set(ratios, "zergling", 0.35)
            self._set(ratios, "roach", 0.10)
            self._log_once("zvp_immortal", game_time, 300,
                           f"[{int(game_time)}s] IMMORTAL ({immortal}) - Ravager bile priority")

        # Colossus 1+ -> corruptor mandatory
        if colossus >= 1:
            self._set(ratios, "corruptor", 0.40)
            self._set(ratios, "ravager", 0.20)
            self._set(ratios, "hydra", 0.30)
            self._log_once("zvp_colossus", game_time, 300,
                           f"[{int(game_time)}s] COLOSSUS ({colossus}) - Corruptor PRIORITY")

        # Void Ray / Carrier -> anti-air + viper
        if voidray >= 2 or carrier >= 1:
            self._set(ratios, "hydralisk", 0.35)
            self._set(ratios, "corruptor", 0.30)
            if carrier >= 3:
                self._set(ratios, "viper", 0.10)
                self._set(ratios, "corruptor", 0.25)
                self._set(ratios, "hydralisk", 0.30)
            self._log_once("zvp_air", game_time, 300,
                           f"[{int(game_time)}s] AIR THREAT - VoidRay/Carrier detected")

        # Disruptor -> split micro, fast units
        if disruptor >= 1:
            self._set(ratios, "zergling", 0.30)
            self._set(ratios, "mutalisk", 0.30)
            self._log_cooldown("zvp_disruptor", game_time,
                               f"[{int(game_time)}s] DISRUPTOR - Split micro needed")

        # High Templar / Archon -> rush them
        if high_templar >= 1 or archon >= 2:
            self._set(ratios, "zergling", 0.40)
            self._set(ratios, "ravager", 0.30)
            self._log_cooldown("zvp_ht", game_time,
                               f"[{int(game_time)}s] HIGH TEMPLAR/ARCHON - Rush them!")

        # Stalker 4+ -> zergling surround + roach
        if stalker >= 4:
            self._set(ratios, "zergling", 0.35)
            self._set(ratios, "roach", 0.30)
            self._set(ratios, "ravager", 0.20)
            self._set(ratios, "baneling", 0.15)
            self._log_once("zvp_stalker", game_time, 300,
                           f"[{int(game_time)}s] ZvP STALKER ARMY -- Zergling surround + Roach")

        return ratios

    # ------------------------------------------------------------------
    # Zerg counters (ZvZ)
    # ------------------------------------------------------------------

    def _counter_zerg(
        self, game_time: float, comp: Dict[str, int],
        ratios: Dict[str, float], req_building=None,
    ) -> Dict[str, float]:
        zergling = comp.get("ZERGLING", 0)
        baneling = comp.get("BANELING", 0)
        roach = comp.get("ROACH", 0)
        mutalisk = comp.get("MUTALISK", 0)
        hydra = comp.get("HYDRALISK", 0)

        # Zergling 10+ -> roach + baneling (ling mirror is bad)
        if zergling >= 10:
            self._set(ratios, "roach", 0.40)
            self._set(ratios, "baneling", 0.30)
            self._set(ratios, "zergling", 0.20)

        # Baneling 4+ -> roach transition
        if baneling >= 4:
            self._set(ratios, "roach", 0.50)
            self._set(ratios, "ravager", 0.20)

        # Roach 5+ -> ravager + hydra
        if roach >= 5:
            self._set(ratios, "ravager", 0.30)
            self._set(ratios, "hydra", 0.30)
            self._set(ratios, "roach", 0.30)

        # Mutalisk 3+ -> hydra + spore
        if mutalisk >= 3:
            self._set(ratios, "hydra", 0.50)
            if req_building:
                req_building(spore=True)
            self._log_cooldown("zvz_muta", game_time,
                               f"[{int(game_time)}s] ZvZ: Mutalisk detected! Hydra + Spore priority")

        # Mid-game transition: roach/hydra mirror -> lurker
        if game_time >= 360 and (roach >= 5 or hydra >= 5):
            self._set(ratios, "lurker", 0.20)
            self._set(ratios, "hydra", 0.30)
            self._set(ratios, "roach", 0.25)
            self._set(ratios, "ravager", 0.15)
            self._set(ratios, "zergling", 0.10)
            self._log_once("zvz_lurker", game_time, 360,
                           f"[{int(game_time)}s] ZvZ MID: Lurker transition for positional advantage")

        return ratios

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _set(ratios: Dict[str, float], unit: str, value: float) -> None:
        """Set ratio only if higher than current (boost, not reduce)."""
        if value > ratios.get(unit, 0):
            ratios[unit] = value

    @staticmethod
    def _normalize(ratios: Dict[str, float]) -> Dict[str, float]:
        """Normalize ratios to sum to 1.0."""
        total = sum(ratios.values())
        if total > 0:
            return {k: v / total for k, v in ratios.items()}
        return ratios

    def _log_once(self, key: str, game_time: float, min_time: float, msg: str) -> None:
        """Log a message only once per game."""
        if game_time > min_time and not self._log_flags.get(key):
            self._log_flags[key] = True
            if self.logger:
                self.logger.info(msg)

    def _log_cooldown(self, key: str, game_time: float, msg: str) -> None:
        """Log with cooldown to prevent spam."""
        last = self._last_log_times.get(key, 0)
        if game_time - last > self.log_cooldown:
            self._last_log_times[key] = game_time
            if self.logger:
                self.logger.warning(msg)

    # ------------------------------------------------------------------
    # High-threat unit detection (merged from DynamicCounterSystem)
    # ------------------------------------------------------------------

    # Counter rules for high-value enemy units
    THREAT_COUNTER_RULES: Dict[str, Dict] = {
        "BATTLECRUISER": {"counter_units": ["corruptor", "queen"], "ratios": [0.70, 0.30], "min_count": 8, "urgency": "CRITICAL"},
        "THOR":          {"counter_units": ["roach", "ravager"], "ratios": [0.60, 0.40], "min_count": 8, "urgency": "HIGH"},
        "SIEGETANK":     {"counter_units": ["roach", "ravager", "mutalisk"], "ratios": [0.40, 0.30, 0.30], "min_count": 6, "urgency": "HIGH"},
        "LIBERATOR":     {"counter_units": ["corruptor", "hydralisk"], "ratios": [0.70, 0.30], "min_count": 6, "urgency": "MEDIUM"},
        "CARRIER":       {"counter_units": ["corruptor", "hydralisk"], "ratios": [0.80, 0.20], "min_count": 10, "urgency": "CRITICAL"},
        "VOIDRAY":       {"counter_units": ["corruptor", "hydralisk"], "ratios": [0.60, 0.40], "min_count": 6, "urgency": "HIGH"},
        "COLOSSUS":      {"counter_units": ["corruptor", "roach"], "ratios": [0.70, 0.30], "min_count": 6, "urgency": "HIGH"},
        "DISRUPTOR":     {"counter_units": ["roach", "hydralisk"], "ratios": [0.50, 0.50], "min_count": 8, "urgency": "HIGH"},
        "IMMORTAL":      {"counter_units": ["hydralisk", "roach", "zergling"], "ratios": [0.50, 0.30, 0.20], "min_count": 10, "urgency": "HIGH"},
        "ARCHON":        {"counter_units": ["roach", "hydralisk"], "ratios": [0.60, 0.40], "min_count": 8, "urgency": "HIGH"},
        "BROODLORD":     {"counter_units": ["corruptor", "hydralisk"], "ratios": [0.80, 0.20], "min_count": 8, "urgency": "CRITICAL"},
        "ULTRALISK":     {"counter_units": ["roach", "queen"], "ratios": [0.80, 0.20], "min_count": 10, "urgency": "HIGH"},
        "LURKER":        {"counter_units": ["roach", "hydralisk"], "ratios": [0.50, 0.50], "min_count": 8, "urgency": "HIGH"},
    }

    def scan_high_threats(self, enemy_composition: Dict[str, int], game_time: float) -> None:
        """
        Scan for high-value enemy units and register counters to Blackboard.
        Replaces DynamicCounterSystem.on_step().
        """
        for unit_name, count in enemy_composition.items():
            if count <= 0:
                continue
            rule = self.THREAT_COUNTER_RULES.get(unit_name)
            if not rule:
                continue

            flag_key = f"threat_{unit_name}"
            if flag_key not in self._log_flags:
                self._log_flags[flag_key] = True
                if self.logger:
                    self.logger.warning(
                        f"[{int(game_time)}s] HIGH THREAT: {unit_name} x{count} "
                        f"-> Counter: {rule['counter_units']} (urgency={rule['urgency']})"
                    )

                # Register counter override to Blackboard
                if self.blackboard:
                    override = self.blackboard.get("unit_composition_override", {})
                    for unit, ratio in zip(rule["counter_units"], rule["ratios"]):
                        override[unit] = override.get(unit, 0) + ratio * 0.3
                    self.blackboard.set("unit_composition_override", override)
                    self.blackboard.set("dynamic_counter_active", True)

    def get_active_threats(self) -> List[str]:
        """Return list of detected high-value enemy unit types."""
        return [k.replace("threat_", "") for k in self._log_flags if k.startswith("threat_")]

    def get_highest_threat(self) -> Tuple[str, str]:
        """Return highest urgency threat detected."""
        threats = self.get_active_threats()
        for urgency in ["CRITICAL", "HIGH", "MEDIUM"]:
            for t in threats:
                rule = self.THREAT_COUNTER_RULES.get(t, {})
                if rule.get("urgency") == urgency:
                    return (t, urgency)
        return ("NONE", "NONE")

    def reset(self) -> None:
        """Reset state between games."""
        self._log_flags.clear()
        self._last_log_times.clear()
        self._counter_cfg = ConfigLoader.get_counter_build_config()
