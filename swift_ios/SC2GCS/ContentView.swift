import SwiftUI

struct ContentView: View {
    @EnvironmentObject var gameState: GameStateManager
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                ConnectionStatusView(status: gameState.connectionStatus)
                
                ResourcesView(resources: gameState.resources)
                
                UnitListView(units: gameState.units)
                
                GameTimeView(time: gameState.gameTime)
                
                Spacer()
            }
            .padding()
            .navigationTitle("Wicked Zerg GCS")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Connect") {
                        gameState.connect(host: "localhost", port: 8080)
                    }
                }
            }
        }
    }
}

struct ConnectionStatusView: View {
    let status: ConnectionStatus
    
    var body: some View {
        HStack {
            Circle()
                .fill(statusColor)
                .frame(width: 12, height: 12)
            Text(statusText)
        }
        .padding()
        .background(Color.gray.opacity(0.2))
        .cornerRadius(8)
    }
    
    var statusColor: Color {
        switch status {
        case .connected: return .green
        case .connecting: return .yellow
        case .error: return .red
        case .disconnected: return .gray
        }
    }
    
    var statusText: String {
        switch status {
        case .connected: return "Connected"
        case .connecting: return "Connecting..."
        case .error: return "Error"
        case .disconnected: return "Disconnected"
        }
    }
}

struct ResourcesView: View {
    let resources: Resources
    
    var body: some View {
        HStack(spacing: 30) {
            ResourceDisplay(icon: "💎", value: resources.minerals, label: "Minerals")
            ResourceDisplay(icon: "🟢", value: resources.gas, label: "Gas")
            ResourceDisplay(icon: "👥", value: resources.supply, label: "Supply")
        }
        .padding()
        .background(Color.blue.opacity(0.1))
        .cornerRadius(12)
    }
}

struct ResourceDisplay: View {
    let icon: String
    let value: Int
    let label: String
    
    var body: some View {
        VStack {
            Text(icon)
                .font(.title)
            Text("\(value)")
                .font(.headline)
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}

struct UnitListView: View {
    let units: [SC2Unit]
    
    var body: some View {
        List(units) { unit in
            UnitRow(unit: unit)
        }
    }
}

struct UnitRow: View {
    let unit: SC2Unit
    
    var body: some View {
        HStack {
            Text(unitTypeIcon(unit.type))
            VStack(alignment: .leading) {
                Text(unit.type)
                Text("HP: \(Int(unit.health))")
                    .font(.caption)
            }
            Spacer()
            Text(unit.state.rawValue)
                .foregroundColor(stateColor)
        }
    }
    
    func unitTypeIcon(_ type: String) -> String {
        switch type {
        case "Drone": return "🐜"
        case "Zergling": return "🦗"
        case "Roach": return "🪳"
        default: return "⬡"
        }
    }
    
    var stateColor: Color {
        switch unit.state {
        case .attacking: return .red
        case .defending: return .orange
        case .gathering: return .green
        default: return .gray
        }
    }
}

struct GameTimeView: View {
    let time: TimeInterval
    
    var body: some View {
        Text("Game Time: \(formatTime(time))")
            .font(.system(.title2, design: .monospaced))
    }
    
    func formatTime(_ time: TimeInterval) -> String {
        let minutes = Int(time) / 60
        let seconds = Int(time) % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
}
