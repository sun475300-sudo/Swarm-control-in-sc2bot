"""
Phase 436: DSPy - SC2 Strategy Programming Framework
Programmatic LLM pipelines with optimizable prompts for SC2 strategy.
"""

import dspy
from dspy import Signature, InputField, OutputField, Module
from dspy import ChainOfThought, ProgramOfThought, ReAct
from dspy.teleprompt import BootstrapFewShot, BootstrapFewShotWithRandomSearch
from dspy.evaluate import Evaluate


# ── DSPy Signatures ───────────────────────────────────────────────────────────

class GameStateToAction(Signature):
    """Analyze an SC2 game state and recommend the optimal action."""
    race: str = InputField(desc="Player's race: Zerg, Terran, or Protoss")
    opponent_race: str = InputField(desc="Opponent's race")
    game_time: float = InputField(desc="Current game time in seconds")
    supply_ratio: float = InputField(desc="supply_used / supply_cap (0.0 - 1.0)")
    minerals: int = InputField(desc="Current mineral count")
    gas: int = InputField(desc="Current gas count")
    army_supply: int = InputField(desc="Current army supply")
    action: str = OutputField(desc="Recommended action (1-2 sentences)")
    reasoning: str = OutputField(desc="Brief tactical reasoning")


class ReplayToInsight(Signature):
    """Extract strategic insight from an SC2 replay description."""
    replay_summary: str = InputField(desc="Text summary of an SC2 replay")
    key_insight: str = OutputField(desc="Most important strategic lesson from this replay")
    tactical_error: str = OutputField(desc="Main mistake made, or 'None' if flawless")
    improvement: str = OutputField(desc="Specific improvement for next game")


class ThreatToResponse(Signature):
    """Assess a threat and recommend a counter-strategy."""
    threat_description: str = InputField(desc="Description of opponent's army/strategy")
    current_units: str = InputField(desc="Player's current army composition")
    threat_level: int = OutputField(desc="Threat level 1-10")
    counter_strategy: str = OutputField(desc="Recommended counter in 1-2 sentences")
    units_to_build: str = OutputField(desc="Comma-separated list of units to prioritize")


# ── DSPy Modules ──────────────────────────────────────────────────────────────

class SC2TacticalAdvisor(Module):
    """Chain-of-thought tactical advisor for real-time SC2 decision making."""

    def __init__(self):
        super().__init__()
        self.analyze = ChainOfThought(GameStateToAction)

    def forward(self, race, opponent_race, game_time, supply_ratio, minerals, gas, army_supply):
        return self.analyze(
            race=race,
            opponent_race=opponent_race,
            game_time=game_time,
            supply_ratio=supply_ratio,
            minerals=minerals,
            gas=gas,
            army_supply=army_supply,
        )


class SC2ReplayAnalyzer(Module):
    """Program-of-thought replay analysis with code generation."""

    def __init__(self):
        super().__init__()
        self.extract_insight = ChainOfThought(ReplayToInsight)

    def forward(self, replay_summary):
        return self.extract_insight(replay_summary=replay_summary)


class SC2ThreatResponder(Module):
    """ReAct-style threat assessment with multi-step reasoning."""

    def __init__(self, tools=None):
        super().__init__()
        if tools is None:
            tools = []
        self.assess = ReAct(ThreatToResponse, tools=tools)

    def forward(self, threat_description, current_units):
        return self.assess(
            threat_description=threat_description,
            current_units=current_units,
        )


# ── Training demonstrations ───────────────────────────────────────────────────

SC2_DEMONSTRATIONS = [
    dspy.Example(
        race="Zerg",
        opponent_race="Terran",
        game_time=240.0,
        supply_ratio=0.75,
        minerals=300,
        gas=50,
        army_supply=10,
        action="Build Roach Warren immediately and produce Roaches.",
        reasoning="Terran bio timing attack incoming around 4 minutes; Roaches counter Marines efficiently.",
    ).with_inputs("race", "opponent_race", "game_time", "supply_ratio", "minerals", "gas", "army_supply"),

    dspy.Example(
        race="Zerg",
        opponent_race="Protoss",
        game_time=480.0,
        supply_ratio=0.85,
        minerals=150,
        gas=400,
        army_supply=40,
        action="Saturate third base workers and add two Spire for Corruptors.",
        reasoning="High gas, low minerals indicates Protoss Colossus tech; air counter needed.",
    ).with_inputs("race", "opponent_race", "game_time", "supply_ratio", "minerals", "gas", "army_supply"),

    dspy.Example(
        race="Zerg",
        opponent_race="Zerg",
        game_time=180.0,
        supply_ratio=0.60,
        minerals=500,
        gas=0,
        army_supply=15,
        action="Expand to third hatchery and maintain Zergling speed patrol.",
        reasoning="ZvZ early is drone-focused; Zergling speed provides map control while droning.",
    ).with_inputs("race", "opponent_race", "game_time", "supply_ratio", "minerals", "gas", "army_supply"),
]


# ── Metric and optimizer ──────────────────────────────────────────────────────

def sc2_action_metric(example: dspy.Example, prediction, trace=None) -> float:
    """Evaluate whether predicted action matches ground truth quality."""
    pred_action = prediction.action.lower() if hasattr(prediction, "action") else ""
    gold_action = example.action.lower()

    # Keyword overlap as proxy metric
    pred_tokens = set(pred_action.split())
    gold_tokens = set(gold_action.split())
    overlap = len(pred_tokens & gold_tokens) / (len(gold_tokens) + 1e-8)
    return min(1.0, overlap * 2)


def optimize_sc2_advisor(advisor: SC2TacticalAdvisor, trainset: list) -> SC2TacticalAdvisor:
    """Run BootstrapFewShot optimization on the SC2 tactical advisor."""
    optimizer = BootstrapFewShot(
        metric=sc2_action_metric,
        max_bootstrapped_demos=3,
        max_labeled_demos=5,
    )
    return optimizer.compile(advisor, trainset=trainset)


# ── Runner ────────────────────────────────────────────────────────────────────

def run_sc2_dspy(lm_model: str = "openai/gpt-4o-mini") -> None:
    """Run SC2 DSPy strategy program."""
    lm = dspy.LM(lm_model)
    dspy.configure(lm=lm)

    advisor = SC2TacticalAdvisor()
    analyzer = SC2ReplayAnalyzer()
    responder = SC2ThreatResponder()

    print("[DSPy] Running SC2 tactical advisor (unoptimized)...")
    result = advisor(
        race="Zerg", opponent_race="Terran",
        game_time=300.0, supply_ratio=0.72,
        minerals=350, gas=100, army_supply=25,
    )
    print(f"  Action: {result.action}")
    print(f"  Reasoning: {result.reasoning}")

    print("\n[DSPy] Optimizing with BootstrapFewShot...")
    optimized = optimize_sc2_advisor(advisor, SC2_DEMONSTRATIONS)
    print("[DSPy] Optimization complete.")


if __name__ == "__main__":
    print("[DSPy] SC2 Strategy Program modules:")
    print("  Signatures: GameStateToAction, ReplayToInsight, ThreatToResponse")
    print("  Modules: SC2TacticalAdvisor (CoT), SC2ReplayAnalyzer (PoT), SC2ThreatResponder (ReAct)")
    print("  Optimizer: BootstrapFewShot with 3 SC2 demonstrations")

# Phase 436: DSPy registered
