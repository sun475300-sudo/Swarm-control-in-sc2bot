' Wicked Zerg - Battle Simulation
' Phase 145: VB.NET v2

Module BattleSim
    Structure BattleUnit
        Public UnitType As Integer
        Public Health As Double
        Public Damage As Double
        Public Armor As Double
        Public PosX As Double
        Public PosY As Double
    End Structure

    Function CalculateSwarmDamage(count As Integer) As Integer
        Return count * 5
    End Function

    Function SwarmFormation(centerX As Double, centerY As Double, count As Integer, radius As Double) As List(Of Tuple(Of Double, Double))
        Dim positions As New List(Of Tuple(Of Double, Double))
        For i As Integer = 0 To count - 1
            Dim angle As Double = 2 * Math.PI * i / count
            Dim x As Double = centerX + radius * Math.Cos(angle)
            Dim y As Double = centerY + radius * Math.Sin(angle)
            positions.Add(Tuple.Create(x, y))
        Next
        Return positions
    End Function

    Function UnitStrength(health As Double, damage As Double, armor As Double) As Double
        Dim effective As Double = damage * health / 100
        Return effective * (1 - armor * 0.01)
    End Function

    Function BattleOutcome(attackers As List(Of Tuple(Of Double, Double, Double)), 
                          defenders As List(Of Tuple(Of Double, Double, Double))) As Boolean
        Dim attackPower As Double = attackers.Sum(Function(a) UnitStrength(a.Item1, a.Item2, a.Item3))
        Dim defensePower As Double = defenders.Sum(Function(d) UnitStrength(d.Item1, d.Item2, d.Item3))
        Return attackPower > defensePower
    End Function
End Module
