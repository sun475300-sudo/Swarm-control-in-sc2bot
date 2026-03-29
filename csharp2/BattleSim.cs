// P113: C# v2 - Async/Await Game State
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

public class Unit
{
    public int Id { get; set; }
    public float Health { get; set; }
    public float Damage { get; set; }
    public float X { get; set; }
    public float Y { get; set; }
}

public class BattleSimulator
{
    private readonly List<Unit> _units = new();
    
    public void AddUnit(Unit unit) => _units.Add(unit);
    
    public float CalculatePower() => _units.Sum(u => u.Health * u.Damage) / 100f;
    
    public Dictionary<int, float> FindThreats()
    {
        var threats = new Dictionary<int, float>();
        foreach (var u in _units)
        {
            int nearby = _units.Count(e => e.Id != u.Id && Distance(u, e) < 50f);
            threats[u.Id] = nearby * 10f;
        }
        return threats;
    }
    
    private static float Distance(Unit a, Unit b)
    {
        float dx = a.X - b.X;
        float dy = a.Y - b.Y;
        return MathF.Sqrt(dx * dx + dy * dy);
    }
    
    public async Task<float> CalculatePowerAsync()
    {
        return await Task.Run(() => CalculatePower());
    }
}

public class Program
{
    public static void Main()
    {
        var sim = new BattleSimulator();
        sim.AddUnit(new Unit { Id = 1, Health = 40, Damage = 5, X = 10, Y = 10 });
        Console.WriteLine($"Power: {sim.CalculatePower()}");
    }
}
