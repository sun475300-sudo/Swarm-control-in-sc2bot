# Phase 658: Feature Flag System for SC2 Bot Dynamic Control
# Dynamic feature flags for toggling SC2 bot behaviors, strategies, and experiments

from __future__ import annotations

import hashlib
import json
import os
import time
import copy
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# ============================================================
# Constants & Enums
# ============================================================


class FlagType(Enum):
    """Supported feature flag types."""

    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    USER_TARGETING = "user_targeting"
    TIME_BASED = "time_based"
    JSON_VARIANT = "json_variant"


class FlagStatus(Enum):
    """Flag lifecycle status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


# ============================================================
# Audit Log
# ============================================================


@dataclass
class AuditEntry:
    """Single audit log entry for flag changes."""

    timestamp: float
    flag_name: str
    action: str
    old_value: Any
    new_value: Any
    actor: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "datetime": time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)
            ),
            "flag_name": self.flag_name,
            "action": self.action,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "actor": self.actor,
            "metadata": self.metadata,
        }


class AuditLog:
    """Thread-safe audit log for tracking flag changes."""

    def __init__(self, max_entries: int = 10000) -> None:
        self._entries: List[AuditEntry] = []
        self._max_entries = max_entries
        self._lock = threading.Lock()

    def record(
        self,
        flag_name: str,
        action: str,
        old_value: Any = None,
        new_value: Any = None,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=time.time(),
            flag_name=flag_name,
            action=action,
            old_value=old_value,
            new_value=new_value,
            actor=actor,
            metadata=metadata or {},
        )
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries :]
        return entry

    def query(
        self,
        flag_name: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        with self._lock:
            results = list(self._entries)
        if flag_name:
            results = [e for e in results if e.flag_name == flag_name]
        if action:
            results = [e for e in results if e.action == action]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results[-limit:]

    def export(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [e.to_dict() for e in self._entries]

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._entries)


# ============================================================
# Flag Definition
# ============================================================


@dataclass
class Flag:
    """A single feature flag with evaluation rules.

    Attributes:
        name: Unique flag identifier.
        flag_type: The type of flag (boolean, percentage, etc.).
        default_value: Fallback value when no rules match.
        description: Human-readable description.
        status: Current lifecycle status.
        rules: Ordered evaluation rules (first match wins).
        metadata: Arbitrary key-value metadata.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    name: str
    flag_type: FlagType = FlagType.BOOLEAN
    default_value: Any = False
    description: str = ""
    status: FlagStatus = FlagStatus.ACTIVE
    rules: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def is_active(self) -> bool:
        return self.status == FlagStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "flag_type": self.flag_type.value,
            "default_value": self.default_value,
            "description": self.description,
            "status": self.status.value,
            "rules": self.rules,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Flag:
        return cls(
            name=data["name"],
            flag_type=FlagType(data.get("flag_type", "boolean")),
            default_value=data.get("default_value", False),
            description=data.get("description", ""),
            status=FlagStatus(data.get("status", "active")),
            rules=data.get("rules", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


# ============================================================
# Percentage Rollout
# ============================================================


class PercentageRollout:
    """Consistent percentage-based feature rollout using hashing.

    Uses deterministic hashing so the same user_id + flag_name
    always gets the same bucket, ensuring consistent experience.
    """

    @staticmethod
    def compute_bucket(flag_name: str, user_id: str, num_buckets: int = 100) -> int:
        key = f"{flag_name}:{user_id}"
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % num_buckets

    @staticmethod
    def is_enabled(flag_name: str, user_id: str, percentage: float) -> bool:
        if percentage <= 0.0:
            return False
        if percentage >= 100.0:
            return True
        bucket = PercentageRollout.compute_bucket(flag_name, user_id)
        return bucket < percentage

    @staticmethod
    def get_variant(
        flag_name: str,
        user_id: str,
        variants: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Select a variant based on weighted percentages.

        Each variant dict must have 'name' and 'weight' keys.
        Weights should sum to 100.
        """
        bucket = PercentageRollout.compute_bucket(flag_name, user_id)
        cumulative = 0.0
        for variant in variants:
            cumulative += variant.get("weight", 0)
            if bucket < cumulative:
                return variant
        return variants[-1] if variants else None


# ============================================================
# User Targeting
# ============================================================


class UserTargeting:
    """Rule-based user targeting for feature flags.

    Supports allowlists, blocklists, and attribute-based matching.
    """

    def __init__(self) -> None:
        self._allowlists: Dict[str, set] = {}
        self._blocklists: Dict[str, set] = {}
        self._attribute_rules: Dict[str, List[Callable[[Dict[str, Any]], bool]]] = {}

    def set_allowlist(self, flag_name: str, user_ids: List[str]) -> None:
        self._allowlists[flag_name] = set(user_ids)

    def add_to_allowlist(self, flag_name: str, user_id: str) -> None:
        if flag_name not in self._allowlists:
            self._allowlists[flag_name] = set()
        self._allowlists[flag_name].add(user_id)

    def set_blocklist(self, flag_name: str, user_ids: List[str]) -> None:
        self._blocklists[flag_name] = set(user_ids)

    def add_to_blocklist(self, flag_name: str, user_id: str) -> None:
        if flag_name not in self._blocklists:
            self._blocklists[flag_name] = set()
        self._blocklists[flag_name].add(user_id)

    def add_attribute_rule(
        self,
        flag_name: str,
        rule_fn: Callable[[Dict[str, Any]], bool],
    ) -> None:
        if flag_name not in self._attribute_rules:
            self._attribute_rules[flag_name] = []
        self._attribute_rules[flag_name].append(rule_fn)

    def evaluate(
        self,
        flag_name: str,
        user_id: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Optional[bool]:
        """Evaluate targeting rules. Returns None if no rule matches.

        Priority: blocklist > allowlist > attribute rules.
        """
        if flag_name in self._blocklists and user_id in self._blocklists[flag_name]:
            return False
        if flag_name in self._allowlists and user_id in self._allowlists[flag_name]:
            return True
        if flag_name in self._attribute_rules and attributes:
            for rule_fn in self._attribute_rules[flag_name]:
                if rule_fn(attributes):
                    return True
        return None


# ============================================================
# Flag Store (Persistence & Hot Reload)
# ============================================================


class FlagStore:
    """JSON-backed flag store with hot reload capability.

    Monitors a JSON configuration file and reloads flags when
    the file changes (based on modification time).
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._flags: Dict[str, Flag] = {}
        self._config_path = config_path
        self._last_mtime: float = 0.0
        self._lock = threading.Lock()

    @property
    def flags(self) -> Dict[str, Flag]:
        with self._lock:
            return dict(self._flags)

    def register(self, flag: Flag) -> None:
        with self._lock:
            self._flags[flag.name] = flag

    def unregister(self, flag_name: str) -> Optional[Flag]:
        with self._lock:
            return self._flags.pop(flag_name, None)

    def get(self, flag_name: str) -> Optional[Flag]:
        with self._lock:
            return self._flags.get(flag_name)

    def list_flags(self, status: Optional[FlagStatus] = None) -> List[Flag]:
        with self._lock:
            flags = list(self._flags.values())
        if status:
            flags = [f for f in flags if f.status == status]
        return flags

    def save_to_json(self, path: Optional[str] = None) -> str:
        target = path or self._config_path
        if not target:
            raise ValueError("No config path specified")
        data = {
            "version": "1.0",
            "generated_at": time.time(),
            "flags": {name: flag.to_dict() for name, flag in self._flags.items()},
        }
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        return target

    def load_from_json(self, path: Optional[str] = None) -> int:
        target = path or self._config_path
        if not target or not os.path.exists(target):
            return 0
        with open(target, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        flags_data = data.get("flags", {})
        count = 0
        with self._lock:
            for name, fdata in flags_data.items():
                self._flags[name] = Flag.from_dict(fdata)
                count += 1
        return count

    def check_and_reload(self) -> bool:
        """Check if config file changed and reload if necessary."""
        if not self._config_path or not os.path.exists(self._config_path):
            return False
        mtime = os.path.getmtime(self._config_path)
        if mtime > self._last_mtime:
            self._last_mtime = mtime
            self.load_from_json()
            return True
        return False

    def bulk_update(self, updates: Dict[str, Dict[str, Any]]) -> int:
        """Apply bulk updates to multiple flags at once."""
        count = 0
        with self._lock:
            for flag_name, changes in updates.items():
                if flag_name in self._flags:
                    flag = self._flags[flag_name]
                    for key, value in changes.items():
                        if key == "status":
                            flag.status = FlagStatus(value)
                        elif key == "default_value":
                            flag.default_value = value
                        elif key == "rules":
                            flag.rules = value
                        elif key == "metadata":
                            flag.metadata.update(value)
                    flag.updated_at = time.time()
                    count += 1
        return count


# ============================================================
# Time-Based Evaluation
# ============================================================


class TimeBasedEvaluator:
    """Evaluate flags based on time windows and schedules."""

    @staticmethod
    def is_within_window(
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        now: Optional[float] = None,
    ) -> bool:
        current = now or time.time()
        if start_time and current < start_time:
            return False
        if end_time and current > end_time:
            return False
        return True

    @staticmethod
    def is_within_game_time(
        game_loop: int,
        min_loop: int = 0,
        max_loop: int = 999999,
    ) -> bool:
        return min_loop <= game_loop <= max_loop

    @staticmethod
    def evaluate_schedule(
        schedule: Dict[str, Any],
        now: Optional[float] = None,
    ) -> bool:
        """Evaluate a time-based schedule rule.

        Schedule dict keys:
            start_time: Unix timestamp for activation.
            end_time: Unix timestamp for deactivation.
            active_hours: Tuple (start_hour, end_hour) in 24h format.
        """
        current = now or time.time()
        if "start_time" in schedule and current < schedule["start_time"]:
            return False
        if "end_time" in schedule and current > schedule["end_time"]:
            return False
        if "active_hours" in schedule:
            local_hour = time.localtime(current).tm_hour
            start_h, end_h = schedule["active_hours"]
            if start_h <= end_h:
                if not (start_h <= local_hour < end_h):
                    return False
            else:
                if end_h <= local_hour < start_h:
                    return False
        return True


# ============================================================
# SC2-Specific Flag Presets
# ============================================================

SC2_DEFAULT_FLAGS: List[Dict[str, Any]] = [
    {
        "name": "sc2.strategy.aggressive_mode",
        "flag_type": "boolean",
        "default_value": False,
        "description": "Enable aggressive all-in strategies",
        "rules": [{"type": "boolean", "value": False}],
    },
    {
        "name": "sc2.strategy.defensive_mode",
        "flag_type": "boolean",
        "default_value": True,
        "description": "Enable defensive turtle play style",
        "rules": [{"type": "boolean", "value": True}],
    },
    {
        "name": "sc2.micro.experimental_blink",
        "flag_type": "percentage",
        "default_value": False,
        "description": "Experimental blink stalker micro (percentage rollout)",
        "rules": [{"type": "percentage", "percentage": 25}],
    },
    {
        "name": "sc2.micro.baneling_split",
        "flag_type": "boolean",
        "default_value": True,
        "description": "Enable marine split vs banelings micro",
    },
    {
        "name": "sc2.macro.auto_expand",
        "flag_type": "time_based",
        "default_value": True,
        "description": "Auto-expand after game minute 5",
        "rules": [{"type": "time_based", "min_game_loop": 3360}],
    },
    {
        "name": "sc2.scouting.proxy_detect",
        "flag_type": "boolean",
        "default_value": True,
        "description": "Enable early proxy detection scouting",
    },
    {
        "name": "sc2.economy.aggressive_gas",
        "flag_type": "percentage",
        "default_value": False,
        "description": "Take early double gas (percentage rollout)",
        "rules": [{"type": "percentage", "percentage": 40}],
    },
    {
        "name": "sc2.army.composition_variant",
        "flag_type": "json_variant",
        "default_value": "standard",
        "description": "Army composition variant selection",
        "rules": [
            {
                "type": "variant",
                "variants": [
                    {"name": "standard", "weight": 50},
                    {"name": "air_heavy", "weight": 25},
                    {"name": "bio_rush", "weight": 25},
                ],
            }
        ],
    },
]


# ============================================================
# Feature Flag Service (Main Facade)
# ============================================================


class FeatureFlagService:
    """Main service coordinating flag evaluation.

    Provides a unified API for flag CRUD, evaluation with hierarchical
    rules (targeting > percentage > time-based > default), audit logging,
    and hot-reload from JSON configuration.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.store = FlagStore(config_path=config_path)
        self.targeting = UserTargeting()
        self.audit = AuditLog()
        self._overrides: Dict[str, Any] = {}

    # ---- Flag Management ----

    def create_flag(
        self,
        name: str,
        flag_type: Union[str, FlagType] = FlagType.BOOLEAN,
        default_value: Any = False,
        description: str = "",
        rules: Optional[List[Dict[str, Any]]] = None,
        actor: str = "system",
    ) -> Flag:
        if isinstance(flag_type, str):
            flag_type = FlagType(flag_type)
        flag = Flag(
            name=name,
            flag_type=flag_type,
            default_value=default_value,
            description=description,
            rules=rules or [],
        )
        self.store.register(flag)
        self.audit.record(name, "created", None, flag.to_dict(), actor)
        return flag

    def update_flag(
        self,
        name: str,
        changes: Dict[str, Any],
        actor: str = "system",
    ) -> Optional[Flag]:
        flag = self.store.get(name)
        if not flag:
            return None
        old_dict = flag.to_dict()
        for key, value in changes.items():
            if key == "default_value":
                flag.default_value = value
            elif key == "status":
                flag.status = FlagStatus(value) if isinstance(value, str) else value
            elif key == "rules":
                flag.rules = value
            elif key == "description":
                flag.description = value
            elif key == "metadata":
                flag.metadata.update(value)
        flag.updated_at = time.time()
        self.audit.record(name, "updated", old_dict, flag.to_dict(), actor)
        return flag

    def delete_flag(self, name: str, actor: str = "system") -> bool:
        flag = self.store.unregister(name)
        if flag:
            self.audit.record(name, "deleted", flag.to_dict(), None, actor)
            return True
        return False

    def archive_flag(self, name: str, actor: str = "system") -> bool:
        return self.update_flag(name, {"status": "archived"}, actor) is not None

    # ---- Override Management ----

    def set_override(self, flag_name: str, value: Any, actor: str = "system") -> None:
        old = self._overrides.get(flag_name)
        self._overrides[flag_name] = value
        self.audit.record(flag_name, "override_set", old, value, actor)

    def clear_override(self, flag_name: str, actor: str = "system") -> None:
        old = self._overrides.pop(flag_name, None)
        if old is not None:
            self.audit.record(flag_name, "override_cleared", old, None, actor)

    def clear_all_overrides(self) -> None:
        self._overrides.clear()

    # ---- Evaluation ----

    def evaluate(
        self,
        flag_name: str,
        user_id: str = "default",
        attributes: Optional[Dict[str, Any]] = None,
        game_loop: Optional[int] = None,
    ) -> Any:
        """Evaluate a flag with hierarchical rule resolution.

        Priority order:
        1. Manual overrides (highest)
        2. User targeting (blocklist > allowlist > attributes)
        3. Rule-based evaluation (percentage, time-based, variant)
        4. Default value (lowest)
        """
        # 1. Override check
        if flag_name in self._overrides:
            return self._overrides[flag_name]

        flag = self.store.get(flag_name)
        if not flag or not flag.is_active():
            return flag.default_value if flag else None

        # 2. User targeting
        targeting_result = self.targeting.evaluate(flag_name, user_id, attributes)
        if targeting_result is not None:
            return targeting_result

        # 3. Rule-based evaluation
        for rule in flag.rules:
            rule_type = rule.get("type", "")

            if rule_type == "boolean":
                return rule.get("value", flag.default_value)

            elif rule_type == "percentage":
                pct = rule.get("percentage", 0)
                return PercentageRollout.is_enabled(flag_name, user_id, pct)

            elif rule_type == "time_based":
                if game_loop is not None:
                    min_loop = rule.get("min_game_loop", 0)
                    max_loop = rule.get("max_game_loop", 999999)
                    if TimeBasedEvaluator.is_within_game_time(
                        game_loop, min_loop, max_loop
                    ):
                        return True
                    else:
                        continue
                schedule = {
                    k: v
                    for k, v in rule.items()
                    if k in ("start_time", "end_time", "active_hours")
                }
                if schedule and TimeBasedEvaluator.evaluate_schedule(schedule):
                    return True
                elif schedule:
                    continue
                return flag.default_value

            elif rule_type == "variant":
                variants = rule.get("variants", [])
                selected = PercentageRollout.get_variant(flag_name, user_id, variants)
                return selected["name"] if selected else flag.default_value

        # 4. Default fallback
        return flag.default_value

    def evaluate_all(
        self,
        user_id: str = "default",
        attributes: Optional[Dict[str, Any]] = None,
        game_loop: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Evaluate all active flags for a given context."""
        results = {}
        for flag in self.store.list_flags(status=FlagStatus.ACTIVE):
            results[flag.name] = self.evaluate(
                flag.name, user_id, attributes, game_loop
            )
        return results

    # ---- SC2 Presets ----

    def load_sc2_defaults(self) -> int:
        """Load SC2-specific default flags."""
        count = 0
        for preset in SC2_DEFAULT_FLAGS:
            self.create_flag(
                name=preset["name"],
                flag_type=preset.get("flag_type", "boolean"),
                default_value=preset.get("default_value", False),
                description=preset.get("description", ""),
                rules=preset.get("rules", []),
                actor="sc2_preset",
            )
            count += 1
        return count

    # ---- Persistence ----

    def save(self, path: Optional[str] = None) -> str:
        return self.store.save_to_json(path)

    def load(self, path: Optional[str] = None) -> int:
        return self.store.load_from_json(path)

    def hot_reload(self) -> bool:
        return self.store.check_and_reload()

    # ---- Reporting ----

    def get_flag_summary(self) -> Dict[str, Any]:
        """Return a summary of all flags and their current states."""
        all_flags = self.store.list_flags()
        summary = {
            "total": len(all_flags),
            "active": sum(1 for f in all_flags if f.status == FlagStatus.ACTIVE),
            "inactive": sum(1 for f in all_flags if f.status == FlagStatus.INACTIVE),
            "archived": sum(1 for f in all_flags if f.status == FlagStatus.ARCHIVED),
            "overrides": len(self._overrides),
            "audit_entries": self.audit.size,
            "flags": {},
        }
        for f in all_flags:
            summary["flags"][f.name] = {
                "type": f.flag_type.value,
                "status": f.status.value,
                "default": f.default_value,
                "rules_count": len(f.rules),
                "has_override": f.name in self._overrides,
            }
        return summary

    def get_audit_trail(
        self,
        flag_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        entries = self.audit.query(flag_name=flag_name, limit=limit)
        return [e.to_dict() for e in entries]


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate the Phase 658 Feature Flag System."""
    print("=" * 70)
    print("Phase 658: Feature Flag System for SC2 Bot Dynamic Control")
    print("=" * 70)

    service = FeatureFlagService()

    # --- Load SC2 Defaults ---
    print("\n[1] Loading SC2 default flags")
    count = service.load_sc2_defaults()
    print(f"    Loaded {count} SC2-specific flags")

    # --- Boolean Evaluation ---
    print("\n[2] Boolean flag evaluation")
    aggressive = service.evaluate("sc2.strategy.aggressive_mode", user_id="bot_v1")
    defensive = service.evaluate("sc2.strategy.defensive_mode", user_id="bot_v1")
    print(f"    Aggressive mode: {aggressive}")
    print(f"    Defensive mode:  {defensive}")

    # --- Percentage Rollout ---
    print("\n[3] Percentage rollout (blink stalker micro)")
    results = {}
    for i in range(100):
        uid = f"game_{i}"
        val = service.evaluate("sc2.micro.experimental_blink", user_id=uid)
        results[val] = results.get(val, 0) + 1
    print(f"    Enabled: {results.get(True, 0)}/100 games")
    print(f"    Disabled: {results.get(False, 0)}/100 games")

    # --- User Targeting ---
    print("\n[4] User targeting (allowlist / blocklist)")
    service.create_flag("sc2.test.vip_feature", default_value=False)
    service.targeting.set_allowlist(
        "sc2.test.vip_feature", ["pro_player_1", "streamer_2"]
    )
    service.targeting.set_blocklist("sc2.test.vip_feature", ["banned_user"])
    print(
        f"    pro_player_1: {service.evaluate('sc2.test.vip_feature', user_id='pro_player_1')}"
    )
    print(
        f"    random_user:  {service.evaluate('sc2.test.vip_feature', user_id='random_user')}"
    )
    print(
        f"    banned_user:  {service.evaluate('sc2.test.vip_feature', user_id='banned_user')}"
    )

    # --- Attribute-Based Targeting ---
    print("\n[5] Attribute-based targeting")
    service.create_flag("sc2.feature.high_mmr_only", default_value=False)
    service.targeting.add_attribute_rule(
        "sc2.feature.high_mmr_only",
        lambda attrs: attrs.get("mmr", 0) >= 5000,
    )
    high_mmr = service.evaluate(
        "sc2.feature.high_mmr_only",
        user_id="player_x",
        attributes={"mmr": 5500, "race": "Zerg"},
    )
    low_mmr = service.evaluate(
        "sc2.feature.high_mmr_only",
        user_id="player_y",
        attributes={"mmr": 3000, "race": "Terran"},
    )
    print(f"    MMR 5500 player: {high_mmr}")
    print(f"    MMR 3000 player: {low_mmr}")

    # --- Time-Based Flags ---
    print("\n[6] Time-based flag (auto-expand after game loop 3360)")
    early_game = service.evaluate("sc2.macro.auto_expand", game_loop=1000)
    mid_game = service.evaluate("sc2.macro.auto_expand", game_loop=5000)
    print(f"    Game loop 1000 (early): {early_game}")
    print(f"    Game loop 5000 (mid):   {mid_game}")

    # --- Variant Selection ---
    print("\n[7] Army composition variant selection")
    variant_counts: Dict[str, int] = {}
    for i in range(100):
        variant = service.evaluate("sc2.army.composition_variant", user_id=f"match_{i}")
        variant_counts[variant] = variant_counts.get(variant, 0) + 1
    for name, cnt in sorted(variant_counts.items()):
        print(f"    {name}: {cnt}/100 matches")

    # --- Overrides ---
    print("\n[8] Manual override demonstration")
    print(
        f"    Aggressive before override: {service.evaluate('sc2.strategy.aggressive_mode')}"
    )
    service.set_override("sc2.strategy.aggressive_mode", True, actor="admin")
    print(
        f"    Aggressive after override:  {service.evaluate('sc2.strategy.aggressive_mode')}"
    )
    service.clear_override("sc2.strategy.aggressive_mode", actor="admin")
    print(
        f"    Aggressive after clear:     {service.evaluate('sc2.strategy.aggressive_mode')}"
    )

    # --- Audit Trail ---
    print("\n[9] Audit trail (last 10 entries)")
    trail = service.get_audit_trail(limit=10)
    for entry in trail[-5:]:
        print(f"    [{entry['datetime']}] {entry['flag_name']}: {entry['action']}")

    # --- Flag Summary ---
    print("\n[10] Flag summary report")
    summary = service.get_flag_summary()
    print(f"    Total flags:   {summary['total']}")
    print(f"    Active:        {summary['active']}")
    print(f"    Overrides:     {summary['overrides']}")
    print(f"    Audit entries: {summary['audit_entries']}")

    # --- Evaluate All ---
    print("\n[11] Evaluate all flags for a specific context")
    all_vals = service.evaluate_all(user_id="bot_v2", game_loop=4000)
    for fname, fval in sorted(all_vals.items()):
        print(f"    {fname}: {fval}")

    print("\n" + "=" * 70)
    print("Phase 658 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 658: Feature Flags registered
