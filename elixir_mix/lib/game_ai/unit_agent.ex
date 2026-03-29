defmodule GameAI.UnitAgent do
  @moduledoc """
  Individual unit state agent for concurrent processing.
  """

  use Agent

  def start_link({unit_id, initial_data}) do
    Agent.start_link(fn -> initial_data end, name: via_tuple(unit_id))
  end

  defp via_tuple(unit_id), do: {:via, Registry, {GameAI.UnitRegistry, unit_id}}

  def get_state(unit_id) do
    Agent.get(via_tuple(unit_id), &(&1))
  end

  def update_state(unit_id, new_state) do
    Agent.update(via_tuple(unit_id), fn _ -> new_state end)
  end
end
