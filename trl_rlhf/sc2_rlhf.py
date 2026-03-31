"""
Phase 540: TRL (Transformer Reinforcement Learning)
SC2 Bot strategy tuning via RLHF / PPO from human feedback
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math
import random
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


try:
    from trl import (
        PPOConfig, PPOTrainer,
        AutoModelForCausalLMWithValueHead,
        RewardTrainer, RewardConfig,
    )
    from transformers import AutoTokenizer
    import torch
    TRL_AVAILABLE = True
except ImportError:
    TRL_AVAILABLE = False


# ─────────────────────────────────────────────
# SC2 Strategy Prompt/Response pairs
# (for RLHF reward model training)
# ─────────────────────────────────────────────

STRATEGY_EXAMPLES = [
    {
        "prompt": "현재 미네랄 400, 가스 200, 병력 공급 40. 상대방 저글링이 보임.",
        "chosen": "저글링 러시 방어 후 바퀴-히드라로 안정적 확장 + 압박",
        "rejected": "즉시 전체 병력 돌격 (너무 이른 공격)",
    },
    {
        "prompt": "13공급 해처리, 16공급 산란못 개시. 저그 vs 테란.",
        "chosen": "22빠른 저글링 스피드 후 본진 급습 + 멀티 확장",
        "rejected": "저글링 없이 경제만 올리다 전멸",
    },
    {
        "prompt": "상대가 발키리/배틀크루저 준비 중. 미네랄 800 있음.",
        "chosen": "바이퍼 + 코르럽터로 공중 대응, 울트라 + 뮤탈 혼합",
        "rejected": "히드라만 계속 생산 (공중 유닛에 무력)",
    },
    {
        "prompt": "4해처리 드론 포화 상태. 가스 0, 미네랄 1200 적립.",
        "chosen": "모든 가스로 업그레이드 + 바퀴 워렌 후 3군단숙주 러시",
        "rejected": "드론만 계속 생산 (병력 부재로 상대에게 무력)",
    },
    {
        "prompt": "싸움에서 지고 있고, 미네랄 100만 남음.",
        "chosen": "유충 기생 능력으로 시간 벌기 + 기지 수호자로 전선 고정",
        "rejected": "전체 기지 포기 후 항복",
    },
]


# ─────────────────────────────────────────────
# Reward model (preference-based)
# ─────────────────────────────────────────────

@dataclass
class SC2RewardSignal:
    """RLHF reward signals for SC2 strategies."""
    economic_efficiency: float = 0.0   # worker/mineral ratio
    army_efficiency: float = 0.0       # combat value per supply
    expansion_timing: float = 0.0      # when bases were built
    tech_progression: float = 0.0      # tech upgrades obtained
    survival_time: float = 0.0         # how long game lasted
    win_loss: float = 0.0              # +1 win, -1 loss, 0 draw

    @property
    def total_reward(self) -> float:
        weights = [0.2, 0.25, 0.15, 0.15, 0.1, 0.15]
        values  = [
            self.economic_efficiency,
            self.army_efficiency,
            self.expansion_timing,
            self.tech_progression,
            self.survival_time,
            self.win_loss,
        ]
        return sum(w * v for w, v in zip(weights, values))


def compute_reward(
    strategy: str,
    outcome: dict,
) -> SC2RewardSignal:
    """Compute RLHF reward from game outcome."""
    workers = outcome.get("workers", 12)
    army = outcome.get("army", 0)
    frame = outcome.get("frame", 0)
    won = outcome.get("won", False)
    bases = outcome.get("bases", 1)
    upgrades = outcome.get("upgrades", 0)

    return SC2RewardSignal(
        economic_efficiency=min(1.0, workers / 66.0),
        army_efficiency=min(1.0, army / 100.0),
        expansion_timing=min(1.0, bases / 4.0),
        tech_progression=min(1.0, upgrades / 6.0),
        survival_time=min(1.0, frame / 8000.0),
        win_loss=1.0 if won else -0.5,
    )


# ─────────────────────────────────────────────
# Strategy LLM wrapper (RLHF tuning target)
# ─────────────────────────────────────────────

class SC2StrategyLLM:
    """
    Wraps an LLM for SC2 strategy generation.
    In full deployment: use GPT-4/Claude via API.
    Here: rule-based mock.
    """

    STRATEGY_TEMPLATES = {
        "aggro": "저글링 스피드 후 {time}분 저글링 러시. 방어 확인 후 멀티 확장.",
        "eco":   "해처리 3개 후 지상군 + 히드라 덴 테크. 안정적 경제 우선.",
        "air":   "스파이어 테크 후 뮤탈 러시 또는 브루드로드 레이트 테크.",
        "ground":"바퀴 워렌 + 하이드라 덴. 바퀴-히드라-울트라 전환.",
        "timing":"특정 타이밍 {time}분에 집중 공격. 이후 재확장.",
    }

    def generate_strategy(self, state: dict) -> str:
        minerals = state.get("minerals", 50)
        supply = state.get("supply", 12)
        enemy_race = state.get("enemy_race", "unknown")

        if supply < 30:
            strategy = "aggro"
        elif minerals > 500:
            strategy = "eco"
        elif enemy_race == "protoss":
            strategy = "ground"
        elif enemy_race == "terran":
            strategy = "air"
        else:
            strategy = "timing"

        template = self.STRATEGY_TEMPLATES[strategy]
        return template.format(time=random.randint(4, 8))

    def evaluate_strategy(self, strategy: str, outcome: dict) -> float:
        signal = compute_reward(strategy, outcome)
        return signal.total_reward


# ─────────────────────────────────────────────
# RLHF training loop
# ─────────────────────────────────────────────

def train_rlhf_agent(episodes: int = 50) -> dict:
    """RLHF training loop using preference-based reward."""
    llm = SC2StrategyLLM()
    from gymnasium_env.sc2_gym_env import SC2ZergEnv

    env = SC2ZergEnv(max_frames=1000)
    total_reward = 0.0
    preference_log = []

    for ep in range(episodes):
        obs, _ = env.reset(seed=ep)
        state = {
            "minerals": obs[0] * 1000,
            "supply": obs[2] * 200,
            "enemy_race": random.choice(["terran", "protoss", "zerg"]),
        }

        # Generate two candidate strategies
        strat_a = llm.generate_strategy(state)
        strat_b = llm.generate_strategy({**state, "supply": state["supply"] * 2})

        # Simulate game
        done = False
        ep_r = 0.0
        while not done:
            action = random.randint(0, 6)
            obs, r, term, trunc, info = env.step(action)
            ep_r += r
            done = term or trunc

        # Outcome
        outcome = {
            "workers": int(obs[4] * 80),
            "army": int(obs[5] * 200),
            "frame": int(obs[6] * 2000),
            "won": ep_r > 50,
            "bases": random.randint(1, 3),
            "upgrades": random.randint(0, 4),
        }

        reward_a = llm.evaluate_strategy(strat_a, outcome)
        reward_b = llm.evaluate_strategy(strat_b, outcome)

        preferred = strat_a if reward_a >= reward_b else strat_b
        preference_log.append({
            "chosen": preferred,
            "reward": max(reward_a, reward_b),
        })
        total_reward += max(reward_a, reward_b)

        if (ep + 1) % 10 == 0:
            avg = total_reward / (ep + 1)
            print(f"  Episode {ep+1:3d} | Avg RLHF reward: {avg:.3f}")

    return {
        "episodes": episodes,
        "mean_rlhf_reward": total_reward / episodes,
        "best_reward": max(p["reward"] for p in preference_log),
    }


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 540: TRL RLHF — SC2 Strategy LLM Fine-tuning")
    print(f"TRL available: {TRL_AVAILABLE}")

    result = train_rlhf_agent(episodes=30)
    print(f"\nResult: {result}")

    print("\nSample preference pairs:")
    for ex in STRATEGY_EXAMPLES[:2]:
        print(f"  Prompt:   {ex['prompt'][:60]}")
        print(f"  Chosen:   {ex['chosen']}")
        print(f"  Rejected: {ex['rejected']}")
        print()
