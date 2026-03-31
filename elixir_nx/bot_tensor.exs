#!/usr/bin/env elixir
# Phase 541: Elixir Nx (Numerical Elixir)
# SC2 Bot tensor operations using Nx + Axon

Mix.install([
  # {:nx, "~> 0.7"},
  # {:axon, "~> 0.6"},
  # {:exla, "~> 0.7"},
])

defmodule SC2Bot.Tensor do
  @moduledoc """
  SC2 Bot tensor operations using Nx (Numerical Elixir).
  Provides pure-Elixir fallback when Nx is not available.
  """

  # ─────────────────────────────────────────────
  # Game state encoding
  # ─────────────────────────────────────────────

  @obs_dim 16
  @act_dim 7

  defstruct [
    :minerals, :gas, :supply, :max_supply,
    :workers, :army, :frame, :threat,
    :tech_level, :hatcheries, :bases
  ]

  def encode_state(%{
    minerals: m, gas: g, supply: s, max_supply: ms,
    workers: w, army: a, frame: f, threat: t
  }) do
    [
      clamp(m / 1000.0),
      clamp(g / 500.0),
      clamp(s / 200.0),
      clamp(ms / 200.0),
      clamp(w / 80.0),
      clamp(a / 200.0),
      clamp(f / 20_000.0),
      t,
      0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    ]
  end

  defp clamp(v), do: max(0.0, min(1.0, v))

  # ─────────────────────────────────────────────
  # Simple dot-product policy
  # ─────────────────────────────────────────────

  def softmax(logits) do
    max_l = Enum.max(logits)
    exp_l = Enum.map(logits, &:math.exp(&1 - max_l))
    sum_l = Enum.sum(exp_l)
    Enum.map(exp_l, &(&1 / sum_l))
  end

  def argmax(list) do
    list
    |> Enum.with_index()
    |> Enum.max_by(fn {v, _} -> v end)
    |> elem(1)
  end

  def linear(input, weights) do
    # weights: n_out x n_in
    Enum.map(weights, fn row ->
      Enum.zip(row, input)
      |> Enum.map(fn {w, x} -> w * x end)
      |> Enum.sum()
    end)
  end

  def relu(x) when x > 0, do: x
  def relu(_), do: 0.0

  # ─────────────────────────────────────────────
  # Policy network (2-layer MLP)
  # ─────────────────────────────────────────────

  defmodule PolicyNet do
    @hidden 32

    def init do
      %{
        w1: random_matrix(@hidden, 16),
        w2: random_matrix(7, @hidden),
      }
    end

    def forward(%{w1: w1, w2: w2}, obs) do
      h = obs
          |> SC2Bot.Tensor.linear(w1)
          |> Enum.map(&SC2Bot.Tensor.relu/1)
      SC2Bot.Tensor.linear(h, w2)
    end

    defp random_matrix(rows, cols) do
      for _ <- 1..rows do
        for _ <- 1..cols, do: (:rand.normal() * 0.1)
      end
    end
  end

  # ─────────────────────────────────────────────
  # Decision function
  # ─────────────────────────────────────────────

  def decide(net, state) do
    obs     = encode_state(state)
    logits  = PolicyNet.forward(net, obs)
    probs   = softmax(logits)
    argmax(probs)
  end

  # ─────────────────────────────────────────────
  # Action names
  # ─────────────────────────────────────────────

  @actions ~w(train_drone train_zergling train_roach build_overlord expand attack defend)a

  def action_name(idx), do: Enum.at(@actions, idx, :unknown)
end

defmodule SC2Bot.Economy do
  @doc "Simulate Zerg economy for N frames."
  def simulate(frames \\ 200) do
    initial = %{
      minerals: 50, gas: 0, supply: 12,
      max_supply: 14, workers: 12, army: 0,
      frame: 0, threat: 0.0
    }
    Enum.reduce(1..frames, initial, &tick/2)
  end

  defp tick(_frame, state) do
    income   = div(state.workers * 8, 10)
    new_min  = state.minerals + income
    new_frame = state.frame + 1

    # Simple build decision
    {new_min2, new_workers} =
      cond do
        state.workers < 22 and new_min >= 50 -> {new_min - 50, state.workers + 1}
        true -> {new_min, state.workers}
      end

    %{state |
      minerals: new_min2,
      workers: new_workers,
      frame: new_frame
    }
  end
end

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

IO.puts("Phase 541: Elixir Nx — SC2 Bot Tensor Operations")

net = SC2Bot.Tensor.PolicyNet.init()

state = %{
  minerals: 400, gas: 100, supply: 50,
  max_supply: 100, workers: 30, army: 20,
  frame: 3000, threat: 0.2
}

action_idx  = SC2Bot.Tensor.decide(net, state)
action_name = SC2Bot.Tensor.action_name(action_idx)

IO.puts("Decision: #{action_idx} (#{action_name})")

final = SC2Bot.Economy.simulate(500)
IO.puts("Final state: minerals=#{final.minerals}, workers=#{final.workers}, frame=#{final.frame}")
