defmodule GameAI.Server do
  @moduledoc """
  Concurrent AI decision processing using Elixir GenServer.
  Handles multiple game state analysis requests in parallel.
  """

  use GenServer
  require Logger

  defstruct [:game_state, :decision_queue, :analysis_workers]

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    Logger.info("Starting Game AI Server...")
    {:ok, %{game_state: %{}, decision_queue: [], analysis_workers: 8}}
  end

  @impl true
  def handle_call(:get_state, _from, state) do
    {:reply, state.game_state, state}
  end

  @impl true
  def handle_call(:process_decision, _from, state) do
    decision = analyze_game_state(state.game_state)
    {:reply, decision, %{state | decision_queue: state.decision_queue ++ [decision]}}
  end

  @impl true
  def handle_cast({:update_state, new_state}, state) do
    {:noreply, %{state | game_state: new_state}}
  end

  @impl true
  def handle_cast({:parallel_analysis, units, callback}, state) do
    tasks = Enum.map(units, fn unit ->
      Task.async(fn -> analyze_unit(unit) end)
    end)
    results = Task.await_many(tasks, 30_000)
    callback.(results)
    {:noreply, state}
  end

  defp analyze_game_state(state) do
    %{
      recommended_action: determine_action(state),
      confidence: calculate_confidence(state),
      timestamp: DateTime.utc_now()
    }
  end

  defp determine_action(state) when map_size(state) == 0, do: :idle
  defp determine_action(_state), do: :analyze

  defp calculate_confidence(_state), do: 0.85

  defp analyze_unit(unit) do
    %{
      unit_id: unit.id,
      threat_level: classify_threat(unit),
      recommended_target: find_best_target(unit)
    }
  end

  defp classify_threat(%{hp: hp, damage: d}) when hp > 100 and d > 10, do: :high
  defp classify_threat(_), do: :low

  defp find_best_target(_unit), do: nil
end
