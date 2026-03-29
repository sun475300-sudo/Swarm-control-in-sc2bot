defmodule GameAI.UnitSupervisor do
  @moduledoc """
  OTP Supervisor for managing game unit agents.
  Implements fault-tolerant unit monitoring.
  """

  use Supervisor

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      {Registry, keys: :unique, name: GameAI.UnitRegistry},
      {DynamicSupervisor, strategy: :one_for_one, name: GameAI.UnitSupervisor}
    ]
    Supervisor.init(children, strategy: :one_for_all)
  end

  def start_unit_agent(unit_id, unit_data) do
    spec = {GameAI.UnitAgent, {unit_id, unit_data}}
    DynamicSupervisor.start_child(GameAI.UnitSupervisor, spec)
  end
end
