# =============================================================
# SC2 Bot AI Inference — Mojo (Python superset)
# High-performance action inference with SIMD + parallelize
# Target: 10x Python speedup via strict fn, SIMD, vectorized ops
# =============================================================

from tensor import Tensor, TensorShape, TensorSpec
from math import sqrt, exp, tanh
from algorithm import parallelize, vectorize
from sys.intrinsics import strided_load
from memory import memset_zero, stack_allocation
from random import rand

alias DType_f32 = DType.float32
alias SIMD8 = SIMD[DType_f32, 8]

# ── Constants ──────────────────────────────────────────────────────────
alias INPUT_DIM   : Int = 128   # observation vector size
alias HIDDEN_DIM  : Int = 256   # hidden layer width
alias ACTION_DIM  : Int = 64    # number of discrete actions
alias BATCH_SIZE  : Int = 32    # parallel inference batch

# ── Action enum (mirrors python-sc2 AbilityId mapping) ────────────────
alias ACTION_ATTACK_MOVE : Int = 0
alias ACTION_EXPAND      : Int = 1
alias ACTION_TRAIN_DRONE  : Int = 2
alias ACTION_TRAIN_LING   : Int = 3
alias ACTION_TRAIN_ROACH  : Int = 4
alias ACTION_INJECT       : Int = 5
alias ACTION_RETREAT      : Int = 6
alias ACTION_HARASS       : Int = 7

# ── Struct: SC2Observation ─────────────────────────────────────────────
@value
struct SC2Observation:
    var minerals:     Float32
    var gas:          Float32
    var supply_used:  Float32
    var supply_cap:   Float32
    var army_supply:  Float32
    var worker_count: Float32
    var enemy_army:   Float32
    var game_time:    Float32

    fn to_tensor(self) -> Tensor[DType_f32]:
        var t = Tensor[DType_f32](TensorShape(8))
        t[0] = self.minerals     / 1800.0   # normalize to [0,1]
        t[1] = self.gas          / 1800.0
        t[2] = self.supply_used  / 200.0
        t[3] = self.supply_cap   / 200.0
        t[4] = self.army_supply  / 200.0
        t[5] = self.worker_count / 80.0
        t[6] = self.enemy_army   / 200.0
        t[7] = self.game_time    / 2000.0
        return t

# ── Struct: LayerWeights ───────────────────────────────────────────────
@value
struct LayerWeights:
    var weight: Tensor[DType_f32]
    var bias:   Tensor[DType_f32]

    fn __init__(inout self, in_dim: Int, out_dim: Int):
        self.weight = Tensor[DType_f32](TensorShape(in_dim, out_dim))
        self.bias   = Tensor[DType_f32](TensorShape(out_dim))
        rand(self.weight.data(), in_dim * out_dim)
        rand(self.bias.data(), out_dim)

# ── SIMD relu activation ───────────────────────────────────────────────
@always_inline
fn relu_simd(x: SIMD8) -> SIMD8:
    return x.max(SIMD8(0.0))

# ── Vectorized linear layer forward pass ──────────────────────────────
fn linear_forward(
    input:  Tensor[DType_f32],
    weight: Tensor[DType_f32],
    bias:   Tensor[DType_f32],
    out:    Tensor[DType_f32],
    in_dim: Int,
    out_dim: Int,
):
    # Vectorize over output dimension using SIMD width 8
    @parameter
    fn compute_row(o: Int):
        var acc = SIMD8(0.0)
        let base = o * in_dim
        @parameter
        fn dot_simd[simd_width: Int](i: Int):
            let w_vec = weight.simd_load[simd_width](base + i)
            let x_vec = input.simd_load[simd_width](i)
            acc = acc + (w_vec * x_vec).reduce_add()
        vectorize[dot_simd, 8](in_dim)
        out[o] = acc.reduce_add() + bias[o]

    parallelize[compute_row](out_dim)

