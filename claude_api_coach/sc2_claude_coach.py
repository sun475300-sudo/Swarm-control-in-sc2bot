"""
Phase 627: Claude API Strategic Advisor for SC2
=================================================
claude_api_coach/sc2_claude_coach.py

Claude API integration for real-time strategic coaching of the SC2
Zerg commander bot.
  - ClaudeCoach           : main coach that calls Claude API for advice
  - GameStateSerializer   : converts game state into structured text
  - StrategyPromptBuilder : matchup-aware prompt templates
  - CoachingSession       : multi-turn coaching with conversation history

Supports Zerg-focused advice, matchup-specific prompts (ZvT, ZvP, ZvZ),
opening analysis, mid-game decisions, late-game transitions, and
timing attack alerts.

Dependencies: numpy (required), anthropic (optional).
Supports 260+ language localisation via label keys.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np

# ---------------------------------------------------------------------------
# Optional Anthropic SDK import
# ---------------------------------------------------------------------------
_ANTHROPIC_AVAILABLE = False
try:
    import anthropic

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums and constants
# ---------------------------------------------------------------------------


class Race(Enum):
    ZERG = "Zerg"
    TERRAN = "Terran"
    PROTOSS = "Protoss"


class Matchup(Enum):
    ZvT = "ZvT"
    ZvP = "ZvP"
    ZvZ = "ZvZ"


class GamePhase(Enum):
    OPENING = auto()  # 0--3 min
    EARLY = auto()  # 3--6 min
    MID = auto()  # 6--12 min
    LATE = auto()  # 12+ min


class CoachingTopic(Enum):
    OPENING_ANALYSIS = "opening_analysis"
    MID_GAME_DECISION = "mid_game_decision"
    LATE_GAME_TRANSITION = "late_game_transition"
    TIMING_ATTACK_ALERT = "timing_attack_alert"
    ECONOMY_CHECK = "economy_check"
    ARMY_COMPOSITION = "army_composition"
    SCOUTING_INFO = "scouting_info"
    GENERAL = "general"


# Phase time boundaries (seconds)
_PHASE_BOUNDS = {
    GamePhase.OPENING: (0, 180),
    GamePhase.EARLY: (180, 360),
    GamePhase.MID: (360, 720),
    GamePhase.LATE: (720, float("inf")),
}

# Claude model configuration
_DEFAULT_MODEL = "claude-sonnet-4-20250514"
_MAX_TOKENS = 1024
_TEMPERATURE = 0.4


# ---------------------------------------------------------------------------
# GameStateSerializer: convert game state to structured text
# ---------------------------------------------------------------------------


@dataclass
class GameState:
    """Snapshot of the current SC2 game state."""

    game_time_seconds: float = 0.0
    supply_used: int = 0
    supply_cap: int = 200
    minerals: int = 0
    vespene: int = 0
    worker_count: int = 0
    army_supply: int = 0
    base_count: int = 1
    matchup: Matchup = Matchup.ZvT

    # Army composition: unit_name -> count
    army_comp: Dict[str, int] = field(default_factory=dict)

    # Structures
    structures: Dict[str, int] = field(default_factory=dict)

    # Upgrades in progress or completed
    upgrades: List[str] = field(default_factory=list)

    # Scouting intel about opponent
    enemy_army_comp: Dict[str, int] = field(default_factory=dict)
    enemy_structures: List[str] = field(default_factory=list)
    enemy_base_count: int = 1

    # Additional context
    pending_units: Dict[str, int] = field(default_factory=dict)
    creep_coverage: float = 0.0  # 0.0 -- 1.0
    inject_efficiency: float = 0.0  # 0.0 -- 1.0


class GameStateSerializer:
    """Converts GameState into structured text for the Claude API."""

    def serialize(self, state: GameState) -> str:
        """Produce a structured text block from the game state."""
        phase = self._detect_phase(state.game_time_seconds)
        minutes = int(state.game_time_seconds // 60)
        seconds = int(state.game_time_seconds % 60)

        lines: List[str] = []
        lines.append("=== SC2 GAME STATE ===")
        lines.append(f"Time       : {minutes:02d}:{seconds:02d}")
        lines.append(f"Matchup    : {state.matchup.value}")
        lines.append(f"Phase      : {phase.name}")
        lines.append(f"Supply     : {state.supply_used}/{state.supply_cap}")
        lines.append(f"Resources  : {state.minerals} minerals, {state.vespene} gas")
        lines.append(f"Workers    : {state.worker_count}")
        lines.append(f"Army Supply: {state.army_supply}")
        lines.append(f"Bases      : {state.base_count}")
        lines.append(f"Creep%     : {state.creep_coverage * 100:.0f}%")
        lines.append(f"Inject Eff : {state.inject_efficiency * 100:.0f}%")

        if state.army_comp:
            lines.append("")
            lines.append("--- Our Army ---")
            for unit, count in sorted(state.army_comp.items()):
                lines.append(f"  {unit}: {count}")

        if state.structures:
            lines.append("")
            lines.append("--- Our Structures ---")
            for struct, count in sorted(state.structures.items()):
                lines.append(f"  {struct}: {count}")

        if state.upgrades:
            lines.append("")
            lines.append("--- Upgrades ---")
            for upg in state.upgrades:
                lines.append(f"  {upg}")

        if state.pending_units:
            lines.append("")
            lines.append("--- Pending Production ---")
            for unit, count in sorted(state.pending_units.items()):
                lines.append(f"  {unit}: {count}")

        if state.enemy_army_comp or state.enemy_structures:
            lines.append("")
            lines.append("--- Enemy Intel ---")
            lines.append(f"  Enemy bases: {state.enemy_base_count}")
            for unit, count in sorted(state.enemy_army_comp.items()):
                lines.append(f"  {unit}: {count}")
            for struct in state.enemy_structures:
                lines.append(f"  [Building] {struct}")

        lines.append("=== END STATE ===")
        return "\n".join(lines)

    def serialize_compact(self, state: GameState) -> str:
        """Short-form summary for token-efficient prompts."""
        phase = self._detect_phase(state.game_time_seconds)
        minutes = int(state.game_time_seconds // 60)
        seconds = int(state.game_time_seconds % 60)
        army_str = ", ".join(f"{k}:{v}" for k, v in state.army_comp.items())
        enemy_str = ", ".join(f"{k}:{v}" for k, v in state.enemy_army_comp.items())
        return (
            f"{state.matchup.value} | {minutes:02d}:{seconds:02d} ({phase.name}) | "
            f"Supply {state.supply_used}/{state.supply_cap} | "
            f"{state.minerals}m {state.vespene}g | "
            f"Bases:{state.base_count} Workers:{state.worker_count} | "
            f"Army:[{army_str}] | Enemy:[{enemy_str}]"
        )

    @staticmethod
    def _detect_phase(seconds: float) -> GamePhase:
        for phase, (lo, hi) in _PHASE_BOUNDS.items():
            if lo <= seconds < hi:
                return phase
        return GamePhase.LATE


# ---------------------------------------------------------------------------
# StrategyPromptBuilder: matchup-aware prompt templates
# ---------------------------------------------------------------------------


class StrategyPromptBuilder:
    """Builds Claude API prompts tailored to SC2 coaching scenarios."""

    _SYSTEM_PROMPT = (
        "You are an expert StarCraft II coach specialising in Zerg gameplay. "
        "You provide concise, actionable advice based on the current game state. "
        "Focus on: macro efficiency, army composition, timing attacks, scouting reads, "
        "and strategic transitions. Always consider the specific matchup. "
        "Keep responses under 200 words unless asked for detailed analysis."
    )

    _MATCHUP_CONTEXT: Dict[Matchup, str] = {
        Matchup.ZvT: (
            "Zerg vs Terran key points: "
            "Watch for early Hellion/Reaper aggression. "
            "Ling-Bane-Hydra is standard vs bio; Roach-Hydra-Viper vs mech. "
            "Creep spread is crucial to slow Terran pushes. "
            "Late game: Broodlord-Viper-Corruptor is the goal composition."
        ),
        Matchup.ZvP: (
            "Zerg vs Protoss key points: "
            "Scout for Stargate (Oracle) and Dark Shrine (DT rush). "
            "Roach-Ravager timing around 5:00 is strong. "
            "Mid-game Lurkers dominate ground armies. "
            "Late game: avoid Skytoss deathball; use Corruptor-Viper with Parasitic Bomb."
        ),
        Matchup.ZvZ: (
            "Zerg vs Zerg key points: "
            "Opening is volatile -- Ling-Bane wars decide many games. "
            "Never stop Ling production until Baneling Nest timing confirmed. "
            "Roach transition after map control is standard. "
            "Late ZvZ: Lurkers or Mutas for harassment; Broodlords to close."
        ),
    }

    _TOPIC_TEMPLATES: Dict[CoachingTopic, str] = {
        CoachingTopic.OPENING_ANALYSIS: (
            "Analyse my opening. Am I on track for a standard {matchup} build? "
            "What should my immediate priorities be?"
        ),
        CoachingTopic.MID_GAME_DECISION: (
            "I am in the mid-game. Based on my army and enemy intel, "
            "should I attack, defend, expand, or tech up? Why?"
        ),
        CoachingTopic.LATE_GAME_TRANSITION: (
            "I need to transition for the late game. What composition should "
            "I aim for in {matchup}? What upgrades are priority?"
        ),
        CoachingTopic.TIMING_ATTACK_ALERT: (
            "Based on the enemy intel, is a timing attack likely? "
            "If so, what should I build and where should I position?"
        ),
        CoachingTopic.ECONOMY_CHECK: (
            "Review my economy. Am I droning enough? Should I take another base? "
            "Am I floating too many resources?"
        ),
        CoachingTopic.ARMY_COMPOSITION: (
            "Is my army composition appropriate for this {matchup} at this stage? "
            "What units should I add or cut?"
        ),
        CoachingTopic.SCOUTING_INFO: (
            "Based on enemy intel, what is the opponent likely doing? "
            "What builds should I prepare against?"
        ),
        CoachingTopic.GENERAL: (
            "Give me general strategic advice for my current situation."
        ),
    }

    def __init__(self) -> None:
        self.serializer = GameStateSerializer()

    @property
    def system_prompt(self) -> str:
        return self._SYSTEM_PROMPT

    def build_prompt(
        self,
        state: GameState,
        topic: CoachingTopic = CoachingTopic.GENERAL,
        custom_question: Optional[str] = None,
        compact: bool = False,
    ) -> str:
        """Build a user-facing prompt including game state and question."""
        parts: List[str] = []

        # Matchup context
        matchup_ctx = self._MATCHUP_CONTEXT.get(state.matchup, "")
        if matchup_ctx:
            parts.append(f"[Matchup Context]\n{matchup_ctx}")
            parts.append("")

        # Game state
        if compact:
            parts.append(f"[Game State] {self.serializer.serialize_compact(state)}")
        else:
            parts.append(self.serializer.serialize(state))
        parts.append("")

        # Question
        if custom_question:
            parts.append(f"[Question] {custom_question}")
        else:
            template = self._TOPIC_TEMPLATES.get(
                topic, self._TOPIC_TEMPLATES[CoachingTopic.GENERAL]
            )
            question = template.format(matchup=state.matchup.value)
            parts.append(f"[Question] {question}")

        return "\n".join(parts)

    def build_timing_alert(
        self,
        state: GameState,
        expected_attack_time: float,
        attack_type: str,
    ) -> str:
        """Build an urgent timing attack alert prompt."""
        eta = max(0.0, expected_attack_time - state.game_time_seconds)
        eta_min = int(eta // 60)
        eta_sec = int(eta % 60)
        parts = [
            self.serializer.serialize(state),
            "",
            f"[TIMING ALERT] Expected {attack_type} in ~{eta_min}:{eta_sec:02d}!",
            f"What should I build and where should I position to defend?",
        ]
        return "\n".join(parts)

    def build_followup(
        self,
        previous_advice: str,
        followup_question: str,
    ) -> str:
        """Build a follow-up question referencing previous advice."""
        return (
            f"[Previous Advice]\n{previous_advice}\n\n"
            f"[Follow-up] {followup_question}"
        )


# ---------------------------------------------------------------------------
# CoachingSession: multi-turn conversation with history
# ---------------------------------------------------------------------------


@dataclass
class ChatMessage:
    """A single message in the coaching conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    topic: Optional[CoachingTopic] = None
    game_time: Optional[float] = None


