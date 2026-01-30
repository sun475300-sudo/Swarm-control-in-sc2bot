# -*- coding: utf-8 -*-
"""
Expansion Manager Module

확장 관련 로직을 담당하는 모듈
"""

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        HATCHERY = "HATCHERY"


def can_expand_safely(resilience) -> tuple:
    """
    안전하게 확장 가능한지 확인

    Args:
        resilience: ProductionResilience 인스턴스

    Returns:
        tuple: (가능 여부, 차단 사유)
    """
    b = resilience.bot
    intel = getattr(b, "intel", None)
    under_attack = False
    enemy_near_base = False

    if intel and hasattr(intel, "is_under_attack"):
        under_attack = bool(intel.is_under_attack())
    if not under_attack and hasattr(b, "enemy_units") and b.enemy_units:
        if b.townhalls.exists:
            base = b.townhalls.first
            threshold = resilience.enemy_near_base_distance * resilience.enemy_near_base_scale
            enemy_near_base = any(e.distance_to(base.position) < threshold for e in b.enemy_units)

    # AGGRESSIVE EXPANSION: If minerals > 300, bypass most safety checks
    # Especially if we don't have a natural expansion yet (bases < 2)
    bases = b.townhalls.amount if hasattr(b, "townhalls") else 1
    aggressive_expand = b.minerals >= 300 or (bases < 2 and b.minerals >= 200)

    # Critical: Bypass enemy check if it's just 1-2 units (likely scouts)
    if enemy_near_base and not under_attack:
        enemy_count = sum(1 for e in b.enemy_units if e.distance_to(b.townhalls.first.position) < 30)
        if enemy_count <= 2:
            enemy_near_base = False  # Ignore scouts

    if under_attack and not aggressive_expand:
        return False, "under_attack"
    if enemy_near_base and not aggressive_expand:
        return False, "enemy_near_base"

    # Relax army requirement - Zerg needs expansions for macro
    supply_army = getattr(b, "supply_army", 0)

    # 2026-01-25 FIX: Weak Defense (Issue 2)
    # Verify army presence before taking 3rd base (bases >= 2)
    # Aggressive expand ignores this ONLY if we are rich (>800 mins)
    req_army = resilience.min_army_supply
    if bases >= 2:
         # If aggressive but poor army, BLOCK expansion to force army production
         if aggressive_expand and b.minerals < 800 and supply_army < 6:
              return False, f"danger_no_army ({supply_army}/6)"

         if not aggressive_expand and supply_army < req_army and b.time > resilience.min_army_time:
              return False, f"low_army ({supply_army}/{req_army})"

    # Relax drone requirement when banking minerals
    drones = b.workers.amount if hasattr(b, "workers") else 0

    # 2026-01-25 FIX: Enforce saturation even for aggressive expansion (Issue 1)
    # Exception: Huge bank (>1000) allows expanding to burn minerals
    min_drones_limit = resilience.min_drones_per_base  # Default 14-16
    if aggressive_expand:
         if b.minerals > 1000:
             min_drones_limit = 0 # Ignore limit if rich
         else:
             min_drones_limit = 12 # Minimum functional saturation

    if drones < bases * min_drones_limit:
        return False, f"low_drones ({drones}/{bases*min_drones_limit})"

    # Reduce cooldown when banking minerals
    now = getattr(b, "time", 0.0)
    # If no natural, almost zero cooldown
    effective_cooldown = 10.0 if bases < 2 else (resilience.expansion_retry_cooldown / 2 if aggressive_expand else resilience.expansion_retry_cooldown)
    if now - resilience.last_expansion_attempt < effective_cooldown:
        return False, "cooldown"

    return True, ""


async def try_expand(resilience) -> bool:
    """
    확장 시도

    Args:
        resilience: ProductionResilience 인스턴스

    Returns:
        bool: 확장 성공 여부
    """
    b = resilience.bot
    if not b.can_afford(UnitTypeId.HATCHERY):
        log_expand_block(resilience, "insufficient_resources")
        return False
    if b.already_pending(UnitTypeId.HATCHERY) > 0:
        log_expand_block(resilience, "pending_hatchery")
        return False
    can_expand, reason = can_expand_safely(resilience)
    if not can_expand:
        log_expand_block(resilience, reason)
        return False

    resilience.last_expansion_attempt = getattr(b, "time", 0.0)

    # Prefer expand_now or get_next_expansion
    try:
        if hasattr(b, "expand_now"):
            await b.expand_now()
            return True
        if hasattr(b, "get_next_expansion"):
            next_pos = await b.get_next_expansion()
            if next_pos:
                await b.build(UnitTypeId.HATCHERY, near=next_pos)
                return True
    except Exception:
        return False

    return False


def log_expand_block(resilience, reason: str) -> None:
    """
    확장 차단 로그 출력

    Args:
        resilience: ProductionResilience 인스턴스
        reason: 차단 사유
    """
    now = getattr(resilience.bot, "time", 0.0)
    if now - resilience.last_expand_log_time < 15.0:
        return
    resilience.last_expand_log_time = now
    if reason:
        print(f"[EXPAND BLOCK] {reason} at {int(now)}s")


def cleanup_build_reservations(resilience) -> None:
    """
    오래된 건물 예약 정리

    Args:
        resilience: ProductionResilience 인스턴스
    """
    try:
        reservations = getattr(resilience.bot, "build_reservations", {})
        now = getattr(resilience.bot, "time", 0.0)
        stale = [sid for sid, ts in reservations.items() if now - ts > 45.0]
        for sid in stale:
            reservations.pop(sid, None)
    except Exception:
        pass
