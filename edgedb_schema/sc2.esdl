# Phase 445: EdgeDB Schema for SC2 Bot Data
# EdgeQL schema: Players, Games, Units, BuildOrders with rich links

module sc2 {

    scalar type Race extending enum<Zerg, Terran, Protoss, Random>;
    scalar type GameResult extending enum<Win, Loss, Draw, Unknown>;

    type Player {
        required property player_id -> str {
            constraint exclusive;
        }
        required property name -> str;
        required property race -> Race;
        property mmr -> int32 {
            default := 1000;
        }
        property total_games -> int32 {
            default := 0;
        }
        property win_rate -> float64 {
            default := 0.0;
        }
        multi link games -> Game {
            on source delete allow;
        }
    }

    type Game {
        required property game_id -> str {
            constraint exclusive;
        }
        required property map_name -> str;
        required property duration_seconds -> int32;
        required property result -> GameResult;
        required property played_at -> datetime {
            default := datetime_current();
        }
        property apm -> int32;
        property supply_peak -> int32;
        link build_order -> BuildOrder;
        multi link units_used -> Unit;
    }

    type Unit {
        required property name -> str {
            constraint exclusive;
        }
        required property race -> Race;
        required property mineral_cost -> int32;
        required property gas_cost -> int32;
        required property supply_cost -> int32;
        property is_worker -> bool {
            default := false;
        }
        multi link counters -> Unit {
            property effectiveness -> float64;
        }
    }

    type BuildOrder {
        required property name -> str;
        required property race -> Race;
        property description -> str;
        property win_rate -> float64;
        multi link steps -> BuildStep {
            constraint exclusive;
        }
    }

    type BuildStep {
        required property supply_trigger -> int32;
        required property action -> str;
        property target_unit -> str;
        property notes -> str;
        required property step_index -> int32;
    }

    # EdgeQL statistics queries (as comments for reference)
    # SELECT Player { name, win_rate, total_games }
    #     FILTER .race = Race.Zerg
    #     ORDER BY .win_rate DESC
    #     LIMIT 10;

    # SELECT Game { map_name, duration_seconds, units_used: { name, mineral_cost } }
    #     FILTER .result = GameResult.Win AND .apm > 150;

    # SELECT BuildOrder { name, win_rate, steps: { supply_trigger, action } ORDER BY .step_index }
    #     FILTER .race = Race.Zerg
    #     ORDER BY .win_rate DESC;
}
