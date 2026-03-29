import SwiftUI

@main
struct SC2GCSApp: App {
    @StateObject private var gameState = GameStateManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(gameState)
        }
    }
}

class GameStateManager: ObservableObject {
    @Published var units: [SC2Unit] = []
    @Published var resources: Resources = Resources(minerals: 0, gas: 0, supply: 0)
    @Published var gameTime: TimeInterval = 0
    @Published var connectionStatus: ConnectionStatus = .disconnected
    
    private var webSocketTask: URLSessionWebSocketTask?
    
    func connect(host: String, port: Int) {
        guard let url = URL(string: "ws://\(host):\(port)/game") else { return }
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        connectionStatus = .connecting
        
        receiveMessage()
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                self?.handleMessage(message)
                self?.receiveMessage()
            case .failure:
                self?.connectionStatus = .disconnected
            }
        }
    }
    
    private func handleMessage(_ message: URLSessionWebSocketTask.Message) {
        // Parse game state from WebSocket
    }
}

struct SC2Unit: Identifiable, Codable {
    let id: UInt64
    let type: String
    var health: Double
    var position: CGPoint
    var state: UnitState
}

enum UnitState: String, Codable {
    case idle, moving, attacking, defending, gathering
}

struct Resources: Codable {
    var minerals: Int
    var gas: Int
    var supply: Int
}

enum ConnectionStatus {
    case disconnected, connecting, connected, error
}
