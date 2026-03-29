' Wicked Zerg - Battle Simulation
' Phase 121: VBScript

Class BattleUnit
    Public unitType
    Public health
    Public positionX
    Public positionY
    
    Sub Initialize(uType, hp, x, y)
        unitType = uType
        health = hp
        positionX = x
        positionY = y
    End Sub
End Class

Function CalculateSwarmDamage(units)
    Dim totalDamage
    totalDamage = 0
    For Each unit In units
        totalDamage = totalDamage + 5
    Next
    CalculateSwarmDamage = totalDamage
End Function

Function GetSwarmFormation(centerX, centerY, count, radius)
    Dim positions()
    ReDim positions(count - 1)
    Dim i
    For i = 0 To count - 1
        Dim angle
        angle = (2 * 3.14159 / count) * i
        positions(i) = centerX + radius * Cos(angle) & "," & centerY + radius * Sin(angle)
    Next
    GetSwarmFormation = positions
End Function

Sub LogBattleEvent(message)
    WScript.Echo "[" & Now & "] " & message
End Sub