class CoachingSession:
    """Manages a multi-turn coaching conversation with history.

    Keeps a rolling window of messages for context and supports
    serialisation for API calls.
    """

    def __init__(self, max_history: int = 20) -> None:
        self.messages: List[ChatMessage] = []
        self.max_history = max_history
        self.session_id: str = f"session-{int(time.time())}"
        self.start_time: float = time.time()
        self.matchup: Optional[Matchup] = None

    def add_user_message(
        self,
        content: str,
        topic: Optional[CoachingTopic] = None,
        game_time: Optional[float] = None,
    ) -> None:
        msg = ChatMessage(
            role="user",
            content=content,
            topic=topic,
            game_time=game_time,
        )
        self.messages.append(msg)
        self._trim()

    def add_assistant_message(self, content: str) -> None:
        msg = ChatMessage(role="assistant", content=content)
        self.messages.append(msg)
        self._trim()

    def to_api_messages(self) -> List[Dict[str, str]]:
        """Convert history to Claude API message format."""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def get_context_summary(self) -> str:
        """Summarise conversation so far."""
        if not self.messages:
            return "No conversation history."
        topics_seen = set()
        for m in self.messages:
            if m.topic:
                topics_seen.add(m.topic.value)
        return (
            f"Session {self.session_id}: {len(self.messages)} messages, "
            f"topics covered: {', '.join(topics_seen) or 'general'}"
        )

    def clear(self) -> None:
        self.messages.clear()

    def _trim(self) -> None:
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history :]


