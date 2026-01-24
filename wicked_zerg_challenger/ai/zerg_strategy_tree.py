"""
저그 전략 행동 트리

행동 트리를 사용하여 저그 전략을 구조화합니다.
복잡한 if-else 로직을 명확한 트리 구조로 변환합니다.
"""

from .behavior_tree import (
    BehaviorTree,
    NodeStatus,
    create_condition,
    create_action,
    create_sequence,
    create_selector,
    Parallel,
)


# ==================== 조건 함수들 ====================

def is_early_game(bot) -> bool:
    """초반 게임 (3분 이내)"""
    return bot.time < 180


def is_mid_game(bot) -> bool:
    """중반 게임 (3-10분)"""
    return 180 <= bot.time < 600


def is_late_game(bot) -> bool:
    """후반 게임 (10분 이상)"""
    return bot.time >= 600


def has_lair(bot) -> bool:
    """레어 보유 여부"""
    from sc2.ids.unit_typeid import UnitTypeId
    return bot.structures(UnitTypeId.LAIR).exists or bot.structures(UnitTypeId.HIVE).exists


def has_hive(bot) -> bool:
    """하이브 보유 여부"""
    from sc2.ids.unit_typeid import UnitTypeId
    return bot.structures(UnitTypeId.HIVE).exists


def is_under_attack(bot) -> bool:
    """기지 공격 받는 중"""
    if not hasattr(bot, 'townhalls') or not bot.townhalls.exists:
        return False

    for base in bot.townhalls:
        nearby_enemies = bot.enemy_units.closer_than(15, base)
        if nearby_enemies.exists:
            return True
    return False


def has_air_threat(bot) -> bool:
    """공중 위협 존재"""
    if not hasattr(bot, 'strategy'):
        return False
    return hasattr(bot.strategy, 'air_threat_active') and bot.strategy.air_threat_active


def should_expand(bot) -> bool:
    """확장 필요 여부"""
    if not hasattr(bot, 'townhalls'):
        return False

    base_count = bot.townhalls.amount
    game_time = bot.time

    # 게임 시간 기반 확장 목표
    if game_time < 120 and base_count >= 2:  # 2분: 2베이스
        return False
    if game_time < 300 and base_count >= 3:  # 5분: 3베이스
        return False
    if game_time < 600 and base_count >= 4:  # 10분: 4베이스
        return False

    # 미네랄 충분하면 확장
    return bot.minerals >= 300 and not bot.already_pending(bot.townhalls.first.type_id)


def has_army_advantage(bot) -> bool:
    """병력 우위"""
    if not hasattr(bot, 'units'):
        return False

    our_army_supply = sum(u.supply_cost for u in bot.units if not u.is_worker)
    enemy_supply = getattr(bot, 'enemy_army_supply', 0)

    return our_army_supply >= enemy_supply * 1.2


def enemy_structures_low(bot) -> bool:
    """적 건물 적음 (10개 이하)"""
    enemy_structures = getattr(bot, 'enemy_structures', [])
    return len(enemy_structures) <= 10


# ==================== 액션 함수들 ====================

async def defend_bases(bot) -> NodeStatus:
    """기지 방어"""
    try:
        if hasattr(bot, 'combat'):
            await bot.combat.defend_bases()
        return NodeStatus.SUCCESS
    except Exception:
        return NodeStatus.FAILURE


async def build_expansion(bot) -> NodeStatus:
    """확장 기지 건설"""
    try:
        if hasattr(bot, 'economy'):
            from sc2.ids.unit_typeid import UnitTypeId
            if bot.can_afford(UnitTypeId.HATCHERY):
                location = await bot.get_next_expansion()
                if location:
                    worker = bot.workers.random
                    if worker:
                        worker.build(UnitTypeId.HATCHERY, location)
                        return NodeStatus.SUCCESS
        return NodeStatus.FAILURE
    except Exception:
        return NodeStatus.FAILURE


async def produce_workers(bot) -> NodeStatus:
    """일꾼 생산"""
    try:
        if hasattr(bot, 'economy'):
            await bot.economy.on_step(bot.iteration)
        return NodeStatus.SUCCESS
    except Exception:
        return NodeStatus.FAILURE


async def build_army(bot) -> NodeStatus:
    """군대 생산"""
    try:
        if hasattr(bot, 'unit_factory'):
            await bot.unit_factory.on_step(bot.iteration)
        return NodeStatus.SUCCESS
    except Exception:
        return NodeStatus.FAILURE


async def scout_enemy(bot) -> NodeStatus:
    """정찰 실행"""
    try:
        if hasattr(bot, 'scouting'):
            await bot.scouting.on_step(bot.iteration)
        return NodeStatus.SUCCESS
    except Exception:
        return NodeStatus.FAILURE


async def upgrade_tech(bot) -> NodeStatus:
    """업그레이드 연구"""
    try:
        if hasattr(bot, 'upgrade_manager'):
            await bot.upgrade_manager.on_step(bot.iteration)
        return NodeStatus.SUCCESS
    except Exception:
        return NodeStatus.FAILURE


