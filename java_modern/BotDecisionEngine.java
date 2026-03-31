// Phase 545: Java 21 Modern
// SC2 Bot with records, sealed classes, pattern matching, virtual threads

package sc2bot.engine;

import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;
import java.util.function.*;

// ─────────────────────────────────────────────
// Sealed class hierarchy
// ─────────────────────────────────────────────

public class BotDecisionEngine {

    // Sealed interface for actions
    sealed interface Action permits
        TrainUnit, BuildStructure, ExpandBase, AttackMove, Defend, Wait {
    }
    record TrainUnit(UnitType unit)     implements Action {}
    record BuildStructure(String name)  implements Action {}
    record ExpandBase()                 implements Action {}
    record AttackMove(float x, float y) implements Action {}
    record Defend()                     implements Action {}
    record Wait()                       implements Action {}

    // Sealed interface for game phases
    sealed interface GamePhase permits
        Opening, EarlyGame, MidGame, LateGame {
    }
    record Opening()   implements GamePhase {}
    record EarlyGame() implements GamePhase {}
    record MidGame()   implements GamePhase {}
    record LateGame()  implements GamePhase {}

    enum UnitType { DRONE, ZERGLING, ROACH, HYDRALISK, MUTALISK, QUEEN, OVERLORD }
    enum Race { ZERG, TERRAN, PROTOSS }

    // ─────────────────────────────────────────────
    // Records for immutable state
    // ─────────────────────────────────────────────

    record Resources(int minerals, int gas, int supply, int maxSupply) {
        boolean canAfford(int m, int g) { return minerals >= m && gas >= g; }
        boolean supplyFull() { return supply >= maxSupply - 1; }
        Resources use(int m, int g, int s) {
            return new Resources(minerals - m, gas - g, supply + s, maxSupply);
        }
        Resources expandSupply(int amt) {
            return new Resources(minerals, gas, supply, maxSupply + amt);
        }
    }

    record ArmyState(int mySupply, int enemySupply, double threatLevel) {
        boolean underThreat() { return threatLevel > 0.6; }
    }

    record GameState(
        Resources resources,
        ArmyState army,
        int workers,
        int frame,
        int hatcheries,
        Race enemyRace
    ) {
        static GameState initial() {
            return new GameState(
                new Resources(50, 0, 12, 14),
                new ArmyState(0, 0, 0.0),
                12, 0, 1, Race.TERRAN
            );
        }

        GamePhase phase() {
            return switch (frame) {
                case int f when f < 1344 -> new Opening();
                case int f when f < 3360 -> new EarlyGame();
                case int f when f < 6720 -> new MidGame();
                default                  -> new LateGame();
            };
        }
    }

    // ─────────────────────────────────────────────
    // Unit costs
    // ─────────────────────────────────────────────

    record UnitCost(int minerals, int gas, int supply) {}

    static final Map<UnitType, UnitCost> COSTS = Map.of(
        UnitType.DRONE,     new UnitCost(50, 0, 1),
        UnitType.ZERGLING,  new UnitCost(25, 0, 1),
        UnitType.ROACH,     new UnitCost(75, 25, 2),
        UnitType.HYDRALISK, new UnitCost(100, 50, 2),
        UnitType.MUTALISK,  new UnitCost(100, 100, 2),
        UnitType.QUEEN,     new UnitCost(150, 0, 2),
        UnitType.OVERLORD,  new UnitCost(100, 0, 0)
    );

    // ─────────────────────────────────────────────
    // Pattern-matching decision
    // ─────────────────────────────────────────────

    static Action decide(GameState s) {
        var res = s.resources();
        var army = s.army();

        if (army.underThreat())         return new Defend();
        if (res.supplyFull() && res.canAfford(100, 0)) return new TrainUnit(UnitType.OVERLORD);
        if (s.workers() < 22 && res.canAfford(50, 0))  return new TrainUnit(UnitType.DRONE);
        if (res.minerals() >= 300 && s.hatcheries() < 3) return new ExpandBase();

        return switch (s.enemyRace()) {
            case TERRAN  -> res.canAfford(100, 50) ? new TrainUnit(UnitType.HYDRALISK) : new Wait();
            case PROTOSS -> res.canAfford(75, 25)  ? new TrainUnit(UnitType.ROACH)     : new Wait();
            case ZERG    -> res.canAfford(25, 0)   ? new TrainUnit(UnitType.ZERGLING)  : new Wait();
        };
    }

