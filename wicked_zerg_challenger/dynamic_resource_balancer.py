# -*- coding: utf-8 -*-
"""
Dynamic Resource Balancer - ?먯썝 遺덇퇏??媛먯? 諛??앹궛 鍮꾩쑉 ?먮룞 議곗젙

?꾨컲 誘몃꽕??怨쇰떎/媛??遺議???媛???좊떅 鍮꾩쨷???먮룞 議곗젅?⑸땲??
"""

from typing import Dict, Tuple

from utils.logger import get_logger


class DynamicResourceBalancer:
    """
    * Dynamic Resource Balancer *

    ?먯썝 遺덇퇏?뺤쓣 媛먯??섍퀬 ?좊떅 ?앹궛 鍮꾩쑉???숈쟻?쇰줈 議곗젙?섏뿬
    誘몃꽕?꾧낵 媛?ㅻ? ?⑥쑉?곸쑝濡??ъ슜?⑸땲??
    """

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger("ResourceBalancer")

        # * ?먯썝 遺꾩꽍 二쇨린 *
        self.last_analysis = 0
        self.analysis_interval = 44  # ??2珥덈쭏??遺꾩꽍

        # * ?먯썝 遺덇퇏???꾧퀎媛?*
        self.mineral_excess_threshold = 1000  # 誘몃꽕??1000+ 怨쇰떎
        self.gas_shortage_threshold = 100  # 媛??100- 遺議?        self.high_mineral_threshold = 1500  # 誘몃꽕??1500+ ?ш컖??怨쇰떎

        # * ?숈쟻 鍮꾩쑉 議곗젙 *
        self.base_gas_ratio = 0.40
        self.current_gas_ratio = 0.40
        self.min_gas_ratio = 0.20
        self.max_gas_ratio = 0.60

        # * 議곗젙 ?띾룄 *
        self.adjustment_step = 0.05  # ?쒕쾲??5% 議곗젙

        # * ?곹깭 異붿쟻 *
        self.resource_state = (
            "BALANCED"  # BALANCED, MINERAL_EXCESS, GAS_SHORTAGE, CRITICAL
        )
        self.last_state_change = 0

    def update(self, iteration: int) -> Dict[str, float]:
        """
        ?먯썝 ?곹깭瑜?遺꾩꽍?섍퀬 議곗젙???좊떅 鍮꾩쑉??諛섑솚

        Args:
            iteration: ?꾩옱 寃뚯엫 諛섎났 ?잛닔

        Returns:
            議곗젙???좊떅 鍮꾩쑉 ?뺤뀛?덈━ {"gas_unit_ratio": 0.XX}
        """
        if iteration - self.last_analysis < self.analysis_interval:
            return {"gas_unit_ratio": self.current_gas_ratio}

        self.last_analysis = iteration

        # * 1. ?먯썝 ?곹깭 遺꾩꽍 *
        minerals = getattr(self.bot, "minerals", 0)
        gas = getattr(self.bot, "vespene", 0)
        game_time = getattr(self.bot, "time", 0)

        old_state = self.resource_state
        old_ratio = self.current_gas_ratio

        # * 2. ?먯썝 遺덇퇏??媛먯? *
        resource_state, target_ratio = self._analyze_resource_imbalance(
            minerals, gas, game_time
        )

        self.resource_state = resource_state
        self.current_gas_ratio = target_ratio

        # * 3. 濡쒓렇 (?곹깭 蹂???쒖뿉留? *
        if old_state != resource_state or abs(old_ratio - target_ratio) > 0.01:
            self.logger.info(
                f"[{int(game_time)}s] * RESOURCE BALANCE: {resource_state} *\n"
                f"  Minerals: {minerals}m, Gas: {gas}g\n"
                f"  Gas Unit Ratio: {old_ratio:.0%} -> {target_ratio:.0%}\n"
                f"  Adjustment: {(target_ratio - old_ratio)*100:+.0f}%"
            )
            self.last_state_change = iteration

        return {"gas_unit_ratio": self.current_gas_ratio}

    def _analyze_resource_imbalance(
        self, minerals: int, gas: int, game_time: float
    ) -> Tuple[str, float]:
        """
        ?먯썝 遺덇퇏?뺤쓣 遺꾩꽍?섍퀬 紐⑺몴 媛??鍮꾩쑉 怨꾩궛

        Args:
            minerals: ?꾩옱 誘몃꽕??            gas: ?꾩옱 媛??            game_time: 寃뚯엫 ?쒓컙

        Returns:
            (resource_state, target_gas_ratio)
        """
        # * Early Game (3遺??댄븯): 湲곕낯 鍮꾩쑉 ?좎? *
        if game_time < 180:
            return "BALANCED", self.base_gas_ratio

        if gas > max(300, minerals * 3) and minerals < 500:
            target_ratio = max(
                self.min_gas_ratio, self.current_gas_ratio - self.adjustment_step * 2
            )
            return "GAS_OVERFLOW", target_ratio

        # * Critical: 誘몃꽕????쬆 + 媛??怨좉컝 *
        if (
            minerals >= self.high_mineral_threshold
            and gas < self.gas_shortage_threshold
        ):
            # 媛???좊떅 鍮꾩쑉 理쒕?濡?利앷?
            target_ratio = min(
                self.max_gas_ratio, self.current_gas_ratio + self.adjustment_step * 2
            )
            return "CRITICAL", target_ratio

        # * Mineral Excess: 誘몃꽕?꾨쭔 留롮쓬 *
        if (
            minerals >= self.mineral_excess_threshold
            and gas >= self.gas_shortage_threshold
        ):
            # 媛???좊떅 鍮꾩쑉 利앷?
            target_ratio = min(
                self.max_gas_ratio, self.current_gas_ratio + self.adjustment_step
            )
            return "MINERAL_EXCESS", target_ratio

        # * Gas Shortage: 媛?ㅻ쭔 遺議?*
        if (
            gas < self.gas_shortage_threshold
            and minerals < self.mineral_excess_threshold
        ):
            # 媛???좊떅 鍮꾩쑉 媛먯냼 (誘몃꽕???좊떅 ?섎┝)
            target_ratio = max(
                self.min_gas_ratio, self.current_gas_ratio - self.adjustment_step
            )
            return "GAS_SHORTAGE", target_ratio

        # * Balanced: ?뺤긽 踰붿쐞 *
        # ?먯쭊?곸쑝濡?湲곕낯 鍮꾩쑉濡?蹂듦?
        if self.current_gas_ratio > self.base_gas_ratio:
            target_ratio = max(
                self.base_gas_ratio, self.current_gas_ratio - self.adjustment_step * 0.5
            )
        elif self.current_gas_ratio < self.base_gas_ratio:
            target_ratio = min(
                self.base_gas_ratio, self.current_gas_ratio + self.adjustment_step * 0.5
            )
        else:
            target_ratio = self.base_gas_ratio

        return "BALANCED", target_ratio

    def get_unit_ratio_adjustments(self) -> Dict[str, float]:
        """
        ?꾩옱 ?먯썝 ?곹깭???곕Ⅸ ?좊떅蹂?鍮꾩쑉 議곗젙媛?諛섑솚

        Returns:
            ?좊떅蹂?鍮꾩쑉 議곗젙 ?뺤뀛?덈━
            ?? {"hydralisk": 0.30, "mutalisk": 0.15, "zergling": 0.40, "roach": 0.15}
        """
        gas_ratio = max(self.min_gas_ratio, min(self.max_gas_ratio, self.current_gas_ratio))
        mineral_ratio = 1.0 - gas_ratio

        # ?먯썝 ?곹깭???곕Ⅸ ?좊떅 援ъ꽦
        if self.resource_state == "CRITICAL":
            return {
            # Mineral-shortage path: prefer cheap gas-heavy units
                "hydralisk": gas_ratio * 0.50,
                "mutalisk": gas_ratio * 0.30,
                "corruptor": gas_ratio * 0.20,
                "zergling": mineral_ratio * 0.70,
                "roach": mineral_ratio * 0.30,
            }

        elif self.resource_state == "MINERAL_EXCESS":
            # 誘몃꽕??留롮쓬 -> 媛???좊떅 鍮꾩쨷 利앷?
            return {
                "hydralisk": gas_ratio * 0.45,
                "roach": 0.25,  # ?쎄컙??媛???ъ슜
                "mutalisk": gas_ratio * 0.25,
                "zergling": mineral_ratio * 0.80,
            }

        elif self.resource_state == "GAS_SHORTAGE":
            # 媛??遺議?-> 誘몃꽕???좊떅 ?꾩＜
            return {
                "zergling": mineral_ratio * 0.60,
                "roach": 0.30,  # ?쎄컙??媛???ъ슜
                "hydralisk": gas_ratio * 0.10,
            }

        elif self.resource_state == "GAS_OVERFLOW":
            return {
                "zergling": 0.70,
                "roach": 0.25,
                "hydralisk": 0.05,
            }

        else:  # BALANCED
            # 洹좏삎 ?≫엺 援ъ꽦
            return {
                "zergling": 0.30,
                "roach": 0.25,
                "hydralisk": 0.25,
                "mutalisk": 0.15,
                "queen": 0.05,
            }

    def should_build_extractor(self) -> bool:
        """
        異붽? 媛??嫄대Ъ 嫄댁꽕 ?꾩슂 ?щ?

        Returns:
            True if more extractors needed
        """
        # Critical ?곹깭?먯꽌??媛??嫄대Ъ ??吏볤린
        if self.resource_state == "CRITICAL":
            return True

        # Gas Shortage ?곹깭?먯꽌??媛??嫄대Ъ 吏볤린
        if self.resource_state == "GAS_SHORTAGE":
            return True

        return False

    def get_current_ratio(self) -> float:
        """?꾩옱 媛???좊떅 鍮꾩쑉 諛섑솚"""
        return self.current_gas_ratio
