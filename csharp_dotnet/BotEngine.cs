// Phase 544: C# .NET 8
// SC2 Bot engine with C# records, pattern matching, LINQ, async/await

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Threading.Channels;
using System.Runtime.CompilerServices;

namespace SC2Bot.Engine;

// ─────────────────────────────────────────────
// Records & discriminated unions
// ─────────────────────────────────────────────

public enum Race { Zerg, Terran, Protoss }

public enum UnitType
{
    Drone, Zergling, Roach, Hydralisk, Mutalisk,
    Ultralisk, Queen, Overlord, Lurker, BroodLord
}

public record Resources(int Minerals, int Gas, int Supply, int MaxSupply)
{
    public bool CanAfford(int min, int gas) =>
        Minerals >= min && Gas >= gas;

    public bool SupplyFull => Supply >= MaxSupply - 1;

    public Resources Use(int min, int gas, int supply) =>
        new(Minerals - min, Gas - gas, Supply + supply, MaxSupply);

    public Resources ExpandSupply(int amount) =>
        this with { MaxSupply = MaxSupply + amount };
}

public record ArmyState(int MySupply, int EnemySupply, double ThreatLevel)
{
    public bool UnderThreat => ThreatLevel > 0.6;
}

public record GameState(
    Resources Resources,
    ArmyState Army,
    int Workers,
    int Frame,
    int Hatcheries,
    Race EnemyRace)
{
    public static GameState Initial(Race enemy = Race.Terran) => new(
        Resources: new(50, 0, 12, 14),
        Army: new(0, 0, 0.0),
        Workers: 12,
        Frame: 0,
        Hatcheries: 1,
        EnemyRace: enemy
    );

    public string Phase => Frame switch
    {
        < 1344 => "Opening",
        < 3360 => "EarlyGame",
        < 6720 => "MidGame",
        _      => "LateGame"
    };
}

// ─────────────────────────────────────────────
// Actions
// ─────────────────────────────────────────────

public abstract record Action;
public record TrainUnit(UnitType Unit) : Action;
public record BuildStructure(string Name) : Action;
public record ExpandAction : Action;
public record AttackAction(float X, float Y) : Action;
public record DefendAction : Action;
public record WaitAction : Action;

// ─────────────────────────────────────────────
// Strategy engine
// ─────────────────────────────────────────────

public static class BotStrategy
{
    private static readonly Dictionary<UnitType, (int Min, int Gas, int Supply)> UnitCosts = new()
    {
        [UnitType.Drone]     = (50, 0, 1),
        [UnitType.Zergling]  = (25, 0, 1),
        [UnitType.Roach]     = (75, 25, 2),
        [UnitType.Hydralisk] = (100, 50, 2),
        [UnitType.Mutalisk]  = (100, 100, 2),
        [UnitType.Ultralisk] = (300, 200, 6),
        [UnitType.Queen]     = (150, 0, 2),
        [UnitType.Overlord]  = (100, 0, 0),
    };

    public static Action Decide(GameState s) => s switch
    {
        // Threat response
        { Army.ThreatLevel: > 0.7 } => new DefendAction(),

        // Supply management
        { Resources.SupplyFull: true }
            when s.Resources.CanAfford(100, 0) => new TrainUnit(UnitType.Overlord),

        // Worker saturation
        { Workers: < 22 }
            when s.Resources.CanAfford(50, 0) => new TrainUnit(UnitType.Drone),

        // Expansion
        { Resources.Minerals: >= 300, Hatcheries: < 3 } => new ExpandAction(),

        // Army by matchup
        { EnemyRace: Race.Terran }
            when s.Resources.CanAfford(100, 50) => new TrainUnit(UnitType.Hydralisk),

        { EnemyRace: Race.Protoss }
            when s.Resources.CanAfford(75, 25) => new TrainUnit(UnitType.Roach),

        { Resources.Minerals: >= 25 } => new TrainUnit(UnitType.Zergling),

        _ => new WaitAction()
    };

    public static (int Min, int Gas, int Supply) GetCost(UnitType unit) =>
        UnitCosts.TryGetValue(unit, out var cost) ? cost : (0, 0, 0);
}

// ─────────────────────────────────────────────
// Economy simulation
// ─────────────────────────────────────────────

public class EconomySimulator
{
    private GameState _state;
    private readonly List<GameState> _history = new();

    public EconomySimulator(GameState? initial = null)
    {
        _state = initial ?? GameState.Initial();
    }