    // ─────────────────────────────────────────────
    // Economy tick
    // ─────────────────────────────────────────────

    static GameState tick(GameState s) {
        int income = s.workers() * 8 / 10;
        double newThreat = Math.min(1.0, s.army().threatLevel() + 0.0001);
        return new GameState(
            s.resources().use(-income, 0, 0).use(0, 0, 0),
            new ArmyState(s.army().mySupply(), s.army().enemySupply(), newThreat),
            s.workers(),
            s.frame() + 1,
            s.hatcheries(),
            s.enemyRace()
        );
    }

    static GameState applyAction(GameState s, Action action) {
        return switch (action) {
            case TrainUnit(UnitType.DRONE) when s.resources().canAfford(50, 0) ->
                new GameState(s.resources().use(50, 0, 1), s.army(),
                              s.workers() + 1, s.frame(), s.hatcheries(), s.enemyRace());

            case TrainUnit(var u) when COSTS.containsKey(u) -> {
                var cost = COSTS.get(u);
                if (!s.resources().canAfford(cost.minerals(), cost.gas())) yield s;
                yield new GameState(
                    s.resources().use(cost.minerals(), cost.gas(), cost.supply()),
                    new ArmyState(s.army().mySupply() + cost.supply(),
                                  s.army().enemySupply(), s.army().threatLevel()),
                    s.workers(), s.frame(), s.hatcheries(), s.enemyRace()
                );
            }

            case ExpandBase() when s.resources().canAfford(300, 0) ->
                new GameState(s.resources().use(300, 0, 0), s.army(),
                              s.workers() + 4, s.frame(), s.hatcheries() + 1, s.enemyRace());

            default -> s;
        };
    }

    static GameState step(GameState s) {
        var ticked = tick(s);
        return applyAction(ticked, decide(ticked));
    }

    // ─────────────────────────────────────────────
    // Virtual threads simulation (Java 21)
    // ─────────────────────────────────────────────

    static CompletableFuture<GameState> simulateAsync(GameState initial, int frames) {
        return CompletableFuture.supplyAsync(() -> {
            GameState s = initial;
            for (int i = 0; i < frames; i++) s = step(s);
            return s;
        }, Executors.newVirtualThreadPerTaskExecutor());
    }

    // ─────────────────────────────────────────────
    // Stream-based analytics
    // ─────────────────────────────────────────────

    static Map<String, Double> analyzeHistory(List<GameState> history) {
        return Map.of(
            "avg_minerals", history.stream().mapToInt(s -> s.resources().minerals()).average().orElse(0),
            "max_workers",  (double) history.stream().mapToInt(GameState::workers).max().orElse(0),
            "max_army",     (double) history.stream().mapToInt(s -> s.army().mySupply()).max().orElse(0)
        );
    }

    // ─────────────────────────────────────────────
    // Main
    // ─────────────────────────────────────────────

    public static void main(String[] args) throws Exception {
        System.out.println("Phase 545: Java 21 Modern — SC2 Bot Decision Engine");

        var initial = GameState.initial();
        List<GameState> history = new ArrayList<>();

        // Sync simulation
        var state = initial;
        for (int i = 0; i < 2000; i++) {
            history.add(state);
            state = step(state);
        }

        var final_ = state;
        System.out.printf("Frame:%d | Minerals:%d | Workers:%d | Army:%d | Supply:%d/%d%n",
            final_.frame(), final_.resources().minerals(), final_.workers(),
            final_.army().mySupply(), final_.resources().supply(), final_.resources().maxSupply());
        System.out.printf("Phase: %s%n", final_.phase());

        // Analytics
        var metrics = analyzeHistory(history);
        metrics.forEach((k, v) -> System.out.printf("  %-20s: %.1f%n", k, v));

        // Async with virtual threads
        System.out.println("Running async simulation (virtual threads)...");
        var asyncResult = simulateAsync(initial, 1000).get();
        System.out.printf("Async result: frame=%d, minerals=%d%n",
            asyncResult.frame(), asyncResult.resources().minerals());
    }
}