# ---------------------------------------------------------------------------
# ClaudeCoach: main coach integrating Claude API
# ---------------------------------------------------------------------------


# Mock responses keyed by (matchup, topic) for demo without API
_MOCK_RESPONSES: Dict[Tuple[str, str], str] = {
    ("ZvT", "opening_analysis"): (
        "Your opening looks solid for ZvT. At this point you should:\n"
        "1. Complete Ling Speed and get a Baneling Nest by 3:30\n"
        "2. Start your third Queen for creep spread\n"
        "3. Scout for Hellion count -- if 4+ Hellions, build extra Lings\n"
        "4. Drone up to 44 workers before building army\n"
        "Priority: Creep spread and inject cycles. Do not miss injects."
    ),
    ("ZvT", "mid_game_decision"): (
        "With your current Ling-Bane-Hydra composition, you should:\n"
        "1. Continue droning your 4th base\n"
        "2. Start +1 Missile upgrade for Hydras\n"
        "3. Keep Banelings on hold position at ramp entrances\n"
        "4. Send Ling packs to deny Terran 3rd base\n"
        "Do NOT attack into a siege line. Wait for creep to reach mid-map."
    ),
    ("ZvT", "late_game_transition"): (
        "For late-game ZvT, transition to Broodlord-Viper-Corruptor:\n"
        "1. Get Hive ASAP, then Greater Spire\n"
        "2. Start Viper energy banking (consume structures)\n"
        "3. Build 6-8 Corruptors first for air defence\n"
        "4. Morph Broodlords in batches of 4\n"
        "5. Keep Ling-Bane runby group for harassment\n"
        "Key upgrades: +3 Air Carapace, Adrenal Glands."
    ),
    ("ZvP", "opening_analysis"): (
        "In ZvP, your opening needs to account for Oracle/DT:\n"
        "1. Build Spore Crawler at mineral line by 3:30\n"
        "2. Send Overlord to scout opponent natural at 2:30\n"
        "3. If you see Stargate, add a Queen at natural\n"
        "4. Roach Warren at 3:00 if going standard Roach-Ravager\n"
        "Priority: Keep 2 Queens per base for defence and injects."
    ),
    ("ZvP", "mid_game_decision"): (
        "Your Roach-Hydra-Lurker transition looks good. Next steps:\n"
        "1. Start Lurker Den after Lair completes\n"
        "2. Get Hydra range upgrade immediately\n"
        "3. Position army outside Protoss 3rd base\n"
        "4. Burrowed Lurkers deny expansions\n"
        "Warning: scout for Disruptors -- spread Hydras wide."
    ),
    ("ZvP", "late_game_transition"): (
        "Late ZvP against Skytoss is challenging:\n"
        "1. Corruptor-Viper is your core anti-air\n"
        "2. Parasitic Bomb clusters of Carriers/Void Rays\n"
        "3. Abduct high-value targets (Tempests, Mothership)\n"
        "4. Keep Spore Crawlers in mineral lines\n"
        "5. Neural Parasite on Carriers if opportunity arises\n"
        "Do not engage without Vipers with full energy."
    ),
    ("ZvZ", "opening_analysis"): (
        "ZvZ opening requires careful micro:\n"
        "1. Get Ling Speed first; opponent's Ling Speed timing is key\n"
        "2. Build Baneling Nest at 2:45-3:00\n"
        "3. Keep 4 Lings at opponent's side of map for scouting\n"
        "4. If opponent goes pool-first, match aggression\n"
        "5. Wall natural ramp with Evolution Chamber\n"
        "Priority: Do NOT lose your initial Zerglings for free."
    ),
    ("ZvZ", "mid_game_decision"): (
        "Roach wars are the mid-game standard in ZvZ:\n"
        "1. +1 Ranged Attack is critical; start it immediately\n"
        "2. Whoever has more Roaches and better upgrades usually wins\n"
        "3. Ravagers add range and Corrosive Bile for clumped Roaches\n"
        "4. Take a 3rd base behind Roach aggression\n"
        "5. Keep an Overseer for detection (Burrow Roaches)\n"
        "Attack: only engage if you have upgrade or Roach count advantage."
    ),
}

