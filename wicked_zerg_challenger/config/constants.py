# -*- coding: utf-8 -*-
"""
Centralized constants — replaces magic numbers scattered across the codebase.
Import: from config.constants import EARLY_GAME_END_SECONDS, ...
"""

# ── Timing ───────────────────────────────────────────────────────────────────
EARLY_GAME_END_SECONDS: float = 180.0  # EarlyDefenseSystem active window
SPINE_BUILD_TIME: float = 120.0  # Spine Crawler construction start gate
ROACH_RUSH_TIMING: float = 360.0  # AttackController roach rush trigger (6 min)

# ── Defense thresholds ────────────────────────────────────────────────────────
ENEMY_DETECT_RADIUS: float = 20.0  # EarlyDefenseSystem base proximity alert
PROXY_DETECT_RADIUS: float = 40.0  # Proxy structure detection range
WORKER_DEFEND_RADIUS: float = 15.0  # Worker pull-back attack radius
BASE_THREAT_RADIUS: float = 12.0  # _has_active_base_threat() distance

# ── Unit counts ───────────────────────────────────────────────────────────────
PROXY_DEFENSE_WORKERS: int = 6  # Workers to pull vs proxy structure
MAX_WORKER_DEFENSE: int = 6  # Cap on defending workers
EMERGENCY_SPINE_COUNT: int = 2  # Spines to build in emergency
ROACH_RUSH_MIN_COUNT: int = 12  # Minimum roaches before rush

# ── Economy ───────────────────────────────────────────────────────────────────
SPINE_CRAWLER_COST: int = 100  # Minerals cost for Spine Crawler
ZERGLING_SPEED_GAS_COST: int = 100  # Gas required for ling speed research

# ── Build order ───────────────────────────────────────────────────────────────
BUILD_ORDER_END_TIME: float = 300.0  # Hard cutoff for build order execution (5 min)
MAX_STEP_RETRIES: int = 50  # Frames before skipping a build step (~2s)
EXPANSION_TIMING_TARGET: float = 60.0  # Target time (s) for natural expansion

# ── RL / Reward ───────────────────────────────────────────────────────────────
REWARD_NORM_SCALE: float = 5.0  # tanh normalization divisor for rewards
MIN_WIN_RATE_FOR_PROMOTION: float = 0.40  # Curriculum promotion win-rate floor
THREAT_CACHE_TTL: float = 0.5  # Seconds before re-computing base threat
