# -*- coding: utf-8 -*-
"""
Fundamentals Manager - 기본기 학습 단계 관리

기본기를 순차적으로 학습하도록 관리:
1. 레벨 0: 드론 생산 기본 (12-16 드론)
2. 레벨 1: 보급 관리 (supply block 방지)
3. 레벨 2: 확장 타이밍 (2베이스 확보)
4. 레벨 3: 군대 생산 (기본 방어)
5. 레벨 4: 빌드오더 적용 (학습된 데이터 사용)

각 레벨을 완수해야 다음 레벨로 진행됩니다.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class FundamentalSkill:
    """개별 기본기 스킬 정의"""

    def __init__(
        self,
        skill_id: str,
        name: str,
        description: str,
        success_criteria: Dict,
        reward_weight: float = 1.0,
    ):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.success_criteria = success_criteria  # 성공 조건
        self.reward_weight = reward_weight  # 이 스킬의 보상 가중치
        self.attempts = 0  # 시도 횟수
        self.successes = 0  # 성공 횟수
        self.failures = 0  # 실패 횟수

    def check_success(self, bot) -> bool:
        """
        봇의 현재 상태가 성공 조건을 만족하는지 확인

        Args:
            bot: BotAI 인스턴스

        Returns:
            성공 여부 (bool)
        """
        criteria = self.success_criteria
        game_time = getattr(bot, "time", 0)

        # 시간 범위 체크
        if "time_min" in criteria and game_time < criteria["time_min"]:
            return False
        if "time_max" in criteria and game_time > criteria["time_max"]:
            return False

        # 드론 수 체크
        if "min_drones" in criteria:
            drone_count = len(bot.units.filter(lambda u: u.name == "Drone"))
            if drone_count < criteria["min_drones"]:
                return False

        # 기지 수 체크
        if "min_bases" in criteria:
            base_count = len(bot.townhalls)
            if base_count < criteria["min_bases"]:
                return False

        # 보급 차단 체크
        if "supply_blocked" in criteria:
            supply_left = bot.supply_left
            supply_cap = bot.supply_cap
            is_blocked = supply_left <= 0 and supply_cap < 200
            if is_blocked != criteria["supply_blocked"]:
                return False

        # 군대 가치 체크
        if "min_army_value" in criteria:
            army_value = sum(u.health + u.shield for u in bot.units if u.can_attack)
            if army_value < criteria["min_army_value"]:
                return False

        # 미네랄 사용 체크 (뱅킹 방지)
        if "max_minerals" in criteria:
            if bot.minerals > criteria["max_minerals"]:
                return False

        return True

    def get_success_rate(self) -> float:
        """성공률 반환"""
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts


class FundamentalsManager:
    """기본기 학습 단계 관리자"""

    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.progress_file = self.data_dir / "fundamentals_progress.json"

        # 기본기 레벨 정의
        self.levels: List[Dict] = [
            # 레벨 0: 드론 생산 기본 (12-16 드론, 2분 이내)
            {
                "level": 0,
                "name": "Drone Production Basics",
                "description": "2분 안에 12-16 드론 생산",
                "skills": [
                    FundamentalSkill(
                        skill_id="drone_12_by_2min",
                        name="12 Drones by 2min",
                        description="2분 안에 드론 12마리 생산",
                        success_criteria={
                            "time_max": 120,  # 2분
                            "min_drones": 12,
                        },
                        reward_weight=2.0,  # 높은 가중치
                    ),
                ],
                "success_threshold": 0.70,  # 70% 성공률로 통과
            },
            # 레벨 1: 보급 관리 (supply block 방지)
            {
                "level": 1,
                "name": "Supply Management",
                "description": "5분 동안 supply block 없이 유지",
                "skills": [
                    FundamentalSkill(
                        skill_id="no_supply_block_5min",
                        name="No Supply Block (5min)",
                        description="5분 동안 supply block 없음",
                        success_criteria={
                            "time_min": 0,
                            "time_max": 300,  # 5분
                            "supply_blocked": False,
                        },
                        reward_weight=1.5,
                    ),
                ],
                "success_threshold": 0.70,
            },
            # 레벨 2: 확장 타이밍 (2베이스, 2분 안)
            {
                "level": 2,
                "name": "Expansion Timing",
                "description": "2분 안에 2베이스 확보",
                "skills": [
                    FundamentalSkill(
                        skill_id="second_base_by_2min",
                        name="Second Base by 2min",
                        description="2분 안에 2번째 기지 건설",
                        success_criteria={
                            "time_max": 120,  # 2분
                            "min_bases": 2,
                        },
                        reward_weight=2.0,
                    ),
                ],
                "success_threshold": 0.70,
            },
            # 레벨 3: 미네랄 사용 (2분 이후 500 이하 유지)
            {
                "level": 3,
                "name": "Resource Management",
                "description": "2분 이후 미네랄 500 이하 유지",
                "skills": [
                    FundamentalSkill(
                        skill_id="minerals_under_500_after_2min",
                        name="Minerals <500 (after 2min)",
                        description="2분 이후 미네랄 500 이하로 유지",
                        success_criteria={
                            "time_min": 120,  # 2분 이후
                            "max_minerals": 500,
                        },
                        reward_weight=1.5,
                    ),
                ],
                "success_threshold": 0.70,
            },
            # 레벨 4: 군대 생산 (5분에 군대 가치 500+)
            {
                "level": 4,
                "name": "Army Production",
                "description": "5분에 군대 가치 500+",
                "skills": [
                    FundamentalSkill(
                        skill_id="army_value_500_by_5min",
                        name="Army Value 500+ by 5min",
                        description="5분에 군대 가치 500 이상",
                        success_criteria={
                            "time_min": 270,  # 4.5분
                            "time_max": 300,  # 5분
                            "min_army_value": 500,
                        },
                        reward_weight=1.5,
                    ),
                ],
                "success_threshold": 0.70,
            },
            # 레벨 5: 빌드오더 적용 (학습된 데이터 기반)
            {
                "level": 5,
                "name": "Build Order Application",
                "description": "학습된 빌드오더 적용",
                "skills": [
                    FundamentalSkill(
                        skill_id="learned_build_order",
                        name="Apply Learned Build Order",
                        description="리플레이에서 학습한 빌드오더 실행",
                        success_criteria={
                            # 빌드오더는 게임 전체 평가
                            "time_min": 0,
                        },
                        reward_weight=1.0,
                    ),
                ],
                "success_threshold": 0.60,  # 낮은 기준 (복합적)
            },
        ]

        # 현재 레벨
        self.current_level = 0

        # 진행도 로드
        self._load_progress()

    def _load_progress(self) -> None:
        """진행도 파일에서 데이터 로드"""
        if not self.progress_file.exists():
            return

        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.current_level = data.get("current_level", 0)

            # 각 스킬의 통계 복원
            for level_data in data.get("levels", []):
                level_idx = level_data["level"]
                if level_idx >= len(self.levels):
                    continue

                skills_data = level_data.get("skills", [])
                for skill_data in skills_data:
                    skill_id = skill_data["skill_id"]

                    # 해당 스킬 찾기
                    for skill in self.levels[level_idx]["skills"]:
                        if skill.skill_id == skill_id:
                            skill.attempts = skill_data.get("attempts", 0)
                            skill.successes = skill_data.get("successes", 0)
                            skill.failures = skill_data.get("failures", 0)
                            break

        except Exception as e:
            print(f"[FUNDAMENTALS] Failed to load progress: {e}")

    def _save_progress(self) -> None:
        """진행도 파일에 저장"""
        try:
            data = {
                "current_level": self.current_level,
                "levels": [],
            }

            for level_info in self.levels:
                level_data = {
                    "level": level_info["level"],
                    "name": level_info["name"],
                    "description": level_info["description"],
                    "success_threshold": level_info["success_threshold"],
                    "skills": [],
                }

                for skill in level_info["skills"]:
                    skill_data = {
                        "skill_id": skill.skill_id,
                        "name": skill.name,
                        "attempts": skill.attempts,
                        "successes": skill.successes,
                        "failures": skill.failures,
                        "success_rate": skill.get_success_rate(),
                    }
                    level_data["skills"].append(skill_data)

                data["levels"].append(level_data)

            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"[FUNDAMENTALS] Failed to save progress: {e}")

    def check_level_progress(self, bot) -> None:
        """
        현재 레벨의 기본기를 체크하고 진행도 업데이트

        Args:
            bot: BotAI 인스턴스
        """
        if self.current_level >= len(self.levels):
            return  # 모든 레벨 완료

        level_info = self.levels[self.current_level]
        skills = level_info["skills"]

        # 각 스킬 체크
        for skill in skills:
            skill.attempts += 1
            if skill.check_success(bot):
                skill.successes += 1
            else:
                skill.failures += 1

        # 레벨 승격 체크
        self._check_level_promotion()

        # 진행도 저장
        self._save_progress()

    def _check_level_promotion(self) -> None:
        """레벨 승격 조건 확인"""
        if self.current_level >= len(self.levels):
            return

        level_info = self.levels[self.current_level]
        threshold = level_info["success_threshold"]

        # 모든 스킬이 기준 이상 성공률인지 확인
        all_passed = True
        for skill in level_info["skills"]:
            if skill.get_success_rate() < threshold:
                all_passed = False
                break

        if all_passed:
            print(f"\n[FUNDAMENTALS] [OK] Level {self.current_level} completed!")
            print(f"[FUNDAMENTALS] Advancing to Level {self.current_level + 1}")
            self.current_level += 1
            self._save_progress()

    def get_current_level_info(self) -> Dict:
        """현재 레벨 정보 반환"""
        if self.current_level >= len(self.levels):
            return {
                "level": self.current_level,
                "name": "Mastery Complete",
                "description": "All fundamentals mastered",
                "skills": [],
            }

        return self.levels[self.current_level]

    def get_skill_reward_weight(self, skill_id: str) -> float:
        """특정 스킬의 보상 가중치 반환"""
        for level_info in self.levels:
            for skill in level_info["skills"]:
                if skill.skill_id == skill_id:
                    return skill.reward_weight
        return 1.0

    def is_skill_active(self, skill_id: str) -> bool:
        """특정 스킬이 현재 레벨에서 활성화되어 있는지 확인"""
        if self.current_level >= len(self.levels):
            return False

        level_info = self.levels[self.current_level]
        for skill in level_info["skills"]:
            if skill.skill_id == skill_id:
                return True
        return False

    def print_progress(self) -> None:
        """현재 진행도 출력"""
        print("\n" + "=" * 70)
        print("[FUNDAMENTALS] PROGRESS REPORT")
        print("=" * 70)
        print(f"Current Level: {self.current_level}")

        if self.current_level < len(self.levels):
            level_info = self.levels[self.current_level]
            print(f"Level Name: {level_info['name']}")
            print(f"Description: {level_info['description']}")
            print(f"Success Threshold: {level_info['success_threshold']:.0%}")
            print("-" * 70)

            for skill in level_info["skills"]:
                print(f"  Skill: {skill.name}")
                print(f"    Attempts: {skill.attempts}")
                print(f"    Successes: {skill.successes}")
                print(f"    Success Rate: {skill.get_success_rate():.2%}")
        else:
            print("Status: All fundamentals mastered!")

        print("=" * 70)