async def spread_creep(bot) -> NodeStatus:
    """점막 확산"""
    try:
        if hasattr(bot, 'queen_manager'):
            await bot.queen_manager.on_step(bot.iteration)
        return NodeStatus.SUCCESS
    except Exception:
        return NodeStatus.FAILURE


async def counter_air(bot) -> NodeStatus:
    """공중 대응"""
    try:
        if hasattr(bot, 'strategy'):
            await bot.strategy._handle_air_threat()
        return NodeStatus.SUCCESS
    except Exception:
        return NodeStatus.FAILURE


async def victory_push(bot) -> NodeStatus:
    """승리 푸시"""
    try:
        if hasattr(bot, 'combat'):
            await bot.combat._execute_victory_push(bot.iteration)
        return NodeStatus.SUCCESS
    except Exception:
        return NodeStatus.FAILURE


async def standard_attack(bot) -> NodeStatus:
    """표준 공격"""
    try:
        if hasattr(bot, 'combat'):
            await bot.combat.on_step(bot.iteration)
        return NodeStatus.SUCCESS
    except Exception:
        return NodeStatus.FAILURE


# ==================== 행동 트리 구축 ====================

def create_zerg_behavior_tree() -> BehaviorTree:
    """
    저그 전략 행동 트리 생성

    트리 구조:
    Root (Selector)
    ├─ 긴급 상황 처리 (Sequence)
    │  ├─ is_under_attack?
    │  └─ defend_bases
    ├─ 초반 전략 (Sequence)
    │  ├─ is_early_game?
    │  └─ 초반 액션 (Parallel)
    │     ├─ produce_workers
    │     ├─ scout_enemy
    │     └─ build_expansion
    ├─ 중반 전략 (Sequence)
    │  ├─ is_mid_game?
    │  └─ 중반 액션 (Parallel)
    │     ├─ build_army
    │     ├─ spread_creep
    │     ├─ upgrade_tech
    │     └─ 공중 대응 (Sequence)
    │        ├─ has_air_threat?
    │        └─ counter_air
    └─ 후반 전략 (Sequence)
       ├─ is_late_game?
       └─ 후반 액션 (Selector)
          ├─ 승리 푸시 (Sequence)
          │  ├─ enemy_structures_low?
          │  ├─ has_army_advantage?
          │  └─ victory_push
          └─ standard_attack
    """

    # === 긴급 상황 처리 ===
    emergency_defense = create_sequence(
        "긴급 방어",
        create_condition("기지 공격 중?", is_under_attack),
        create_action("기지 방어", defend_bases)
    )

    # === 초반 전략 (병렬 실행) ===
    early_actions = Parallel(
        "초반 액션",
        [
            create_action("일꾼 생산", produce_workers),
            create_action("정찰", scout_enemy),
            create_sequence(
                "확장 건설",
                create_condition("확장 필요?", should_expand),
                create_action("확장 짓기", build_expansion)
            ),
        ],
        success_threshold=2  # 2개 이상 성공하면 SUCCESS
    )

    early_strategy = create_sequence(
        "초반 전략",
        create_condition("초반?", is_early_game),
        early_actions
    )

    # === 중반 전략 (병렬 실행) ===
    air_defense = create_sequence(
        "공중 대응",
        create_condition("공중 위협?", has_air_threat),
        create_action("공중 카운터", counter_air)
    )

    mid_actions = Parallel(
        "중반 액션",
        [
            create_action("군대 생산", build_army),
            create_action("점막 확산", spread_creep),
            create_action("업그레이드", upgrade_tech),
            air_defense,
        ],
        success_threshold=3  # 3개 이상 성공하면 SUCCESS
    )

    mid_strategy = create_sequence(
        "중반 전략",
        create_condition("중반?", is_mid_game),
        mid_actions
    )

    # === 후반 전략 ===
    victory_push_sequence = create_sequence(
        "승리 푸시",
        create_condition("적 건물 적음?", enemy_structures_low),
        create_condition("병력 우위?", has_army_advantage),
        create_action("승리 공격", victory_push)
    )

    late_actions = create_selector(
        "후반 액션",
        victory_push_sequence,
        create_action("표준 공격", standard_attack)
    )

    late_strategy = create_sequence(
        "후반 전략",
        create_condition("후반?", is_late_game),
        late_actions
    )

    # === 루트 노드 (우선순위 순) ===
    root = create_selector(
        "저그 전략 루트",
        emergency_defense,  # 1순위: 긴급 방어
        late_strategy,      # 2순위: 후반 전략
        mid_strategy,       # 3순위: 중반 전략
        early_strategy,     # 4순위: 초반 전략
    )

    return BehaviorTree("ZergStrategyTree", root)


# ==================== 사용 예시 ====================

async def execute_strategy(bot) -> None:
    """
    행동 트리를 사용하여 전략 실행

    Usage:
        # 봇 클래스에서
        self.strategy_tree = create_zerg_behavior_tree()

        # on_step에서
        await execute_strategy(self)
    """
    if not hasattr(bot, 'strategy_tree'):
        bot.strategy_tree = create_zerg_behavior_tree()

    status = await bot.strategy_tree.tick(bot)

    # 디버그 로그 (옵션)
    if bot.iteration % 220 == 0:  # 10초마다
        print(f"[BEHAVIOR TREE] Status: {status.value}")