# ── Struct: SC2Model ───────────────────────────────────────────────────
struct SC2Model:
    var fc1:   LayerWeights
    var fc2:   LayerWeights
    var fc_out: LayerWeights

    # Hidden activation buffers
    var _h1: Tensor[DType_f32]
    var _h2: Tensor[DType_f32]
    var _logits: Tensor[DType_f32]

    fn __init__(inout self):
        self.fc1    = LayerWeights(INPUT_DIM,  HIDDEN_DIM)
        self.fc2    = LayerWeights(HIDDEN_DIM, HIDDEN_DIM)
        self.fc_out = LayerWeights(HIDDEN_DIM, ACTION_DIM)
        self._h1     = Tensor[DType_f32](TensorShape(HIDDEN_DIM))
        self._h2     = Tensor[DType_f32](TensorShape(HIDDEN_DIM))
        self._logits = Tensor[DType_f32](TensorShape(ACTION_DIM))

    # ── Strict fn: vectorized single-sample forward pass ──────────────
    fn forward(inout self, obs: Tensor[DType_f32]) -> Tensor[DType_f32]:
        # Layer 1: fc1 + ReLU
        linear_forward(obs, self.fc1.weight, self.fc1.bias,
                        self._h1, INPUT_DIM, HIDDEN_DIM)
        @parameter
        fn relu1[w: Int](i: Int):
            self._h1.simd_store[w](i, relu_simd(self._h1.simd_load[w](i)))
        vectorize[relu1, 8](HIDDEN_DIM)

        # Layer 2: fc2 + ReLU
        linear_forward(self._h1, self.fc2.weight, self.fc2.bias,
                        self._h2, HIDDEN_DIM, HIDDEN_DIM)
        @parameter
        fn relu2[w: Int](i: Int):
            self._h2.simd_store[w](i, relu_simd(self._h2.simd_load[w](i)))
        vectorize[relu2, 8](HIDDEN_DIM)

        # Output layer (no activation — raw logits)
        linear_forward(self._h2, self.fc_out.weight, self.fc_out.bias,
                        self._logits, HIDDEN_DIM, ACTION_DIM)
        return self._logits

    # ── fn infer_action: argmax over logits with SIMD ─────────────────
    fn infer_action(inout self, obs: SC2Observation) -> Int:
        let obs_tensor = obs.to_tensor()

        # Pad obs to INPUT_DIM
        var input = Tensor[DType_f32](TensorShape(INPUT_DIM))
        memset_zero(input.data(), INPUT_DIM)
        for i in range(8):
            input[i] = obs_tensor[i]

        let logits = self.forward(input)

        # SIMD argmax
        var best_val: Float32 = logits[0]
        var best_idx: Int = 0
        @parameter
        fn find_max[simd_width: Int](i: Int):
            let vals = logits.simd_load[simd_width](i)
            # Per-lane comparison
            for lane in range(simd_width):
                let v = vals[lane]
                if v > best_val:
                    best_val = v
                    best_idx = i + lane
        vectorize[find_max, 8](ACTION_DIM)
        return best_idx

    # ── fn batch_predict: parallel inference over a batch ─────────────
    fn batch_predict(inout self, observations: Tensor[DType_f32]) -> Tensor[DType_f32]:
        """
        observations: shape [BATCH_SIZE, INPUT_DIM]
        returns:      shape [BATCH_SIZE]  (action indices as Float32)
        """
        var results = Tensor[DType_f32](TensorShape(BATCH_SIZE))

        @parameter
        fn infer_one(b: Int):
            # Extract slice for batch item b
            var obs_slice = Tensor[DType_f32](TensorShape(INPUT_DIM))
            let offset = b * INPUT_DIM
            for i in range(INPUT_DIM):
                obs_slice[i] = observations[offset + i]

            # Forward pass
            var h1 = Tensor[DType_f32](TensorShape(HIDDEN_DIM))
            var h2 = Tensor[DType_f32](TensorShape(HIDDEN_DIM))
            var logits = Tensor[DType_f32](TensorShape(ACTION_DIM))

            linear_forward(obs_slice, self.fc1.weight, self.fc1.bias,
                            h1, INPUT_DIM, HIDDEN_DIM)
            linear_forward(h1, self.fc2.weight, self.fc2.bias,
                            h2, HIDDEN_DIM, HIDDEN_DIM)
            linear_forward(h2, self.fc_out.weight, self.fc_out.bias,
                            logits, HIDDEN_DIM, ACTION_DIM)

            # Argmax
            var best_val: Float32 = logits[0]
            var best_idx: Int = 0
            for i in range(ACTION_DIM):
                if logits[i] > best_val:
                    best_val = logits[i]
                    best_idx = i
            results[b] = Float32(best_idx)

        parallelize[infer_one](BATCH_SIZE)
        return results

# ── Softmax utility (for probability output) ──────────────────────────
fn softmax(logits: Tensor[DType_f32], out: Tensor[DType_f32], size: Int):
    var max_val: Float32 = logits[0]
    for i in range(size):
        if logits[i] > max_val:
            max_val = logits[i]
    var sum_exp: Float32 = 0.0
    for i in range(size):
        let e = exp(logits[i] - max_val)
        out[i] = e
        sum_exp += e
    for i in range(size):
        out[i] /= sum_exp

# ── Main entry ─────────────────────────────────────────────────────────
fn main():
    var model = SC2Model()

    # Single-sample inference
    let obs = SC2Observation(
        minerals=600.0,
        gas=200.0,
        supply_used=44.0,
        supply_cap=66.0,
        army_supply=20.0,
        worker_count=22.0,
        enemy_army=16.0,
        game_time=210.0,
    )
    let action = model.infer_action(obs)
    print("Inferred action index:", action)

    # Batch inference
    var batch_obs = Tensor[DType_f32](TensorShape(BATCH_SIZE, INPUT_DIM))
    rand(batch_obs.data(), BATCH_SIZE * INPUT_DIM)
    let actions = model.batch_predict(batch_obs)
    print("Batch inference complete. First action:", actions[0])
