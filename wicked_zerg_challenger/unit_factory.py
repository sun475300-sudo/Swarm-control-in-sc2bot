#!/usr/bin/env python3
import logging

logger = logging.getLogger("UnitFactory")
# -*- coding: utf-8 -*-
"""
Unit factory - larva production with gas reservation logic.

Keeps gas-heavy units from being starved by mineral-only spam.
"""

from typing import List, Optional

try:
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:  # Fallbacks for tooling environments
    UnitTypeId = None


class UnitFactory:
    def __init__(self, bot, blackboard=None, config=None):
        """
        UnitFactory - Blackboard ???? ?類????

        Args:
            bot: SC2 Bot ?嶺뚮ㅎ?ц짆???⑤８痢?
            blackboard: GameStateBlackboard ?嶺뚮ㅎ?ц짆???⑤８痢?(Optional)
            config: GameConfig ?嶺뚮ㅎ?ц짆???⑤８痢?(Optional)
        """
        self.bot = bot
        self.blackboard = blackboard
        self.config = config

        # Config ??れ삀??뫢????源놁젳 (fallback to defaults)
        if config:
            self.min_gas_reserve = config.MIN_GAS_RESERVE
            self.larva_pressure_threshold = config.LARVA_PRESSURE_THRESHOLD
        else:
            self.min_gas_reserve = 50
            self.larva_pressure_threshold = 6

        self.min_mineral_reserve_for_gas = 150
        self.gas_unit_ratio_target = 0.50  # * BALANCED: 0.60 -> 0.50 (??筌먦끉?????Β?띾쭡) *
        self.larva_gas_ratio = 0.45  # * BALANCED: 0.6 -> 0.45 (雅?퍔瑗띰㎖?덈빝?????ル늅筌?55%) *
        self.max_larva_spend_per_step = 5

        # * COMBAT REINFORCEMENT SYSTEM *
        # ??ш낄援??濚??怨뚮옖筌???野껊챶爾?????ш낄援η뵳???筌?痢??        self._combat_mode = False
        self._combat_mode = False
        self._last_combat_check = 0
        self._combat_check_interval = 22  # ~1?縕?袁?맪??癲ル슪???띿물?
        self._combat_larva_spend = 5  # ??ш낄援??濚???癲ル슢??? ???⑥ロ떋 ?????(3 -> 5)

        # ???ろ꼥???꾨룱???좊읈??????ル늅筌??????- * RE-BALANCED: ??筌먦끉????獄쏅똾???怨뚮옖???*
        self.race_gas_ratios = {
            "Terran": 0.50,  # * BALANCED: 0.65 -> 0.50 (雅?퍔瑗띰㎖?덈빝?????? ?嶺뚮㉡?€쾮? *
            "Protoss": 0.55,  # * BALANCED: 0.70 -> 0.55 (??筌먦끉?????Β?띾쭡) *
            "Zerg": 0.45,  # * BALANCED: 0.55 -> 0.45 *
            "Unknown": 0.50,  # * BALANCED: 0.60 -> 0.50 *
        }

    def _should_save_larva(self) -> bool:
        """
        Rogue Tactics?????⑥ロ떋 ?嶺뚮ㅎ?닻??癲ル슢?꾤땟????嶺뚮Ĳ?됮?

        癲ル슢??첎???釉랁돯???筌먦끇??????ш끽維?????ш낄援?????⑥ロ떋????ш낄猷쀨린????嚥▲꺂痢롳┼??넊? 癲ル슪???띿물??筌뤾퍓???

        Returns:
            ???⑥ロ떋????ш낄猷쀨린????嚥???True
        """
        # Strategy Manager 癲ル슪???띿물?
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and hasattr(strategy, "should_save_larva"):
            if strategy.should_save_larva():
                return True

        # Rogue Tactics Manager 癲ル슣????癲ル슪???띿물?
        rogue = getattr(self.bot, "rogue_tactics", None)
        if rogue:
            if getattr(rogue, "larva_saving_active", False):
                return True
            if getattr(rogue, "preparing_baneling_drop", False):
                return True

        return False

    def _update_gas_ratio_target(self) -> None:
        """
        ??? ???ろ꼥??????ㅻ깹????좊읈??????ル늅筌??????????깆뱾 ?釉뚰???
        """
        # Strategy Manager????????ろ꼥???嶺뚮㉡?€쾮???좊읈??嶺뚮ㅎ?닸쾮濡㏓섀?        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy:
            race = getattr(strategy, "detected_enemy_race", None)
            if race:
                race_name = race.value if hasattr(race, "value") else str(race)
                self.gas_unit_ratio_target = self.race_gas_ratios.get(
                    race_name, self.race_gas_ratios["Unknown"]
                )
                return

        # 癲ル슣???????ろ꼥???嶺뚮Ĳ?됮?
        enemy_race = getattr(self.bot, "enemy_race", None)
        if enemy_race:
            race_str = str(enemy_race)
            for race_name in self.race_gas_ratios:
                if race_name in race_str:
                    self.gas_unit_ratio_target = self.race_gas_ratios[race_name]
                    return

    def _is_emergency_mode(self) -> bool:
        """Emergency Mode ?嶺뚮Ĳ?됮?- ??筌먦끉?????????굿? ???Β?띾쭡"""
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy:
            return getattr(strategy, "emergency_active", False)
        return False

    def _has_serious_base_threat(self, min_enemies: int = 4) -> bool:
        enemy_units = getattr(self.bot, "enemy_units", None)
        townhalls = getattr(self.bot, "townhalls", None)
        if enemy_units is None or townhalls is None:
            return False

        ready = getattr(townhalls, "ready", townhalls)
        try:
            bases = list(ready)
        except TypeError:
            try:
                bases = list(townhalls)
            except TypeError:
                first_base = getattr(townhalls, "first", None)
                bases = [first_base] if first_base else []

        for base in bases:
            if not base:
                continue
            try:
                nearby = enemy_units.closer_than(30, base)
            except Exception:
                continue
            amount = getattr(nearby, "amount", None)
            if amount is None:
                try:
                    amount = len(nearby)
                except TypeError:
                    amount = 0
            try:
                if int(amount or 0) >= min_enemies:
                    return True
            except (TypeError, ValueError):
                continue

        return False

    def _check_combat_mode(self, iteration: int) -> bool:
        """
        ??ш낄援??癲ル슢?꾤땟????嶺뚮Ĳ?됮?- ??ш낄援??濚욌꼬?댄꺍??ル쵐異??怨뚮옖筌???野껊챶爾??癲ル슢?꾤땟?????筌????
        Returns:
            True if in combat mode (need reinforcement)
        """
        if iteration - self._last_combat_check < self._combat_check_interval:
            return self._combat_mode

        self._last_combat_check = iteration
        in_combat = False

        # ??ш낄援????좊즴?? ?釉뚰???쨨??        in_combat = False

        # 1. Strategy Manager??emergency_active 癲ル슪???띿물?
        strategy = getattr(self.bot, "strategy_manager", None)
        if strategy and getattr(strategy, "emergency_active", False):
            in_combat = True

        # 2. ?????ル늅筌????れ삀?? ?????뗫쐩??????덉툗癲ル슣?? 癲ル슪???띿물?
        if (
            not in_combat
            and hasattr(self.bot, "enemy_units")
            and hasattr(self.bot, "townhalls")
        ):
            enemy_units = self.bot.enemy_units
            for th in self.bot.townhalls:
                nearby_enemies = [
                    e for e in enemy_units if e.distance_to(th.position) < 35
                ]
                if len(nearby_enemies) >= 3:  # 3?????⑤?彛?????ㅼ굣???????뗫쐩??                    in_combat = True
                    in_combat = True
                    break

        # 3. ??ш낄猷???怨뚮옖筌???????癲ル슪???띿물?(?????뭇??繹먮끏????ヂ?筌???
        if not in_combat and hasattr(self.bot, "supply_army"):
            supply_army = self.bot.supply_army
            if not hasattr(self, "_last_supply_army"):
                self._last_supply_army = supply_army
            else:
                supply_loss = self._last_supply_army - supply_army
                if supply_loss > 10:  # 10 ?????뭇??繹먮끏?????⑤?彛??????
                    in_combat = True
                self._last_supply_army = supply_army

        self._combat_mode = in_combat
        return in_combat

    async def on_step(self, iteration: int) -> None:
        if not (UnitTypeId and hasattr(self.bot, "larva") and self.bot.larva):
            # ???⑥ロ떋??좊읈? ???⑤챶?뺧┼????????⑤챶苡?
            return

        # * CRITICAL FIX: ???????3癲ル슢議????嶺뚮㉡?€쾮????ш낄援η뵳???????怨뚮옖???(?嶺뚮Ĳ??????Β?띾쭡) *
        # ???ル늅筌???獄쏅똾????嶺뚮Ĳ?????袁⑸젻泳?떘???? ????녳뵣????좊즴甕??????モ뵲
        townhalls = self.bot.townhalls
        base_count = townhalls.amount
        game_time = self.bot.time
        pending_hatch = self.bot.already_pending(UnitTypeId.HATCHERY)

        # 1. ???????癲ル슪???띿물?(1??癲ル슣???????1?類?ｄ펺????醫딅뱠 ??????嶺뚮ㅎ?닻??
        # ?? ???? ???⑤챸諭??癲꾧퀗????빝?濚욌꼬?댄꺍??ル쵐異?pending) ?嶺뚮ㅎ?닻???????????        pending_hatch = self.bot.already_pending(UnitTypeId.HATCHERY)

        # * FIX: ??ш낄援??濚욌꼬?댄꺍????嶺뚮Ĳ???????れ삀????壤? ???怨룹쓱 (??獄쎼뀙?????Β?띾쭡) *
        strategy = getattr(self.bot, "strategy_manager", None)
        under_attack = self._has_serious_base_threat()
        if strategy:
            strategic_alert = getattr(strategy, "emergency_active", False) or getattr(
                strategy, "defense_active", False
            )
            under_attack = under_attack or (
                strategic_alert and self._has_serious_base_threat()
            )

        # Expansion reserve should not starve army production.
        # Only pause larva spending while enough combat units exist, and only
        # inside a bounded timing window for each expansion.
        combat_count = self._count_combat_units()
        if (
            base_count < 2
            and game_time > 60
            and game_time < 240
            and pending_hatch == 0
            and not under_attack
            and combat_count >= 8
            and 200 <= self.bot.minerals < 350
        ):
            if iteration % 100 == 0:
                logger.info(
                    f"Saving minerals for Natural Expansion (Time: {int(game_time)}s), Minerals: {self.bot.minerals}"
                )
            return

        if (
            base_count < 3
            and game_time > 190
            and game_time < 360
            and pending_hatch == 0
            and not under_attack
            and combat_count >= 14
            and 200 <= self.bot.minerals < 350
        ):
            if iteration % 100 == 0:
                logger.info(
                    f"Saving minerals for 3rd Base (Time: {int(game_time)}s), Minerals: {self.bot.minerals}"
                )
            return

        supply_left = getattr(self.bot, "supply_left", 0)
        if (
            base_count < 4
            and game_time > 280
            and game_time < 480
            and pending_hatch == 0
            and not under_attack
            and combat_count >= 24
            and 50 <= self.bot.minerals < 350
            and supply_left > 2
        ):
            if iteration % 100 == 0:
                logger.info(
                    f"Saving minerals for 4th Base (Time: {int(game_time)}s), Minerals: {self.bot.minerals}"
                )
            return

        larva = self.bot.larva
        if not larva:
            return

        if hasattr(self.bot, "supply_left") and self.bot.supply_left <= 0:
            return

        # *** FIX: ????????곷츉?棺??짆?삠궘???獄쏅똾??(supply_left < 4 ????좊즴甕?? ***
        # ?????뭇??繹먮끏????怨????袁⑸젻泳?: 雅?퍔瑗띰㎖??????곷츉?棺??짆?삠궘???獄쏅똾??
        if hasattr(self.bot, "supply_left") and self.bot.supply_left < 4:
            # ???? ??獄쏅똾??濚욌꼬?댄꺍??????곷츉?棺??짆?삠궘?癲ル슪???띿물?
            pending_overlords = self.bot.already_pending(UnitTypeId.OVERLORD)
            if pending_overlords == 0 and self.bot.can_afford(UnitTypeId.OVERLORD):
                # Blackboard ????: ????곷츉?棺??짆?삠궘???ヂ??????釉먯뒜??
                if self.blackboard:
                    self.blackboard.request_production(
                        unit_type=UnitTypeId.OVERLORD,
                        count=1,
                        requester="UnitFactory",
                        priority=0,  # URGENT
                    )
                    if iteration % 100 == 0:
                        logger.info(
                            f"[*] Preemptive Overlord (supply_left={self.bot.supply_left}) [*]"
                        )
                else:
                    # Fallback: 癲ル슣??????獄쏅똾??
                    try:
                        if larva:
                            if hasattr(self.bot, "production") and self.bot.production:
                                await self.bot.production._safe_train(
                                    larva.first, UnitTypeId.OVERLORD
                                )
                            else:
                                self.bot.do(larva.first.train(UnitTypeId.OVERLORD))
                            if iteration % 100 == 0:
                                logger.info(
                                    f"[*] Preemptive Overlord (supply_left={self.bot.supply_left}) [*]"
                                )
                    except Exception:
                        pass

        # * COMBAT REINFORCEMENT: ??ш낄援??癲ル슢?꾤땟???癲ル슪???띿물?*
        in_combat = self._check_combat_mode(iteration)

        # ??ш낄援??濚욌꼬?댄꺍??ル쵐異???癲ル슢??? ???⑥ロ떋 ?????
        if in_combat:
            self.max_larva_spend_per_step = self._combat_larva_spend
            if iteration % 50 == 0:
                game_time = getattr(self.bot, "time", 0)
                logger.info(
                    f"[{int(game_time)}s] COMBAT MODE: Increased production rate"
                )
        else:
            self.max_larva_spend_per_step = 3  # ??れ삀???筌?
        # === StrategyManager ???怨뺣빰??????????ㅻ쿋筌?(via Blackboard or Direct) ===
        # 癲?????읐?壤???덊렡 ??ш끽維??癲ル슢?????????좊읈???????????좊읈??嶺??????ㅼ굣??
        strategy_mode = "NORMAL"
        emergency_active = False

        # 1. Try Blackboard first
        if self.blackboard:
            strategy_mode = self.blackboard.get("strategy_mode", "NORMAL")
            emergency_active = self.blackboard.get("is_rush_detected", False)

        # 2. Fallback to direct access if Blackboard missing (Backward Compat)
        elif hasattr(self.bot, "strategy_manager") and self.bot.strategy_manager:
            strategy = self.bot.strategy_manager
            strategy_mode = getattr(strategy, "current_mode", "NORMAL")
            # emergency_active handled below

        strategy = getattr(
            self.bot, "strategy_manager", None
        )  # Still needed for get_unit_ratios until that is moved to Blackboard
        if strategy:
            if emergency_active or getattr(strategy, "emergency_active", False):
                self.gas_unit_ratio_target = 0.15
            else:
                protoss_threat_boost = self._check_protoss_threat_boost()
                if protoss_threat_boost:
                    self.gas_unit_ratio_target = 0.55
                else:
                    ratios = strategy.get_unit_ratios()
                    if ratios:
                        gas_ratio = (
                            ratios.get("hydra", 0)
                            + ratios.get("hydralisk", 0)
                            + ratios.get("mutalisk", 0)
                            + ratios.get("roach", 0)
                            + ratios.get("ravager", 0)
                            + ratios.get("corruptor", 0)
                        )
                        if gas_ratio > 0:
                            self.gas_unit_ratio_target = min(gas_ratio, 0.60)
                        if iteration % 100 == 0:
                            race = getattr(strategy, "detected_enemy_race", None)
                            race_name = race.value if hasattr(race, "value") else str(race)
                            logger.info(
                                f"vs {race_name}: gas_ratio_target = {self.gas_unit_ratio_target:.2f}"
                            )

        # Rogue Tactics ???⑥ロ떋 ?嶺뚮ㅎ?닻??癲ル슪???띿물?
        if self._should_save_larva():
            # ???⑥ロ떋 ?嶺뚮ㅎ?닻??癲ル슢?꾤땟??? 癲ル슔?됭짆?????⑥ロ떋癲?????(????곷츉?棺??짆?삠궘?????ш끽維?????ル늅筌묐?異?
            if iteration % 100 == 0:
                logger.info("Larva saving mode - minimal production")
            # ????곷츉?棺??짆?삠궘?諭苡? ??ш끽維???嚥?????獄쏅똾?? ??ш끽維??씤異????袁⑤툞
            if self.bot.supply_left < 2 and self.bot.can_afford(UnitTypeId.OVERLORD):
                if self.blackboard:
                    self.blackboard.request_production(
                        unit_type=UnitTypeId.OVERLORD,
                        count=1,
                        requester="UnitFactory",
                        priority=0,  # URGENT
                    )
                else:
                    # Fallback: 癲ル슣??????獄쏅똾??
                    try:
                        if hasattr(self.bot, "production") and self.bot.production:
                            await self.bot.production._safe_train(
                                larva.first, UnitTypeId.OVERLORD
                            )
                        else:
                            self.bot.do(larva.first.train(UnitTypeId.OVERLORD))
                    except Exception:
                        pass
            return

        # ???ろ꼥???꾨룱???좊읈????????????녿ぅ??熬곣뫀肄?(StrategyManager ???⑤챶援???fallback)
        if not strategy:
            self._update_gas_ratio_target()

        minerals = getattr(self.bot, "minerals", 0)
        vespene = getattr(self.bot, "vespene", 0)
        if vespene > max(300, minerals * 3) and minerals < 500:
            self.gas_unit_ratio_target = min(self.gas_unit_ratio_target, 0.25)
        gas_units = self._count_gas_units()
        total_units = max(1, self._count_combat_units())
        gas_ratio = gas_units / total_units
        can_spend_gas = vespene >= self.min_gas_reserve

        # *** IMPROVED: ???용봿????源낇꼧?????Β?띾쭡??筌믨퀡彛??釉뚰??ｃ뀋?(????????怨좊뭿 ??筌?痢?? ***
        # StrictUpgradePriority??좊읈? ??좊읈???? ???怨좊뭿???源끹걬癲????ル늅筌???獄쏅똾??????モ뵲
        if hasattr(self.bot, "upgrade_priority") and self.bot.upgrade_priority:
            available_gas = self.bot.upgrade_priority.get_available_gas()
            can_spend_gas = can_spend_gas and available_gas >= self.min_gas_reserve
        queue = self._build_priority_queue(
            minerals=minerals,
            vespene=vespene,
            gas_ratio=gas_ratio,
            gas_units=gas_units,
            larva_count=len(larva),
            can_spend_gas=can_spend_gas,
        )

        # *** Blackboard ????: ???Β?띾쭡??筌믨퀡彛???? Blackboard????釉먯뒜????⑥???濚밸Ŧ援욃ㅇ?***
        if self.blackboard:
            to_request = min(self.max_larva_spend_per_step, len(larva))

            # ???Β?띾쭡??筌믨퀡彛??????????ル늅筌???????ヂ嚥?肉???숆강筌?쓣爾??            unit_requests = {}
            for _ in range(to_request):
                unit_type = self._pick_unit(queue)
                if not unit_type:
                    break
                unit_requests[unit_type] = unit_requests.get(unit_type, 0) + 1

            # Blackboard????獄쏅똾????釉먯뒜???濚밸Ŧ援욃ㅇ?
            for unit_type, count in unit_requests.items():
                # ??ш낄援??癲ル슢?꾤땟????쎾퐲????Β?띾쭡??筌믨퀡彛??亦껋꼨援?굢?(MEDIUM -> HIGH)
                priority = 1 if in_combat else 2
                self.blackboard.request_production(
                    unit_type=unit_type,
                    count=count,
                    requester="UnitFactory",
                    priority=priority,
                )

            # ??釉먮폏?遺룹쐺??棺??짆??
            if iteration % 50 == 0 and unit_requests:
                logger.info(f"Production requested: {unit_requests}")

        else:
            # Fallback: ProductionController????ш끽維쀨굢?(???????獄쏅똾???袁⑸젻泳???濚욌꼬?댄꺇????癰귙끋源?
            prod_ctrl = getattr(self.bot, "production_controller", None)
            to_spend = 0
            for larva_unit in larva:
                if to_spend >= self.max_larva_spend_per_step:
                    break

                unit_type = self._pick_unit(queue)
                if not unit_type:
                    break

                try:
                    if prod_ctrl and hasattr(prod_ctrl, "request_unit"):
                        prod_ctrl.request_unit(unit_type, requester="UnitFactory")
                    elif hasattr(self.bot, "production") and self.bot.production:
                        await self.bot.production._safe_train(larva_unit, unit_type)
                    else:
                        self.bot.do(larva_unit.train(unit_type))
                    to_spend += 1
                except Exception:
                    continue

    def _pick_unit(self, queue: List[object]) -> Optional[object]:
        for unit_type in queue:
            if self._can_train(unit_type):
                return unit_type
        return None

    def _can_train(self, unit_type) -> bool:
        if not self.bot.can_afford(unit_type):
            return False
        if not self._requirements_met(unit_type):
            return False
        return True

    def _requirements_met(self, unit_type) -> bool:
        if not hasattr(self.bot, "structures"):
            return True

        requirements = {
            UnitTypeId.ZERGLING: UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.BANELING: UnitTypeId.BANELINGNEST,
            UnitTypeId.ROACH: UnitTypeId.ROACHWARREN,
            UnitTypeId.RAVAGER: UnitTypeId.ROACHWARREN,
            UnitTypeId.HYDRALISK: UnitTypeId.HYDRALISKDEN,
            UnitTypeId.LURKERMP: UnitTypeId.LURKERDENMP,
        }
        required = requirements.get(unit_type)
        if not required:
            return True

        structures = self.bot.structures(required)
        return bool(structures and structures.ready)

    def _build_priority_queue(
        self,
        minerals: int,
        vespene: int,
        gas_ratio: float,
        gas_units: int,
        larva_count: int,
        can_spend_gas: bool,
    ) -> List[object]:
        force_hydra = getattr(self, "_force_hydra", False)
        if force_hydra:
            if self._requirements_met(UnitTypeId.HYDRALISK) and vespene >= 50:
                hydra_count = self._count_unit_type(UnitTypeId.HYDRALISK)
                if hydra_count < 15:
                    return [UnitTypeId.HYDRALISK, UnitTypeId.ROACH, UnitTypeId.ZERGLING]

        gas_priority = can_spend_gas and gas_ratio < self.gas_unit_ratio_target
        larva_gas_target = max(1, int(larva_count * self.larva_gas_ratio))
        gas_shortfall = gas_units < larva_gas_target
        mineral_guard = minerals < self.min_mineral_reserve_for_gas

        allow_mineral_mix = not (gas_priority and (gas_shortfall or mineral_guard))
        if gas_priority and larva_count >= self.larva_pressure_threshold:
            allow_mineral_mix = (
                allow_mineral_mix or minerals >= self.min_mineral_reserve_for_gas * 2
            )

        queue: List[object] = []

        # * Strategy Manager????????살쓴勇???ш낄援?뤃???좊즴????????뉖뜤?????Β?띾쭡 *
        strategy = getattr(self.bot, "strategy_manager", None)
        if (
            strategy
            and hasattr(strategy, "should_force_hydra")
            and strategy.should_force_hydra()
        ):
            # ????뉖뜤?????Β?띾쭡 ??筌믨퀡彛???袁⑸즲???
            if self._requirements_met(UnitTypeId.HYDRALISK) and vespene >= 50:
                queue.append(UnitTypeId.HYDRALISK)

        if gas_priority:
            queue.extend(self._filter_units(self._gas_unit_table(), vespene))
            if allow_mineral_mix:
                queue.extend(self._filter_units(self._mineral_unit_table(), vespene))
        else:
            if allow_mineral_mix:
                queue.extend(self._filter_units(self._mineral_unit_table(), vespene))
            queue.extend(self._filter_units(self._gas_unit_table(), vespene))

        if not queue:
            queue = [
                entry["unit"]
                for entry in self._gas_unit_table() + self._mineral_unit_table()
            ]
        return queue

    def _filter_units(self, table: List[dict], vespene: int) -> List[object]:
        queue: List[object] = []
        for entry in table:
            unit_type = entry["unit"]
            max_ratio = entry.get("max_ratio")
            min_gas = entry.get("min_gas", 0)
            if max_ratio is not None and self._unit_ratio(unit_type) >= max_ratio:
                continue
            if vespene < min_gas:
                continue
            queue.append(unit_type)
        return queue

    def _gas_unit_table(self) -> List[dict]:
        # Phase 18: Dynamic Ratios from StrategyManager
        strategy = getattr(self.bot, "strategy_manager", None)
        ratios = {}
        if strategy and hasattr(strategy, "get_unit_ratios"):
            ratios = strategy.get_unit_ratios()

        # Default fallbacks if no ratios provided
        def get_ratio(name, default):
            if name == "hydra":
                return ratios.get("hydra", ratios.get("hydralisk", default))
            return ratios.get(name, default)

        # Base units that consume gas
        # Note: Ravager/Lurker/Baneling are morphs, but we control their base unit production here
        # We use the ratio of the *final* unit to control the *base* unit production if needed,
        # but typically UnitMorphManager handles the morphing.
        # However, to support "Heavy Ravager" style, we need enough Roaches.

        # Calculate max_ratio dynamically
        return [
            {
                "unit": UnitTypeId.HYDRALISK,
                "min_gas": 50,
                "max_ratio": get_ratio("hydra", 0.3) + get_ratio("lurker", 0.1),
            },
            {
                "unit": UnitTypeId.CORRUPTOR,
                "min_gas": 100,
                "max_ratio": get_ratio("corruptor", 0.15),
            },
            {
                "unit": UnitTypeId.MUTALISK,
                "min_gas": 100,
                "max_ratio": get_ratio("mutalisk", 0.10),
            },
            {
                "unit": UnitTypeId.ROACH,
                "min_gas": 25,
                "max_ratio": get_ratio("roach", 0.4) + get_ratio("ravager", 0.2),
            },
            {
                "unit": UnitTypeId.ULTRALISK,
                "min_gas": 150,
                "max_ratio": get_ratio("ultralisk", 0.05),
            },
            {
                "unit": UnitTypeId.INFESTOR,
                "min_gas": 150,
                "max_ratio": get_ratio("infestor", 0.05),
            },
            {
                "unit": UnitTypeId.VIPER,
                "min_gas": 200,
                "max_ratio": get_ratio("viper", 0.05),
            },
        ]

    def _mineral_unit_table(self) -> List[dict]:
        strategy = getattr(self.bot, "strategy_manager", None)
        ratios = {}
        if strategy and hasattr(strategy, "get_unit_ratios"):
            ratios = strategy.get_unit_ratios()

        # Banelings are morphed from Zerglings
        ling_ratio = ratios.get("zergling", 0.4)
        bane_ratio = ratios.get("baneling", 0.1)

        return [
            {
                "unit": UnitTypeId.ZERGLING,
                "max_ratio": ling_ratio + bane_ratio + 0.2,
            },  # +0.2 buffer
        ]

    def _count_combat_units(self) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        units = self.bot.units
        combat_types = {
            UnitTypeId.ZERGLING,
            UnitTypeId.BANELING,
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKERMP,
            UnitTypeId.ULTRALISK,
        }
        return sum(1 for unit in units if unit.type_id in combat_types)

    def _count_gas_units(self) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        units = self.bot.units
        gas_types = {
            UnitTypeId.ROACH,
            UnitTypeId.RAVAGER,
            UnitTypeId.HYDRALISK,
            UnitTypeId.LURKERMP,
            UnitTypeId.ULTRALISK,
        }
        return sum(1 for unit in units if unit.type_id in gas_types)

    def _count_unit_type(self, unit_type) -> int:
        if not hasattr(self.bot, "units"):
            return 0
        units = self.bot.units
        return sum(1 for unit in units if unit.type_id == unit_type)

    def _unit_ratio(self, unit_type) -> float:
        total = max(1, self._count_combat_units())
        return self._count_unit_type(unit_type) / total

    def _check_protoss_threat_boost(self) -> bool:
        """
        *** ???????ш낄援?뤃????ル늅筌????살쓴勇???낆뒩??? ??좊즴?? ***
        """
        if not hasattr(self.bot, "enemy_units"):
            return False

        threat_units = {
            "IMMORTAL": 1,
            "VOIDRAY": 1,
            "COLOSSUS": 1,
            "CARRIER": 1,
            "ARCHON": 2,
            "DISRUPTOR": 1,
            "TEMPEST": 1,
            "BATTLECRUISER": 1,
            "LIBERATOR": 1,
        }

        unit_counts = {}
        found_air_threat = False

        for enemy in self.bot.enemy_units:
            try:
                name = getattr(enemy.type_id, "name", "").upper()
                if name in threat_units:
                    unit_counts[name] = unit_counts.get(name, 0) + 1
                    if name in [
                        "VOIDRAY",
                        "CARRIER",
                        "TEMPEST",
                        "BATTLECRUISER",
                        "LIBERATOR",
                        "COLOSSUS",
                    ]:
                        found_air_threat = True
            except Exception:
                continue

        if found_air_threat:
            self.gas_unit_ratio_target = 0.60

        for unit_type, threshold in threat_units.items():
            if unit_counts.get(unit_type, 0) >= threshold:
                if self.bot.iteration % 50 == 0:
                    logger.info(
                        f"Threat: {unit_type} x{unit_counts[unit_type]} -> Gas Boost!"
                    )
                return True

        return False
