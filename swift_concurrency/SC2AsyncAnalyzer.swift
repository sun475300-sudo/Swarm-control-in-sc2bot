import Foundation

// --- Data Models ---

struct GameState: Codable {
    let gameId: String
    let minerals: Int
    let vespene: Int
    let supplyUsed: Int
    let supplyCap: Int
    let units: [SC2Unit]
    let tick: TimeInterval
}

struct SC2Unit: Codable {
    let tag: UInt64
    let type: String
    let health: Float
    let x: Float
    let y: Float
}

struct ReplayAnalysis: Sendable {
    let gameId: String
    let winRate: Double
    let avgApm: Int
    let keyEvents: [String]
    let duration: TimeInterval
}

enum AnalysisError: Error {
    case fileNotFound(String)
    case parseError(String)
    case networkError(String)
}

// --- Actor for thread-safe state management ---

actor SC2Analyzer {
    private var cachedStates: [String: GameState] = [:]
    private var analysisHistory: [ReplayAnalysis] = []

    // Fetch and cache game state
    func fetchGameState(gameId: String) async throws -> GameState {
        if let cached = cachedStates[gameId] {
            return cached
        }
        // Simulate async network fetch
        try await Task.sleep(nanoseconds: 50_000_000)
        let state = GameState(
            gameId: gameId,
            minerals: 300,
            vespene: 150,
            supplyUsed: 24,
            supplyCap: 44,
            units: [],
            tick: Date().timeIntervalSince1970
        )
        cachedStates[gameId] = state
        return state
    }

    // Analyze a replay file
    func analyzeReplay(path: String) async throws -> ReplayAnalysis {
        guard !path.isEmpty else {
            throw AnalysisError.fileNotFound(path)
        }
        // Simulate heavy computation
        try await Task.sleep(nanoseconds: 100_000_000)
        let analysis = ReplayAnalysis(
            gameId: path,
            winRate: 0.65,
            avgApm: 195,
            keyEvents: ["Proxy rax at 1:30", "All-in push at 4:00"],
            duration: 480.0
        )
        analysisHistory.append(analysis)
        return analysis
    }

    func getHistory() -> [ReplayAnalysis] { analysisHistory }
}

// --- AsyncStream for game events ---

func gameEventStream(gameId: String) -> AsyncStream<String> {
    AsyncStream { continuation in
        Task {
            let events = ["unit_created", "resource_update", "unit_killed", "game_ended"]
            for event in events {
                try? await Task.sleep(nanoseconds: 200_000_000)
                continuation.yield("\(gameId):\(event)")
            }
            continuation.finish()
        }
    }
}

// --- Main Entry ---

@main
struct SC2AnalyzerApp {
    static func main() async {
        let analyzer = SC2Analyzer()

        // Parallel analysis with async let
        async let state = try analyzer.fetchGameState(gameId: "game-001")
        async let replay1 = try analyzer.analyzeReplay(path: "replay_001.SC2Replay")
        async let replay2 = try analyzer.analyzeReplay(path: "replay_002.SC2Replay")

        do {
            let (gameState, r1, r2) = try await (state, replay1, replay2)
            print("Game State minerals: \(gameState.minerals)")
            print("Replay 1 win rate: \(r1.winRate)")
            print("Replay 2 avg APM: \(r2.avgApm)")
        } catch {
            print("Analysis failed: \(error)")
        }

        // Stream game events
        print("Streaming events for game-001:")
        for await event in gameEventStream(gameId: "game-001") {
            print("  Event: \(event)")
        }
    }
}
