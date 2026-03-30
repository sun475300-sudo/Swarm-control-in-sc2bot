# Wicked Zerg - Battle Simulation
# Phase 139: Elixir v2

defmodule BattleSim do
  defstruct [:units, :turn]
  
  def new do
    %BattleSim{units: [], turn: 0}
  end
  
  def calculate_swarm_damage(count) do
    count * 5
  end
  
  def swarm_formation(center_x, center_y, count, radius) do
    for i <- 0..(count-1) do
      angle = 2 * :math.pi() * i / count
      x = center_x + radius * :math.cos(angle)
      y = center_y + radius * :math.sin(angle)
      {x, y}
    end
  end
  
  def unit_strength(health, damage, armor) do
    effective = damage * health / 100
    effective * (1 - armor * 0.01)
  end
  
  def battle_outcome(attackers, defenders) do
    attack_power = attackers |> Enum.map(fn {h, d, a} -> unit_strength(h, d, a) end) |> Enum.sum()
    defense_power = defenders |> Enum.map(fn {h, d, a} -> unit_strength(h, d, a) end) |> Enum.sum()
    attack_power > defense_power
  end
end
