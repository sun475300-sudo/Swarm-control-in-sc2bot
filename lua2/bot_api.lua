--[[
  Wicked Zerg - Battle Simulation API v2
  Phase 119: Lua v2
--]]

local M = {}

function M.createUnit(unitType, position, owner)
  return {
    type = unitType,
    x = position.x,
    y = position.y,
    owner = owner,
    health = 200,
    shields = 50,
    cooldown = 0
  }
end

function M.calculateDamage(attacker, defender)
  local baseDamage = 5
  local armorMultiplier = 1.0 - (defender.armor or 0) * 0.01
  return math.floor(baseDamage * armorMultiplier)
end

function M.simulateEngagement(units)
  local result = {}
  for _, unit in ipairs(units) do
    table.insert(result, {
      unit_id = unit.id or math.random(1000, 9999),
      status = "active",
      health = unit.health or 100
    })
  end
  return result
end

function M.getSwarmPosition(center, count, radius)
  local positions = {}
  for i = 1, count do
    local angle = (2 * math.pi / count) * i
    table.insert(positions, {
      x = center.x + radius * math.cos(angle),
      y = center.y + radius * math.sin(angle)
    })
  end
  return positions
end

return M
