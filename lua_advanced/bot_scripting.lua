-- Phase 550: Lua Advanced
-- SC2 Bot scripting engine with coroutines, metatables, and closures

-- ─────────────────────────────────────────────
-- OOP via metatables
-- ─────────────────────────────────────────────

local function class(parent)
  local cls = {}
  cls.__index = cls
  if parent then
    setmetatable(cls, { __index = parent })
  end
  cls.new = function(...)
    local self = setmetatable({}, cls)
    if self.init then self:init(...) end
    return self
  end
  return cls
end

-- ─────────────────────────────────────────────
-- GameState class
-- ─────────────────────────────────────────────

local GameState = class()

function GameState:init(enemy_race)
  self.minerals    = 50
  self.gas         = 0
  self.supply      = 12
  self.max_supply  = 14
  self.workers     = 12
  self.army        = 0
  self.frame       = 0
  self.hatcheries  = 1
  self.threat      = 0.0
  self.enemy_race  = enemy_race or "terran"
end

function GameState:can_afford(m, g)
  g = g or 0
  return self.minerals >= m and self.gas >= g
end

function GameState:supply_full()
  return self.supply >= self.max_supply - 1
end

function GameState:phase()
  if     self.frame < 1344 then return "opening"
  elseif self.frame < 3360 then return "early"
  elseif self.frame < 6720 then return "mid"
  else                          return "late"
  end
end

function GameState:clone()
  local c = {}
  for k, v in pairs(self) do c[k] = v end
  return setmetatable(c, getmetatable(self))
end

-- ─────────────────────────────────────────────
-- Unit costs
-- ─────────────────────────────────────────────

local COSTS = {
  drone     = { minerals = 50,  gas = 0,  supply = 1 },
  zergling  = { minerals = 25,  gas = 0,  supply = 1 },
  roach     = { minerals = 75,  gas = 25, supply = 2 },
  hydralisk = { minerals = 100, gas = 50, supply = 2 },
  mutalisk  = { minerals = 100, gas = 100, supply = 2 },
  overlord  = { minerals = 100, gas = 0,  supply = 0 },
}

-- ─────────────────────────────────────────────
-- Strategy using closures
-- ─────────────────────────────────────────────

local function make_strategy(config)
  local worker_cap     = config.worker_cap or 22
  local threat_thresh  = config.threat_thresh or 0.6
  local army_unit      = config.army_unit or "zergling"

  return function(state)
    if state.threat > threat_thresh then
      return "defend", nil
    end
    if state:supply_full() and state:can_afford(100) then
      return "train", "overlord"
    end
    if state.workers < worker_cap and state:can_afford(50) then
      return "train", "drone"
    end
    if state.minerals >= 300 and state.hatcheries < 3 then
      return "expand", nil
    end
    local cost = COSTS[army_unit]
    if cost and state:can_afford(cost.minerals, cost.gas) then
      return "train", army_unit
    end
    return "wait", nil
  end
end

local aggressive = make_strategy({ army_unit = "zergling", worker_cap = 16 })
local eco        = make_strategy({ army_unit = "hydralisk", worker_cap = 28 })
local adaptive   = make_strategy({ army_unit = "roach",    worker_cap = 22 })

-- ─────────────────────────────────────────────
-- Tick & apply
-- ─────────────────────────────────────────────

local function tick(s)
  local income = math.floor(s.workers * 8 / 10)
  s.minerals = s.minerals + income
  s.frame    = s.frame + 1
  s.threat   = math.min(1.0, s.threat + 0.0001)
  return s
end

local function apply_action(s, action, arg)
  if action == "train" and arg then
    local cost = COSTS[arg]
    if not cost then return s end
    if not s:can_afford(cost.minerals, cost.gas) then return s end
    s.minerals = s.minerals - cost.minerals
    s.gas      = s.gas      - cost.gas
    s.supply   = s.supply   + cost.supply
    if arg == "drone" then
      s.workers = s.workers + 1
    elseif arg == "overlord" then
      s.max_supply = s.max_supply + 8
    else
      s.army = s.army + cost.supply
    end
  elseif action == "expand" then
    if not s:can_afford(300) then return s end
    s.minerals   = s.minerals - 300
    s.hatcheries = s.hatcheries + 1
    s.workers    = s.workers + 4
  end
  return s
end

-- ─────────────────────────────────────────────
-- Coroutine-based game loop
-- ─────────────────────────────────────────────

local function make_game_coroutine(strategy, enemy_race)
  return coroutine.create(function()
    local s = GameState.new(enemy_race)
    while true do
      tick(s)
      local action, arg = strategy(s)
      apply_action(s, action, arg)
      coroutine.yield(s)
    end
  end)
end

local function run_coroutine(co, steps)
  local states = {}
  for _ = 1, steps do
    local ok, state = coroutine.resume(co)
    if not ok then break end
    states[#states + 1] = {
      frame    = state.frame,
      minerals = state.minerals,
      workers  = state.workers,
      army     = state.army,
    }
  end
  return states
end

-- ─────────────────────────────────────────────
-- Simulation runner
-- ─────────────────────────────────────────────

local function simulate(strategy, frames, enemy_race)
  local s = GameState.new(enemy_race)
  for _ = 1, frames do
    tick(s)
    local action, arg = strategy(s)
    apply_action(s, action, arg)
  end
  return s
end

-- ─────────────────────────────────────────────
-- Main
-- ─────────────────────────────────────────────

print("Phase 550: Lua Advanced — SC2 Bot Scripting Engine")

-- Run strategies
local strategies = { aggressive = aggressive, eco = eco, adaptive = adaptive }
for name, strat in pairs(strategies) do
  local final = simulate(strat, 1500, "terran")
  print(string.format(
    "  [%s] Frame:%d | Minerals:%d | Workers:%d | Army:%d",
    name, final.frame, final.minerals, final.workers, final.army
  ))
end

-- Coroutine demo
print("\nCoroutine game loop (100 steps):")
local co = make_game_coroutine(adaptive, "protoss")
local history = run_coroutine(co, 100)
print(string.format(
  "  Step 50: frame=%d minerals=%d",
  history[50].frame, history[50].minerals
))
print(string.format(
  "  Step 100: frame=%d workers=%d army=%d",
  history[100].frame, history[100].workers, history[100].army
))
