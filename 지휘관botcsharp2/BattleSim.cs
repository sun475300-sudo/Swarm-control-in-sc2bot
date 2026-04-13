using System;
using System.Collections.Generic;
using System.Linq;

namespace WickedZerg
{
    public class BattleUnit
    {
        public int UnitType { get; set; }
        public double Health { get; set; }
        public double Damage { get; set; }
        public double Armor { get; set; }
        public double PosX { get; set; }
        public double PosY { get; set; }
        
        public double GetStrength()
        {
            double effective = Damage * Health / 100.0;
            return effective * (1.0 - Armor * 0.01);
        }
    }
    
    public static class BattleSim
    {
        public static int CalculateSwarmDamage(int count) => count * 5;
        
        public static List<(double x, double y)> SwarmFormation(double centerX, double centerY, int count, double radius)
        {
            return Enumerable.Range(0, count).Select(i =>
            {
                double angle = 2.0 * Math.PI * i / count;
                return (centerX + radius * Math.Cos(angle), centerY + radius * Math.Sin(angle));
            }).ToList();
        }
        
        public static double UnitStrength(double health, double damage, double armor)
        {
            double effective = damage * health / 100.0;
            return effective * (1.0 - armor * 0.01);
        }
        
        public static bool BattleOutcome(List<(double h, double d, double a)> attackers, 
                                        List<(double h, double d, double a)> defenders)
        {
            double attackPower = attackers.Sum(a => UnitStrength(a.h, a.d, a.a));
            double defensePower = defenders.Sum(d => UnitStrength(d.h, d.d, d.a));
            return attackPower > defensePower;
        }
        
        static void Main()
        {
            Console.WriteLine("Battle Simulation Initialized - C# v2");
        }
    }
}
