// game_logic.wren
// Wren lightweight scripting layer for StarCraft II Zerg bot game-logic hooks.
// Provides a rule-based decision system: EconomyRule and CombatRule instances
// are registered with BotStrategy, which evaluates them each game tick.

// ---------------------------------------------------------------------------
// Rule base class
// ---------------------------------------------------------------------------

// Rule is the abstract base for all decision rules.
// Subclasses must override condition() and action().
class Rule {
    // Returns true when this rule's condition is currently satisfied.
    condition(state) { false }

    // Returns a string describing the action to take.
    action(state) { "no-op" }

    // Evaluate: if condition holds, return the action string; else null.
    evaluate(state) {
        if (condition(state)) return action(state)
        return null
    }
}

// ---------------------------------------------------------------------------
// Economy rules
// ---------------------------------------------------------------------------

// EconomyRule fires when the bot should prioritise economic actions
// (drone production, expansion, extractor building).
class EconomyRule is Rule {
    // Trigger: fewer than 16 drones OR mineral surplus above 400.
    condition(state) {
        return (state["drone_count"] < 16) || (state["minerals"] > 400)
    }

    action(state) {
        if (state["drone_count"] < 16) {
            return "train_drone"          // grow the worker line
        }
        if (state["minerals"] > 400 && !state["has_expansion"]) {
            return "expand_hatchery"      // spend surplus on expansion
        }
        return "build_extractor"          // convert excess to gas income
    }
}

// ---------------------------------------------------------------------------
// Combat rules
// ---------------------------------------------------------------------------

// CombatRule fires when the bot should shift attention to military actions.
class CombatRule is Rule {
    // Trigger: enemy spotted near base OR army supply threshold reached.
    condition(state) {
        return state["enemy_near_base"] || (state["army_supply"] >= 20)
    }

    action(state) {
        if (state["enemy_near_base"]) {
            return "defend_base"          // pull army back to defend
        }
        if (state["army_supply"] >= 30) {
            return "attack_move_enemy"    // critical mass — attack
        }
        return "rally_army"              // keep building up before committing
    }
}

// ---------------------------------------------------------------------------
// Scout rule
// ---------------------------------------------------------------------------

// ScoutRule keeps map information current by sending an overlord or drone.
class ScoutRule is Rule {
    condition(state) {
        // Scout again if we haven't seen the enemy base yet, or 120 s elapsed.
        return !state["enemy_base_known"] || (state["game_time"] % 120 < 1)
    }

    action(state) {
        if (!state["enemy_base_known"]) return "send_overlord_scout"
        return "patrol_overlord"
    }
}

// ---------------------------------------------------------------------------
// Main strategy controller
// ---------------------------------------------------------------------------

// BotStrategy aggregates rules and drives the per-tick decision loop.
class BotStrategy {
    construct new() {
        _rules = [EconomyRule.new(), ScoutRule.new(), CombatRule.new()]
        _action_log = []
    }

    // analyze() inspects the game state and returns a snapshot map.
    // In a real integration this would pull data from the SC2 API.
    analyze(raw_state) {
        // Validate required keys; fill defaults for missing ones.
        var state = raw_state
        if (!state.containsKey("drone_count"))     state["drone_count"]     = 12
        if (!state.containsKey("minerals"))        state["minerals"]        = 50
        if (!state.containsKey("army_supply"))     state["army_supply"]     = 0
        if (!state.containsKey("enemy_near_base")) state["enemy_near_base"] = false
        if (!state.containsKey("enemy_base_known"))state["enemy_base_known"]= false
        if (!state.containsKey("has_expansion"))   state["has_expansion"]   = false
        if (!state.containsKey("game_time"))       state["game_time"]       = 0
        return state
    }

    // decide() evaluates all rules against the analyzed state and returns
    // the highest-priority action (first matching rule wins).
    decide(state) {
        for (rule in _rules) {
            var result = rule.evaluate(state)
            if (result != null) return result
        }
        return "idle"
    }

    // execute() records the decided action and (in production) would call
    // the corresponding python-sc2 command via FFI or message passing.
    execute(action, state) {
        _action_log.add({ "time": state["game_time"], "action": action })
        System.print("[BotStrategy] t=%(state["game_time"])s -> %(action)")
    }

    // tick() is the single entry point called every bot step.
    tick(raw_state) {
        var state  = analyze(raw_state)
        var action = decide(state)
        execute(action, state)
        return action
    }

    // actionLog exposes the history for diagnostics.
    actionLog { _action_log }
}

// ---------------------------------------------------------------------------
// Demo / smoke test
// ---------------------------------------------------------------------------

var bot = BotStrategy.new()

// Simulate a few game ticks with different state snapshots.
var tick1 = {
    "drone_count": 10, "minerals": 150, "army_supply": 0,
    "enemy_near_base": false, "enemy_base_known": false,
    "has_expansion": false,   "game_time": 30
}
var tick2 = {
    "drone_count": 16, "minerals": 450, "army_supply": 12,
    "enemy_near_base": false, "enemy_base_known": true,
    "has_expansion": false,   "game_time": 120
}
var tick3 = {
    "drone_count": 20, "minerals": 200, "army_supply": 22,
    "enemy_near_base": true,  "enemy_base_known": true,
    "has_expansion": true,    "game_time": 300
}

bot.tick(tick1)
bot.tick(tick2)
bot.tick(tick3)

System.print("--- Action log: %(bot.actionLog.count) entries recorded ---")