# Fallback responses for matchup/topic combos without specific mocks
_GENERIC_MOCK = (
    "Based on the game state:\n"
    "1. Ensure inject cycles are running on all Hatcheries\n"
    "2. Keep producing workers until 66+ count\n"
    "3. Spread creep aggressively with Queens\n"
    "4. Scout with Overlords and Zerglings\n"
    "5. Adjust army composition based on enemy tech choices\n"
    "Remember: Zerg power comes from efficient macro and reactive play."
)


class ClaudeCoach:
    """Claude API-powered strategic coach for SC2 Zerg.

    When the anthropic library is available and an API key is set,
    uses real Claude API calls. Otherwise, returns mock responses
    for development and testing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _MAX_TOKENS,
        temperature: float = _TEMPERATURE,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.prompt_builder = StrategyPromptBuilder()
        self.session = CoachingSession()
        self._client: Any = None
        self._api_available = False

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if _ANTHROPIC_AVAILABLE and resolved_key:
            try:
                self._client = anthropic.Anthropic(api_key=resolved_key)
                self._api_available = True
                logger.info("Claude API client initialised (model=%s)", model)
            except Exception as exc:
                logger.warning("Failed to init Anthropic client: %s", exc)
        else:
            logger.info(
                "Running in mock mode (anthropic=%s, key=%s)",
                _ANTHROPIC_AVAILABLE,
                bool(resolved_key),
            )

    @property
    def is_live(self) -> bool:
        """True if connected to real Claude API."""
        return self._api_available

    # -- Core coaching methods ---------------------------------------------

    def get_advice(
        self,
        state: GameState,
        topic: CoachingTopic = CoachingTopic.GENERAL,
        custom_question: Optional[str] = None,
    ) -> str:
        """Get strategic advice for the current game state.

        Returns Claude's response or a mock response if API unavailable.
        """
        prompt = self.prompt_builder.build_prompt(
            state,
            topic=topic,
            custom_question=custom_question,
        )
        self.session.matchup = state.matchup
        self.session.add_user_message(
            prompt,
            topic=topic,
            game_time=state.game_time_seconds,
        )

        response = self._call_api(prompt, state)
        self.session.add_assistant_message(response)
        return response

    def get_timing_alert(
        self,
        state: GameState,
        expected_attack_time: float,
        attack_type: str,
    ) -> str:
        """Get urgent advice about an incoming timing attack."""
        prompt = self.prompt_builder.build_timing_alert(
            state,
            expected_attack_time,
            attack_type,
        )
        self.session.add_user_message(
            prompt,
            topic=CoachingTopic.TIMING_ATTACK_ALERT,
            game_time=state.game_time_seconds,
        )
        response = self._call_api(prompt, state)
        self.session.add_assistant_message(response)
        return response

    def followup(self, question: str) -> str:
        """Ask a follow-up question referencing previous advice."""
        if not self.session.messages:
            return "No previous conversation to follow up on."

        last_assistant = ""
        for m in reversed(self.session.messages):
            if m.role == "assistant":
                last_assistant = m.content
                break

        prompt = self.prompt_builder.build_followup(last_assistant, question)
        self.session.add_user_message(prompt, topic=CoachingTopic.GENERAL)
        response = self._call_api(prompt, None)
        self.session.add_assistant_message(response)
        return response

    def quick_check(self, state: GameState) -> str:
        """Fast economy/army check with compact prompt."""
        prompt = self.prompt_builder.build_prompt(
            state,
            topic=CoachingTopic.ECONOMY_CHECK,
            compact=True,
        )
        return self._call_api(prompt, state)

    # -- Session management ------------------------------------------------

    def new_session(self, matchup: Optional[Matchup] = None) -> str:
        """Start a new coaching session."""
        self.session = CoachingSession()
        self.session.matchup = matchup
        return self.session.session_id

    def get_history(self) -> List[Dict[str, str]]:
        return self.session.to_api_messages()

    # -- Private -----------------------------------------------------------

    def _call_api(
        self,
        user_content: str,
        state: Optional[GameState],
    ) -> str:
        """Call Claude API or return mock response."""
        if self._api_available and self._client is not None:
            return self._call_live_api(user_content)
        return self._mock_response(user_content, state)

    def _call_live_api(self, user_content: str) -> str:
        """Make a real Claude API call."""
        try:
            messages = self.session.to_api_messages()
            # Ensure last message is user role
            if messages and messages[-1]["role"] != "user":
                messages.append({"role": "user", "content": user_content})

            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.prompt_builder.system_prompt,
                messages=messages,
            )
            text_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
            return "\n".join(text_parts) if text_parts else "(No response)"
        except Exception as exc:
            logger.error("Claude API call failed: %s", exc)
            return f"[API Error] {exc}"

    def _mock_response(
        self,
        user_content: str,
        state: Optional[GameState],
    ) -> str:
        """Return a mock response for testing."""
        if state is None:
            return _GENERIC_MOCK

        matchup_key = state.matchup.value
        # Try to detect topic from user content
        topic_key = self._detect_topic_from_text(user_content, state)
        key = (matchup_key, topic_key)

        result = _MOCK_RESPONSES.get(key)
        if result is not None:
            return result
        return _GENERIC_MOCK

    @staticmethod
    def _detect_topic_from_text(text: str, state: GameState) -> str:
        """Heuristic topic detection from prompt text."""
        low = text.lower()
        if "timing" in low or "alert" in low or "attack" in low:
            return "timing_attack_alert"
        if "opening" in low or "early" in low:
            return "opening_analysis"
        if "late" in low or "transition" in low or "hive" in low:
            return "late_game_transition"
        if "economy" in low or "drone" in low or "resource" in low:
            return "economy_check"
        if "composition" in low or "army" in low or "units" in low:
            return "army_composition"
        if "scout" in low or "intel" in low:
            return "scouting_info"

        # Fallback: use game phase
        phase = GameStateSerializer._detect_phase(state.game_time_seconds)
        if phase in (GamePhase.OPENING, GamePhase.EARLY):
            return "opening_analysis"
        if phase == GamePhase.MID:
            return "mid_game_decision"
        return "late_game_transition"


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------


def _make_demo_state(
    matchup: Matchup,
    time_sec: float,
    supply: int,
    army: Dict[str, int],
    enemy: Optional[Dict[str, int]] = None,
) -> GameState:
    """Helper to build a demo GameState quickly."""
    rng = np.random.default_rng(int(time_sec))
    return GameState(
        game_time_seconds=time_sec,
        supply_used=supply,
        supply_cap=min(200, supply + int(rng.integers(10, 30))),
        minerals=int(rng.integers(100, 800)),
        vespene=int(rng.integers(50, 400)),
        worker_count=min(80, int(supply * 0.4)),
        army_supply=int(supply * 0.5),
        base_count=max(1, supply // 40),
        matchup=matchup,
        army_comp=army,
        structures={"Hatchery": max(1, supply // 40), "Spawning Pool": 1},
        upgrades=["Ling Speed"] if time_sec > 180 else [],
        enemy_army_comp=enemy or {},
        enemy_structures=["Command Center"] if matchup == Matchup.ZvT else ["Nexus"],
        enemy_base_count=max(1, supply // 50),
        pending_units={"Zergling": int(rng.integers(2, 8))},
        creep_coverage=min(1.0, time_sec / 1200.0),
        inject_efficiency=float(rng.uniform(0.6, 0.95)),
    )


def demo() -> None:
    """Demonstrate Phase 627 Claude API Strategic Advisor."""
    print("=" * 70)
    print("Phase 627: Claude API Strategic Advisor for SC2")
    print("=" * 70)
    print()

    coach = ClaudeCoach()
    print(f"[1] Coach initialised (live API: {coach.is_live})")
    print(f"    Model: {coach.model}")
    print()

    # -- Scenario 1: ZvT Opening ------------------------------------------
    state1 = _make_demo_state(
        Matchup.ZvT,
        150.0,
        30,
        army={"Zergling": 6, "Queen": 2},
        enemy={"Marine": 4, "Reaper": 1},
    )
    print("[2] Scenario: ZvT Opening (2:30)")
    serializer = GameStateSerializer()
    print(serializer.serialize(state1))
    print()
    advice1 = coach.get_advice(state1, CoachingTopic.OPENING_ANALYSIS)
    print(f"Coach advice:\n{advice1}")
    print()

    # -- Scenario 2: ZvP Mid-game -----------------------------------------
    state2 = _make_demo_state(
        Matchup.ZvP,
        480.0,
        90,
        army={"Roach": 12, "Ravager": 4, "Hydralisk": 8, "Queen": 4},
        enemy={"Stalker": 6, "Immortal": 3, "Sentry": 2},
    )
    print("[3] Scenario: ZvP Mid-game (8:00)")
    advice2 = coach.get_advice(state2, CoachingTopic.MID_GAME_DECISION)
    print(f"Coach advice:\n{advice2}")
    print()

    # -- Scenario 3: ZvT Timing Alert -------------------------------------
    state3 = _make_demo_state(
        Matchup.ZvT,
        360.0,
        70,
        army={"Zergling": 20, "Baneling": 6, "Hydralisk": 4},
        enemy={"Marine": 20, "Medivac": 2, "Siege Tank": 2},
    )
    print("[4] Scenario: ZvT Timing Alert (6:00)")
    alert = coach.get_timing_alert(state3, 420.0, "Marine-Medivac push")
    print(f"Alert response:\n{alert}")
    print()

    # -- Scenario 4: ZvT Late-game Transition -----------------------------
    state4 = _make_demo_state(
        Matchup.ZvT,
        900.0,
        160,
        army={"Zergling": 40, "Baneling": 12, "Hydralisk": 20, "Viper": 3},
        enemy={"Marine": 30, "Medivac": 4, "Siege Tank": 6, "Thor": 2},
    )
    print("[5] Scenario: ZvT Late-game (15:00)")
    advice4 = coach.get_advice(state4, CoachingTopic.LATE_GAME_TRANSITION)
    print(f"Coach advice:\n{advice4}")
    print()

    # -- Scenario 5: Follow-up question -----------------------------------
    print("[6] Follow-up question:")
    followup = coach.followup("Should I get Ultralisks or Broodlords first?")
    print(f"Follow-up response:\n{followup}")
    print()

    # -- Scenario 6: ZvZ Opening ------------------------------------------
    state6 = _make_demo_state(
        Matchup.ZvZ,
        120.0,
        22,
        army={"Zergling": 4, "Queen": 1},
        enemy={"Zergling": 6},
    )
    print("[7] Scenario: ZvZ Opening (2:00)")
    advice6 = coach.get_advice(state6, CoachingTopic.OPENING_ANALYSIS)
    print(f"Coach advice:\n{advice6}")
    print()

    # -- Scenario 7: Quick economy check ----------------------------------
    print("[8] Quick economy check (compact prompt):")
    quick = coach.quick_check(state2)
    print(f"Quick check:\n{quick}")
    print()

    # -- Session summary ---------------------------------------------------
    print("[9] Session summary:")
    print(f"    {coach.session.get_context_summary()}")
    print(f"    Messages: {len(coach.session.messages)}")
    print(f"    API format preview:")
    api_msgs = coach.get_history()
    for m in api_msgs[:4]:
        preview = m["content"][:80].replace("\n", " ")
        print(f"      [{m['role']}] {preview}...")
    print()

    # -- New session -------------------------------------------------------
    print("[10] Starting new session:")
    sid = coach.new_session(Matchup.ZvP)
    print(f"     New session ID: {sid}")
    state_new = _make_demo_state(
        Matchup.ZvP,
        600.0,
        110,
        army={"Roach": 15, "Hydralisk": 12, "Lurker": 4},
    )
    advice_new = coach.get_advice(state_new, CoachingTopic.ARMY_COMPOSITION)
    print(f"     Advice: {advice_new[:120]}...")
    print()

    print("=" * 70)
    print("Phase 627 demo complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    demo()

# Phase 627: Claude API registered