    public GameState CurrentState => _state;

    private GameState Tick(GameState s)
    {
        int income = s.Workers * 8 / 10;
        double newThreat = Math.Min(1.0, s.Army.ThreatLevel + 0.0001);
        return s with
        {
            Resources = s.Resources with { Minerals = s.Resources.Minerals + income },
            Frame = s.Frame + 1,
            Army = s.Army with { ThreatLevel = newThreat },
        };
    }

    private GameState ApplyAction(GameState s, Action action) => action switch
    {
        TrainUnit { Unit: UnitType.Drone } when s.Resources.CanAfford(50, 0)
            => s with
            {
                Resources = s.Resources.Use(50, 0, 1),
                Workers = s.Workers + 1,
            },
        TrainUnit { Unit: var u } when BotStrategy.GetCost(u) is var (m, g, sup)
            && s.Resources.CanAfford(m, g)
            => s with
            {
                Resources = s.Resources.Use(m, g, sup),
                Army = s.Army with { MySupply = s.Army.MySupply + sup },
            },
        TrainUnit { Unit: UnitType.Overlord } when s.Resources.CanAfford(100, 0)
            => s with
            {
                Resources = s.Resources.Use(100, 0, 0).ExpandSupply(8),
            },
        ExpandAction when s.Resources.CanAfford(300, 0)
            => s with
            {
                Resources = s.Resources.Use(300, 0, 0),
                Hatcheries = s.Hatcheries + 1,
                Workers = s.Workers + 4,
            },
        _ => s
    };

    public void Step()
    {
        _history.Add(_state);
        var ticked = Tick(_state);
        var action = BotStrategy.Decide(ticked);
        _state = ApplyAction(ticked, action);
    }

    public void Run(int frames)
    {
        for (int i = 0; i < frames; i++)
            Step();
    }

    public IEnumerable<GameState> History => _history;

    public string Report()
    {
        var s = _state;
        return $"Frame:{s.Frame} | Minerals:{s.Resources.Minerals} | " +
               $"Workers:{s.Workers} | Army:{s.Army.MySupply} | " +
               $"Supply:{s.Resources.Supply}/{s.Resources.MaxSupply} | " +
               $"Phase:{s.Phase}";
    }
}

// ─────────────────────────────────────────────
// Async channel-based event bus
// ─────────────────────────────────────────────

public class BotEventBus
{
    private readonly Channel<string> _channel = Channel.CreateUnbounded<string>();
    public ChannelWriter<string> Writer => _channel.Writer;

    public async IAsyncEnumerable<string> ReadAllAsync(
        [EnumeratorCancellation] System.Threading.CancellationToken ct = default)
    {
        await foreach (var item in _channel.Reader.ReadAllAsync(ct))
            yield return item;
    }
}

// ─────────────────────────────────────────────
// LINQ analytics
// ─────────────────────────────────────────────

public static class Analytics
{
    public static Dictionary<string, double> ComputeMetrics(IEnumerable<GameState> history)
    {
        var states = history.ToList();
        if (!states.Any()) return new();

        return new Dictionary<string, double>
        {
            ["avg_minerals"]    = states.Average(s => s.Resources.Minerals),
            ["max_workers"]     = states.Max(s => s.Workers),
            ["max_army"]        = states.Max(s => s.Army.MySupply),
            ["avg_threat"]      = states.Average(s => s.Army.ThreatLevel),
            ["expand_frame"]    = states.FirstOrDefault(s => s.Hatcheries >= 2)?.Frame ?? -1,
        };
    }
}

// ─────────────────────────────────────────────
// Entry point
// ─────────────────────────────────────────────

class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("Phase 544: C# .NET 8 — SC2 Bot Engine");

        var sim = new EconomySimulator(GameState.Initial(Race.Protoss));
        sim.Run(3000);
        Console.WriteLine(sim.Report());

        var metrics = Analytics.ComputeMetrics(sim.History);
        foreach (var (key, value) in metrics.OrderBy(kv => kv.Key))
            Console.WriteLine($"  {key,-20}: {value:F1}");

        // Async event demo
        var bus = new BotEventBus();
        await bus.Writer.WriteAsync("attack");
        await bus.Writer.WriteAsync("expand");
        bus.Writer.Complete();

        await foreach (var evt in bus.ReadAllAsync())
            Console.WriteLine($"  Event: {evt}");
    }
}
