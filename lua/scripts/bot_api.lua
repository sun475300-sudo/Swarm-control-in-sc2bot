-- P87: Lua - Embedded Script Engine
-- StarCraft II AI Bot - Lua Scripting API

local SC2 = SC2 or {}
SC2.API = SC2.API or {}
SC2.API.Bot = {}

local Bot = {}
Bot.__index = Bot

function Bot:new(config)
    local instance = setmetatable({}, Bot)
    instance.config = config or {}
    instance.units = {}
    instance.resources = { minerals = 50, vespene = 0, supply = 0 }
    instance.game_state = "idle"
    return instance
end

-- Unit Management
function Bot:on_unit_created(unit)
    table.insert(self.units, unit)
    self:log("Unit created: " .. unit.type)
end

function Bot:on_unit_destroyed(unit_id)
    for i, unit in ipairs(self.units) do
        if unit.id == unit_id then
            table.remove(self.units, i)
            self:log("Unit destroyed: " .. unit.type)
            break
        end
    end
end

-- Game Loop
function Bot:on_step()
    self:update_resources()
    self:update_game_state()
    
    if self.game_state == "early" then
        self:handle_early_game()
    elseif self.game_state == "mid" then
        self:handle_mid_game()
    elseif self.game_state == "late" then
        self:handle_late_game()
    end
end

function Bot:update_resources()
    self.resources.minerals = self:get_minerals()
    self.resources.vespene = self:get_vespene()
    self.resources.supply = self:get_supply_used()
end

function Bot:update_game_state()
    local supply = self.resources.supply
    if supply < 30 then
        self.game_state = "early"
    elseif supply < 80 then
        self.game_state = "mid"
    else
        self.game_state = "late"
    end
end

-- Build Orders
function Bot:handle_early_game()
    local drones = self:count_units("drone")
    local overlords = self:count_units("overlord")
    
    if drones < 16 then
        self:train("drone")
    elseif overlords < 2 then
        self:train("overlord")
    elseif self.resources.minerals >= 100 and self:has_larva() then
        self:morph("zergling", 4)
    end
end

function Bot:handle_mid_game()
    local roaches = self:count_units("roach")
    local hydralisks = self:count_units("hydralisk")
    
    if roaches < 10 then
        self:train("roach")
    elseif self.resources.vespene >= 100 then
        self:research("grooved_spines")
    end
    
    if self:enemy_count() > 10 then
        self:attack_all()
    end
end

function Bot:handle_late_game()
    local ultras = self:count_units("ultralisk")
    local broodlords = self:count_units("broodlord")
    
    if ultras < 5 then
        self:morph("ultralisk")
    end
    
    self:attack_all()
end

-- Actions
function Bot:train(unit_type)
    self:log("Training: " .. unit_type)
    -- API call would go here
end

function Bot:morph(unit_type, count)
    self:log("Morphing: " .. unit_type .. " x" .. (count or 1))
end

function Bot:research(tech)
    self:log("Researching: " .. tech)
end

function Bot:attack_all()
    local army = self:get_army_units()
    if #army > 20 then
        local target = self:get_enemy_expansion()
        for _, unit in ipairs(army) do
            self:command(unit.id, "attack", target)
        end
    end
end

function Bot:defend_base()
    local enemy = self:get_nearby_enemies()
    if #enemy > 0 then
        local army = self:get_army_units()
        for _, unit in ipairs(army) do
            self:command(unit.id, "attack", enemy[1].position)
        end
    end
end

-- Helpers
function Bot:count_units(unit_type)
    local count = 0
    for _, unit in ipairs(self.units) do
        if unit.type == unit_type then
            count = count + 1
        end
    end
    return count
end

function Bot:get_army_units()
    local army = {}
    local army_types = {
        zergling = true, roach = true, hydralisk = true,
        mutalisk = true, ultralisk = true, broodlord = true
    }
    for _, unit in ipairs(self.units) do
        if army_types[unit.type] then
            table.insert(army, unit)
        end
    end
    return army
end

function Bot:has_larva()
    for _, unit in ipairs(self.units) do
        if unit.type == "larva" then
            return true
        end
    end
    return false
end

function Bot:enemy_count()
    return 0 -- Would query game state
end

function Bot:get_enemy_expansion()
    return { x = 150, y = 150 }
end

function Bot:get_nearby_enemies()
    return {} -- Would query game state
end

function Bot:command(unit_id, action, target)
    self:log("Command: " .. unit_id .. " " .. action)
end

function Bot:get_minerals()
    return self.resources.minerals
end

function Bot:get_vespene()
    return self.resources.vespene
end

function Bot:get_supply_used()
    return self.resources.supply
end

function Bot:log(message)
    if self.config.verbose then
        print("[Bot] " .. message)
    end
end

-- Configuration
Bot.config_schema = {
    verbose = { type = "boolean", default = true },
    build_order = { type = "string", default = "standard" },
    apm_limit = { type = "number", default = 200 },
    debug_mode = { type = "boolean", default = false }
}

-- Export
return Bot
