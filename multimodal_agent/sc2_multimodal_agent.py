"""
Phase 633: Multimodal Agent for SC2 (Vision + Text + State)

Combines minimap vision encoding, strategy text encoding, and structured
numeric game-state encoding via late fusion for decision making.
All networks are plain PyTorch-compatible Python (numpy-based fallback
included for environments without torch).
"""

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

# ---------------------------------------------------------------------------
# Lightweight tensor helpers (numpy-free, pure Python fallback)
# ---------------------------------------------------------------------------


class Vector:
    """Minimal 1-D float vector with basic linear-algebra ops."""

    __slots__ = ("data",)

    def __init__(self, data: List[float]):
        self.data = list(data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> float:
        return self.data[idx]

    def __repr__(self) -> str:
        short = self.data[:6]
        suffix = ", ..." if len(self.data) > 6 else ""
        return f"Vector([{', '.join(f'{v:.4f}' for v in short)}{suffix}], dim={len(self.data)})"

    # arithmetic
    def __add__(self, other: "Vector") -> "Vector":
        return Vector([a + b for a, b in zip(self.data, other.data)])

    def __sub__(self, other: "Vector") -> "Vector":
        return Vector([a - b for a, b in zip(self.data, other.data)])

    def __mul__(self, scalar: float) -> "Vector":
        return Vector([v * scalar for v in self.data])

    def dot(self, other: "Vector") -> float:
        return sum(a * b for a, b in zip(self.data, other.data))

    def norm(self) -> float:
        return math.sqrt(self.dot(self))

    def normalize(self) -> "Vector":
        n = self.norm()
        if n < 1e-9:
            return Vector([0.0] * len(self.data))
        return Vector([v / n for v in self.data])

    def relu(self) -> "Vector":
        return Vector([max(0.0, v) for v in self.data])

    def tanh(self) -> "Vector":
        return Vector([math.tanh(v) for v in self.data])

    def sigmoid(self) -> "Vector":
        return Vector(
            [1.0 / (1.0 + math.exp(-max(-500, min(500, v)))) for v in self.data]
        )

    @staticmethod
    def zeros(dim: int) -> "Vector":
        return Vector([0.0] * dim)

    @staticmethod
    def random_normal(dim: int, std: float = 0.1) -> "Vector":
        return Vector([random.gauss(0, std) for _ in range(dim)])

    @staticmethod
    def concat(vectors: List["Vector"]) -> "Vector":
        out: List[float] = []
        for v in vectors:
            out.extend(v.data)
        return Vector(out)


class Matrix:
    """Minimal 2-D weight matrix (rows x cols)."""

    __slots__ = ("rows", "cols", "data")

    def __init__(self, rows: int, cols: int, data: Optional[List[List[float]]] = None):
        self.rows = rows
        self.cols = cols
        if data is not None:
            self.data = [list(r) for r in data]
        else:
            std = math.sqrt(2.0 / (rows + cols))
            self.data = [
                [random.gauss(0, std) for _ in range(cols)] for _ in range(rows)
            ]

    def forward(self, x: Vector) -> Vector:
        """Matrix-vector multiply: y = Wx."""
        assert (
            len(x) == self.cols
        ), f"Shape mismatch: matrix cols={self.cols}, vec dim={len(x)}"
        out = []
        for row in self.data:
            out.append(sum(r * v for r, v in zip(row, x.data)))
        return Vector(out)


# ---------------------------------------------------------------------------
# Linear layer with optional bias
# ---------------------------------------------------------------------------


class LinearLayer:
    """Fully-connected layer: y = Wx + b."""

    def __init__(self, in_dim: int, out_dim: int, use_bias: bool = True):
        self.weight = Matrix(out_dim, in_dim)
        self.bias = Vector.zeros(out_dim) if use_bias else None

    def forward(self, x: Vector) -> Vector:
        y = self.weight.forward(x)
        if self.bias is not None:
            y = y + self.bias
        return y


# ---------------------------------------------------------------------------
# Activation helpers
# ---------------------------------------------------------------------------


def relu(v: Vector) -> Vector:
    return v.relu()


def tanh(v: Vector) -> Vector:
    return v.tanh()


def softmax(v: Vector) -> Vector:
    max_val = max(v.data)
    exps = [math.exp(x - max_val) for x in v.data]
    total = sum(exps)
    return Vector([e / total for e in exps])


def layer_norm(v: Vector, eps: float = 1e-5) -> Vector:
    mean = sum(v.data) / len(v.data)
    var = sum((x - mean) ** 2 for x in v.data) / len(v.data)
    std = math.sqrt(var + eps)
    return Vector([(x - mean) / std for x in v.data])


# ---------------------------------------------------------------------------
# Vision Encoder
# ---------------------------------------------------------------------------


class VisionEncoder:
    """
    Encodes a minimap screenshot (represented as a flat pixel grid)
    into a fixed-size feature vector.

    Pipeline:  flatten -> linear -> relu -> linear -> relu -> norm
    In production this would be a CNN; here we use MLPs as a lightweight
    stand-in compatible with any Python environment.
    """

    def __init__(
        self,
        grid_height: int = 16,
        grid_width: int = 16,
        channels: int = 3,
        hidden_dim: int = 128,
        output_dim: int = 64,
    ):
        self.grid_height = grid_height
        self.grid_width = grid_width
        self.channels = channels
        self.input_dim = grid_height * grid_width * channels
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        self.fc1 = LinearLayer(self.input_dim, hidden_dim)
        self.fc2 = LinearLayer(hidden_dim, hidden_dim)
        self.fc3 = LinearLayer(hidden_dim, output_dim)

    def encode(self, pixel_grid: List[List[List[float]]]) -> Vector:
        """
        Encode a minimap image.

        Args:
            pixel_grid: shape [H][W][C] with values in [0, 1].
                        Can also be a flat list of length H*W*C.

        Returns:
            Vector of dimension *output_dim*.
        """
        flat: List[float] = []
        if isinstance(pixel_grid[0], (list, tuple)) and isinstance(
            pixel_grid[0][0], (list, tuple)
        ):
            for row in pixel_grid:
                for pixel in row:
                    flat.extend(pixel)
        else:
            for item in pixel_grid:
                if isinstance(item, (list, tuple)):
                    flat.extend(item)
                else:
                    flat.append(float(item))

        # pad or trim to expected input_dim
        if len(flat) < self.input_dim:
            flat.extend([0.0] * (self.input_dim - len(flat)))
        flat = flat[: self.input_dim]

        x = Vector(flat)
        x = relu(self.fc1.forward(x))
        x = relu(self.fc2.forward(x))
        x = self.fc3.forward(x)
        return layer_norm(x)

    def encode_flat(self, flat_pixels: List[float]) -> Vector:
        """Convenience: encode from already-flattened pixels."""
        return self.encode([flat_pixels])


# ---------------------------------------------------------------------------
# Text Encoder
# ---------------------------------------------------------------------------


class TextEncoder:
    """
    Encodes strategy descriptions or chat text into a feature vector.

    Approach: bag-of-words with learned (random-init) embeddings,
    followed by a two-layer MLP.  In production, replace with a
    pretrained language model.
    """

    def __init__(
        self,
        vocab_size: int = 2000,
        embed_dim: int = 32,
        hidden_dim: int = 64,
        output_dim: int = 64,
    ):
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.output_dim = output_dim

        # random embedding table
        self._embeddings: List[Vector] = [
            Vector.random_normal(embed_dim, std=0.3) for _ in range(vocab_size)
        ]
        self.fc1 = LinearLayer(embed_dim, hidden_dim)
        self.fc2 = LinearLayer(hidden_dim, output_dim)

    def _token_hash(self, token: str) -> int:
        """Deterministic hash of a token to a vocab index."""
        h = 0
        for ch in token:
            h = (h * 31 + ord(ch)) % self.vocab_size
        return h

    def tokenize(self, text: str) -> List[int]:
        """Simple whitespace tokenizer with hash-based vocab mapping."""
        tokens = text.lower().strip().split()
        return [self._token_hash(t) for t in tokens]

    def encode(self, text: str) -> Vector:
        """
        Encode a text string into a fixed-size vector.

        Steps: tokenize -> embed -> mean-pool -> MLP -> norm
        """
        ids = self.tokenize(text)
        if not ids:
            return Vector.zeros(self.output_dim)

        # mean-pool embeddings
        pool = Vector.zeros(self.embed_dim)
        for idx in ids:
            pool = pool + self._embeddings[idx]
        pool = pool * (1.0 / len(ids))

        x = relu(self.fc1.forward(pool))
        x = self.fc2.forward(x)
        return layer_norm(x)


# ---------------------------------------------------------------------------
# Structured (Numeric) Encoder
# ---------------------------------------------------------------------------


class StructuredEncoder:
    """
    Encodes numeric SC2 game state (resources, supply, army composition, etc.)
    into a feature vector.
    """

    # The canonical field order for SC2 game state.
    FIELD_NAMES: List[str] = [
        "minerals",
        "vespene",
        "supply_used",
        "supply_cap",
        "worker_count",
        "army_supply",
        "army_value_minerals",
        "army_value_gas",
        "enemy_army_supply_estimate",
        "enemy_worker_estimate",
        "bases_count",
        "enemy_bases_count",
        "tech_progress",  # 0..1
        "upgrade_progress",  # 0..1
        "game_time_seconds",
        "idle_workers",
    ]

    # normalization ranges (min, max) for each field
    FIELD_RANGES: Dict[str, Tuple[float, float]] = {
        "minerals": (0.0, 5000.0),
        "vespene": (0.0, 5000.0),
        "supply_used": (0.0, 200.0),
        "supply_cap": (0.0, 200.0),
        "worker_count": (0.0, 90.0),
        "army_supply": (0.0, 200.0),
        "army_value_minerals": (0.0, 15000.0),
        "army_value_gas": (0.0, 10000.0),
        "enemy_army_supply_estimate": (0.0, 200.0),
        "enemy_worker_estimate": (0.0, 90.0),
        "bases_count": (0.0, 8.0),
        "enemy_bases_count": (0.0, 8.0),
        "tech_progress": (0.0, 1.0),
        "upgrade_progress": (0.0, 1.0),
        "game_time_seconds": (0.0, 1800.0),
        "idle_workers": (0.0, 30.0),
    }

    def __init__(self, hidden_dim: int = 64, output_dim: int = 64):
        self.input_dim = len(self.FIELD_NAMES)
        self.output_dim = output_dim
        self.fc1 = LinearLayer(self.input_dim, hidden_dim)
        self.fc2 = LinearLayer(hidden_dim, hidden_dim)
        self.fc3 = LinearLayer(hidden_dim, output_dim)

    def _normalize(self, name: str, value: float) -> float:
        lo, hi = self.FIELD_RANGES.get(name, (0.0, 1.0))
        if hi - lo < 1e-9:
            return 0.0
        return max(0.0, min(1.0, (value - lo) / (hi - lo)))

    def encode(self, state: Dict[str, float]) -> Vector:
        """
        Encode a dictionary of game-state fields into a fixed-size vector.
        Missing fields default to 0.
        """
        raw: List[float] = []
        for name in self.FIELD_NAMES:
            val = state.get(name, 0.0)
            raw.append(self._normalize(name, val))

        x = Vector(raw)
        x = relu(self.fc1.forward(x))
        x = relu(self.fc2.forward(x))
        x = self.fc3.forward(x)
        return layer_norm(x)


# ---------------------------------------------------------------------------
# Late Fusion Network
# ---------------------------------------------------------------------------


class FusionNetwork:
    """
    Combines feature vectors from all modalities via late fusion
    (concatenation + MLP) to produce a unified representation.
    """

    def __init__(
        self,
        vision_dim: int = 64,
        text_dim: int = 64,
        state_dim: int = 64,
        hidden_dim: int = 128,
        output_dim: int = 64,
    ):
        self.concat_dim = vision_dim + text_dim + state_dim
        self.output_dim = output_dim

        self.fc1 = LinearLayer(self.concat_dim, hidden_dim)
        self.fc2 = LinearLayer(hidden_dim, hidden_dim)
        self.fc3 = LinearLayer(hidden_dim, output_dim)

        # modality-specific gates (learned scalars approximated as linear projections)
        self.gate_vision = LinearLayer(vision_dim, 1, use_bias=True)
        self.gate_text = LinearLayer(text_dim, 1, use_bias=True)
        self.gate_state = LinearLayer(state_dim, 1, use_bias=True)

    def _gate_value(self, gate: LinearLayer, feat: Vector) -> float:
        raw = gate.forward(feat)
        return 1.0 / (1.0 + math.exp(-max(-500, min(500, raw[0]))))

    def fuse(
        self,
        vision_feat: Vector,
        text_feat: Vector,
        state_feat: Vector,
    ) -> Vector:
        """
        Fuse three modality vectors into a single representation.

        Each modality is gated (sigmoid attention) before concatenation,
        then passed through a shared MLP.
        """
        g_v = self._gate_value(self.gate_vision, vision_feat)
        g_t = self._gate_value(self.gate_text, text_feat)
        g_s = self._gate_value(self.gate_state, state_feat)

        gated_v = vision_feat * g_v
        gated_t = text_feat * g_t
        gated_s = state_feat * g_s

        concat = Vector.concat([gated_v, gated_t, gated_s])
        x = relu(self.fc1.forward(concat))
        x = relu(self.fc2.forward(x))
        x = self.fc3.forward(x)
        return layer_norm(x)


# ---------------------------------------------------------------------------
# Action Head
# ---------------------------------------------------------------------------


class ActionHead:
    """Maps a fused representation to SC2 action probabilities."""

    SC2_ACTIONS: List[str] = [
        "build_workers",
        "build_army",
        "expand",
        "tech_up",
        "attack",
        "defend",
        "scout",
        "harass",
        "retreat",
        "build_static_defense",
        "upgrade",
        "special_ability",
    ]

    def __init__(self, input_dim: int = 64, num_actions: int = 12):
        self.num_actions = num_actions
        self.fc = LinearLayer(input_dim, num_actions)

    def forward(self, fused: Vector) -> Tuple[Vector, int, str]:
        """
        Returns:
            (action_probs, best_action_idx, best_action_name)
        """
        logits = self.fc.forward(fused)
        probs = softmax(logits)
        best_idx = max(range(self.num_actions), key=lambda i: probs[i])
        name = (
            self.SC2_ACTIONS[best_idx]
            if best_idx < len(self.SC2_ACTIONS)
            else f"action_{best_idx}"
        )
        return probs, best_idx, name


# ---------------------------------------------------------------------------
# Multimodal Agent
# ---------------------------------------------------------------------------


class MultimodalAgent:
    """
    Full multimodal SC2 agent: minimap vision + strategy text + numeric state
    are encoded separately, fused, then decoded into an action.
    """

    def __init__(
        self,
        grid_size: int = 16,
        channels: int = 3,
        vocab_size: int = 2000,
        embed_dim: int = 32,
        vision_hidden: int = 128,
        text_hidden: int = 64,
        state_hidden: int = 64,
        feat_dim: int = 64,
        fusion_hidden: int = 128,
        fusion_out: int = 64,
        num_actions: int = 12,
    ):
        self.vision_encoder = VisionEncoder(
            grid_height=grid_size,
            grid_width=grid_size,
            channels=channels,
            hidden_dim=vision_hidden,
            output_dim=feat_dim,
        )
        self.text_encoder = TextEncoder(
            vocab_size=vocab_size,
            embed_dim=embed_dim,
            hidden_dim=text_hidden,
            output_dim=feat_dim,
        )
        self.state_encoder = StructuredEncoder(
            hidden_dim=state_hidden,
            output_dim=feat_dim,
        )
        self.fusion = FusionNetwork(
            vision_dim=feat_dim,
            text_dim=feat_dim,
            state_dim=feat_dim,
            hidden_dim=fusion_hidden,
            output_dim=fusion_out,
        )
        self.action_head = ActionHead(input_dim=fusion_out, num_actions=num_actions)

        self._decision_history: List[Dict[str, Any]] = []

    def decide(
        self,
        minimap: List[List[List[float]]],
        strategy_text: str,
        game_state: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Full forward pass: encode all modalities, fuse, pick action.

        Args:
            minimap: pixel grid [H][W][C], values in [0,1].
            strategy_text: free-form strategy description.
            game_state: dict with keys from StructuredEncoder.FIELD_NAMES.

        Returns:
            Dict with action_name, action_index, probabilities, and
            per-modality feature norms.
        """
        v_feat = self.vision_encoder.encode(minimap)
        t_feat = self.text_encoder.encode(strategy_text)
        s_feat = self.state_encoder.encode(game_state)

        fused = self.fusion.fuse(v_feat, t_feat, s_feat)
        probs, idx, name = self.action_head.forward(fused)

        result = {
            "action_name": name,
            "action_index": idx,
            "probabilities": {
                ActionHead.SC2_ACTIONS[i]: round(probs[i], 4)
                for i in range(len(ActionHead.SC2_ACTIONS))
            },
            "vision_norm": round(v_feat.norm(), 4),
            "text_norm": round(t_feat.norm(), 4),
            "state_norm": round(s_feat.norm(), 4),
            "fused_norm": round(fused.norm(), 4),
        }
        self._decision_history.append(result)
        return result

    def decide_state_only(self, game_state: Dict[str, float]) -> Dict[str, Any]:
        """
        Fallback: decide with only structured state (no vision/text).
        Zero vectors are used for missing modalities.
        """
        dummy_minimap = [
            [[0.0] * self.vision_encoder.channels] * self.vision_encoder.grid_width
        ] * self.vision_encoder.grid_height
        return self.decide(dummy_minimap, "", game_state)

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._decision_history)

    def clear_history(self) -> None:
        self._decision_history.clear()


# ---------------------------------------------------------------------------
# Utility: generate a fake minimap for testing
# ---------------------------------------------------------------------------


def _generate_fake_minimap(
    height: int = 16,
    width: int = 16,
    channels: int = 3,
    seed: int = 42,
) -> List[List[List[float]]]:
    """Create a synthetic minimap with some spatial structure."""
    rng = random.Random(seed)
    grid: List[List[List[float]]] = []
    for y in range(height):
        row: List[List[float]] = []
        for x in range(width):
            # base color depends on quadrant
            base_r = 0.2 if x < width // 2 else 0.7
            base_g = 0.3 if y < height // 2 else 0.6
            base_b = 0.5
            noise = rng.gauss(0, 0.05)
            pixel = [
                max(0.0, min(1.0, base_r + noise)),
                max(0.0, min(1.0, base_g + noise)),
                max(0.0, min(1.0, base_b + noise)),
            ]
            if channels == 1:
                pixel = [sum(pixel) / 3.0]
            row.append(pixel[:channels])
        grid.append(row)
    return grid


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate the Multimodal Agent with synthetic SC2 data."""
    print("=" * 70)
    print("Phase 633: Multimodal Agent for SC2 - Demo")
    print("=" * 70)

    random.seed(123)

    agent = MultimodalAgent(
        grid_size=8,
        channels=3,
        feat_dim=32,
        fusion_hidden=64,
        fusion_out=32,
        num_actions=12,
    )

    # --- Scenario 1: early-game macro ---
    print("\n--- Scenario 1: Early-game macro phase ---")
    minimap1 = _generate_fake_minimap(8, 8, 3, seed=1)
    strategy1 = "Focus on economy and workers, take a fast third base"
    state1 = {
        "minerals": 450,
        "vespene": 120,
        "supply_used": 38,
        "supply_cap": 44,
        "worker_count": 30,
        "army_supply": 8,
        "army_value_minerals": 400,
        "army_value_gas": 100,
        "bases_count": 2,
        "enemy_bases_count": 1,
        "tech_progress": 0.2,
        "game_time_seconds": 180,
        "idle_workers": 2,
    }
    result1 = agent.decide(minimap1, strategy1, state1)
    _print_decision(result1, "Scenario 1")

    # --- Scenario 2: mid-game aggression ---
    print("\n--- Scenario 2: Mid-game aggression ---")
    minimap2 = _generate_fake_minimap(8, 8, 3, seed=2)
    strategy2 = "Attack with roach ravager push, break enemy natural"
    state2 = {
        "minerals": 800,
        "vespene": 500,
        "supply_used": 120,
        "supply_cap": 140,
        "worker_count": 55,
        "army_supply": 65,
        "army_value_minerals": 3500,
        "army_value_gas": 1800,
        "enemy_army_supply_estimate": 50,
        "bases_count": 3,
        "enemy_bases_count": 2,
        "tech_progress": 0.5,
        "game_time_seconds": 420,
        "idle_workers": 0,
    }
    result2 = agent.decide(minimap2, strategy2, state2)
    _print_decision(result2, "Scenario 2")

    # --- Scenario 3: late-game defense ---
    print("\n--- Scenario 3: Late-game defense ---")
    minimap3 = _generate_fake_minimap(8, 8, 3, seed=3)
    strategy3 = "Defend with spore crawlers and vipers, enemy going air"
    state3 = {
        "minerals": 2000,
        "vespene": 1500,
        "supply_used": 190,
        "supply_cap": 200,
        "worker_count": 70,
        "army_supply": 120,
        "army_value_minerals": 8000,
        "army_value_gas": 5000,
        "enemy_army_supply_estimate": 150,
        "bases_count": 5,
        "enemy_bases_count": 4,
        "tech_progress": 0.9,
        "upgrade_progress": 0.8,
        "game_time_seconds": 900,
        "idle_workers": 1,
    }
    result3 = agent.decide(minimap3, strategy3, state3)
    _print_decision(result3, "Scenario 3")

    # --- Scenario 4: state-only fallback ---
    print("\n--- Scenario 4: State-only fallback (no vision/text) ---")
    result4 = agent.decide_state_only(state2)
    _print_decision(result4, "Scenario 4")

    # --- Show encoder details ---
    print("\n--- Encoder dimensions ---")
    print(
        f"  Vision:     input={agent.vision_encoder.input_dim} -> {agent.vision_encoder.output_dim}"
    )
    print(
        f"  Text:       vocab={agent.text_encoder.vocab_size}, embed={agent.text_encoder.embed_dim} -> {agent.text_encoder.output_dim}"
    )
    print(
        f"  Structured: fields={agent.state_encoder.input_dim} -> {agent.state_encoder.output_dim}"
    )
    print(
        f"  Fusion:     concat={agent.fusion.concat_dim} -> {agent.fusion.output_dim}"
    )
    print(
        f"  Actions:    {agent.action_head.num_actions} ({', '.join(ActionHead.SC2_ACTIONS)})"
    )

    # --- Decision history ---
    print(f"\n--- Decision history: {len(agent.get_history())} decisions recorded ---")
    for i, dec in enumerate(agent.get_history()):
        print(f"  [{i}] {dec['action_name']} (fused_norm={dec['fused_norm']})")

    print("\n" + "=" * 70)
    print("Phase 633 demo complete.")
    print("=" * 70)


def _print_decision(result: Dict[str, Any], label: str) -> None:
    """Pretty-print a decision result."""
    print(f"  Decision: {result['action_name']} (idx={result['action_index']})")
    print(
        f"  Feature norms -- vision: {result['vision_norm']}, text: {result['text_norm']}, "
        f"state: {result['state_norm']}, fused: {result['fused_norm']}"
    )
    print("  Top-3 action probabilities:")
    sorted_probs = sorted(
        result["probabilities"].items(), key=lambda kv: kv[1], reverse=True
    )
    for name, prob in sorted_probs[:3]:
        bar = "#" * int(prob * 40)
        print(f"    {name:25s} {prob:.4f} {bar}")


if __name__ == "__main__":
    demo()

# Phase 633: Multimodal registered
