' P97: VB.NET - .NET Integration Module

Imports System.Net.WebSockets

Module WickedBot
    Private gameSocket As ClientWebSocket
    Private gameState As GameState

    Sub Main()
        Console.WriteLine("Starting Wicked Zerg Bot (VB.NET)...")
        ConnectToGame("localhost", 8080)
    End Sub

    Private Async Function ConnectToGame(host As String, port As Integer) As Task
        gameSocket = New ClientWebSocket()
        Await gameSocket.ConnectAsync(New Uri($"ws://{host}:{port}/game"), CancellationToken.None)
        Console.WriteLine("Connected to game server")
        ReceiveLoop()
    End Function

    Private Async Function ReceiveLoop() As Task
        Dim buffer(4096) As Byte
        While gameSocket.State = WebSocketState.Open
            Dim result = Await gameSocket.ReceiveAsync(New ArraySegment(Of Byte)(buffer), CancellationToken.None)
            If result.MessageType = WebSocketMessageType.Text Then
                Dim message = System.Text.Encoding.UTF8.GetString(buffer, 0, result.Count)
                ProcessMessage(message)
            End If
        End While
    End Function

    Private Sub ProcessMessage(message As String)
        ' Parse JSON and update game state
        Console.WriteLine($"Received: {message}")
    End Sub

    Private Async Function SendCommand(command As String) As Task
        Dim bytes = System.Text.Encoding.UTF8.GetBytes(command)
        Await gameSocket.SendAsync(New ArraySegment(Of Byte)(bytes), WebSocketMessageType.Text, True, CancellationToken.None)
    End Function
End Module

Public Class GameState
    Public Units As New List(Of Unit)
    Public Resources As New Resources
    Public GameTime As Double
End Class

Public Class Unit
    Public Id As Integer
    Public Type As String
    Public Health As Double
    Public PositionX As Double
    Public PositionY As Double
End Class

Public Class Resources
    Public Minerals As Integer
    Public Gas As Integer
    Public Supply As Integer
End Class
