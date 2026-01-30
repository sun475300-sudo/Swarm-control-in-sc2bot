# -*- coding: utf-8 -*-
"""
Unit Production Module

유닛 생산 로직을 담당하는 모듈
"""

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    class UnitTypeId:
        ZERGLING = "ZERGLING"
        ROACH = "ROACH"
        HYDRALISK = "HYDRALISK"
        MUTALISK = "MUTALISK"
        ROACHWARREN = "ROACHWARREN"
        HYDRALISKDEN = "HYDRALISKDEN"
        SPIRE = "SPIRE"


async def safe_train(resilience, unit, unit_type, retry_count: int = 1):
    """
    안전한 유닛 생산 (에러 처리 포함)

    Args:
        resilience: ProductionResilience 인스턴스
        unit: 생산할 유닛 (larva 등)
        unit_type: 생산할 유닛 타입
        retry_count: 재시도 횟수

    Returns:
        bool: 생산 성공 여부
    """
    last_error = None

    for attempt in range(retry_count + 1):
        try:
            # Validate unit is still valid
            if not unit or not hasattr(unit, 'train'):
                print(f"[TRAIN_ERROR] Invalid unit for training {unit_type}")
                return False

            # Create train action and execute it via bot.do()
            action = unit.train(unit_type)
            resilience.bot.do(action)  # bot.do() is not async, just call it
            return True

        except Exception as e:
            last_error = e
            game_time = getattr(resilience.bot, "time", 0.0)

            # Always log errors (not just every 200 iterations)
            if attempt == retry_count:  # Final attempt failed
                print(f"[TRAIN_ERROR] [{int(game_time)}s] Failed to train {unit_type}: {e}")
            else:
                print(f"[TRAIN_WARN] [{int(game_time)}s] Retry {attempt + 1}/{retry_count} for {unit_type}: {e}")

    return False


async def produce_army_unit(resilience, larva, ignore_caps=False) -> bool:
    """
    현재 구성과 테크에 따라 군대 유닛 생산

    Args:
        resilience: ProductionResilience 인스턴스
        larva: 생산할 애벌레
        ignore_caps: True면 유닛 수 제한 무시

    Returns:
        bool: 생산 성공 여부
    """
    b = resilience.bot
    game_time = getattr(b, "time", 0)

    # Auto-ignore caps if very rich
    if b.minerals > 1500:
        ignore_caps = True

    # Get current unit counts
    zergling_count = b.units(UnitTypeId.ZERGLING).amount if hasattr(b, "units") else 0
    roach_count = b.units(UnitTypeId.ROACH).amount if hasattr(b, "units") else 0
    hydra_count = b.units(UnitTypeId.HYDRALISK).amount if hasattr(b, "units") else 0
    mutalisk_count = b.units(UnitTypeId.MUTALISK).amount if hasattr(b, "units") else 0

    # Check available tech
    has_roach_warren = b.structures(UnitTypeId.ROACHWARREN).ready.exists
    has_hydra_den = b.structures(UnitTypeId.HYDRALISKDEN).ready.exists
    has_spire = b.structures(UnitTypeId.SPIRE).ready.exists

    # === MINIMUM DEFENSE REQUIREMENT ===
    if not ignore_caps:
        # Always maintain minimum army for defense before teching/droning
        min_defense_met = True
        total_army_supply = (zergling_count * 0.5) + (roach_count * 2) + (hydra_count * 2) + (mutalisk_count * 2)

        if game_time >= 120 and game_time < 240:
            min_defense_met = zergling_count >= 6
        elif game_time >= 240 and game_time < 360:
            min_defense_met = zergling_count >= 8 or roach_count >= 4 or total_army_supply >= 8
        elif game_time >= 360:
            min_defense_met = total_army_supply >= 10

        # If minimum defense NOT met, prioritize army production
        if not min_defense_met:
            if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
                return await safe_train(resilience, larva, UnitTypeId.ZERGLING)
            return False  # Wait for resources

    # === COUNTER ENEMY COMPOSITION ===
    from local_training.production.counter_units import get_counter_unit
    enemy_units = getattr(b, "enemy_units", [])
    counter_unit = get_counter_unit(resilience, enemy_units, has_roach_warren, has_hydra_den, has_spire)

    if counter_unit and b.can_afford(counter_unit) and b.supply_left >= 2:
        return await safe_train(resilience, larva, counter_unit)

    # === Calculate Zergling cap based on game phase ===
    max_zerglings = 20
    if game_time > 300:
        max_zerglings = 30 if (has_roach_warren or has_hydra_den) else 50
    if game_time > 600:
        max_zerglings = 40 if has_spire else 60

    # If ignoring caps, set limit to infinity
    if ignore_caps:
        max_zerglings = 9999

    # Late game priority
    if game_time > 600 and has_spire:
         # Logic ...
         if has_hydra_den and b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
              return await safe_train(resilience, larva, UnitTypeId.HYDRALISK)

    # Mid game priority
    if game_time > 300:
         if has_hydra_den and b.can_afford(UnitTypeId.HYDRALISK) and b.supply_left >= 2:
              return await safe_train(resilience, larva, UnitTypeId.HYDRALISK)
         if has_roach_warren and b.can_afford(UnitTypeId.ROACH) and b.supply_left >= 2:
              return await safe_train(resilience, larva, UnitTypeId.ROACH)

    # Default / Early game: Zerglings
    if (zergling_count < max_zerglings or ignore_caps) and b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
        return await safe_train(resilience, larva, UnitTypeId.ZERGLING)

    # If ignore_caps is True and we failed to build tech units, DUMP into Zerglings anyway
    if ignore_caps and b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
         return await safe_train(resilience, larva, UnitTypeId.ZERGLING)

    return False


async def emergency_zergling_production(resilience, larvae) -> None:
    """
    긴급 저글링 생산

    Args:
        resilience: ProductionResilience 인스턴스
        larvae: 애벌레 리스트
    """
    b = resilience.bot

    # Cap zergling count based on game time
    game_time = getattr(b, "time", 0)
    zergling_count = b.units(UnitTypeId.ZERGLING).amount if hasattr(b, "units") else 0
    max_zerglings = 24 if game_time > 300 else 16

    if zergling_count >= max_zerglings:
        return

    # Emergency: spawn as many zerglings as possible
    for larva in larvae:
        if b.can_afford(UnitTypeId.ZERGLING) and b.supply_left >= 1:
            if zergling_count >= max_zerglings:
                break
            await safe_train(resilience, larva, UnitTypeId.ZERGLING)
            zergling_count += 2  # Each zergling production gives 2 units


async def balanced_production(resilience, larvae) -> None:
    """
    균형잡힌 유닛 생산

    Args:
        resilience: ProductionResilience 인스턴스
        larvae: 애벌레 리스트
    """
    b = resilience.bot

    # Production logic based on balancer
    if resilience.balancer:
        for larva in larvae:
            should_make_drones = resilience.balancer.should_make_drones()
            if should_make_drones:
                # Make drones (handled by economy manager)
                pass
            else:
                # Make army units
                await produce_army_unit(resilience, larva)
    else:
        # Fallback: emergency production
        await emergency_zergling_production(resilience, larvae)
