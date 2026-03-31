import Vapor
import Fluent
import JWT

// --- Models ---

final class Game: Model, Content {
    static let schema = "games"

    @ID(key: .id) var id: UUID?
    @Field(key: "game_id") var gameId: String
    @Field(key: "winner") var winner: String
    @Field(key: "duration") var duration: Double
    @Field(key: "player_race") var playerRace: String
    @Timestamp(key: "created_at", on: .create) var createdAt: Date?

    init() {}

    init(id: UUID? = nil, gameId: String, winner: String, duration: Double, playerRace: String) {
        self.id = id
        self.gameId = gameId
        self.winner = winner
        self.duration = duration
        self.playerRace = playerRace
    }
}

struct ReplayUpload: Content {
    var file: File
    var playerName: String
    var race: String
}

struct LeaderboardEntry: Content {
    var rank: Int
    var playerName: String
    var mmr: Int
    var winRate: Double
}

struct SC2JWTPayload: JWTPayload {
    var subject: SubjectClaim
    var expiration: ExpirationClaim
    var isAdmin: Bool

    func verify(using algorithm: some JWTAlgorithm) async throws {
        try expiration.verifyNotExpired()
    }
}

// --- Controller ---

struct SC2Controller: RouteCollection {
    func boot(routes: RoutesBuilder) throws {
        let api = routes.grouped("api")
        let protected = api.grouped(JWTMiddleware())

        // Public routes
        api.get("games", use: listGames)
        api.get("leaderboard", use: getLeaderboard)

        // Protected routes
        protected.post("replays", use: uploadReplay)
        protected.delete("games", ":gameId", use: deleteGame)
    }

    // GET /api/games
    func listGames(req: Request) async throws -> [Game] {
        let page = try req.query.decode(PageRequest.self)
        return try await Game.query(on: req.db)
            .sort(\.$createdAt, .descending)
            .paginate(for: req)
            .items
    }

    // POST /api/replays
    func uploadReplay(req: Request) async throws -> HTTPStatus {
        let payload = try req.jwt.verify(as: SC2JWTPayload.self)
        let upload = try req.content.decode(ReplayUpload.self)

        let filePath = req.application.directory.publicDirectory + "replays/" + upload.file.filename
        try await req.fileio.writeFile(upload.file.data, at: filePath)

        let game = Game(
            gameId: UUID().uuidString,
            winner: payload.subject.value,
            duration: 0.0,
            playerRace: upload.race
        )
        try await game.save(on: req.db)

        req.logger.info("Replay uploaded by \(payload.subject.value): \(upload.file.filename)")
        return .created
    }

    // GET /api/leaderboard
    func getLeaderboard(req: Request) async throws -> [LeaderboardEntry] {
        let games = try await Game.query(on: req.db).all()
        let grouped = Dictionary(grouping: games, by: \.winner)
        let entries = grouped.map { (player, playerGames) -> LeaderboardEntry in
            let wins = playerGames.filter { $0.winner == player }.count
            return LeaderboardEntry(
                rank: 0,
                playerName: player,
                mmr: wins * 25,
                winRate: Double(wins) / Double(max(playerGames.count, 1))
            )
        }
        return entries
            .sorted { $0.mmr > $1.mmr }
            .enumerated()
            .map { (idx, entry) in
                LeaderboardEntry(rank: idx + 1, playerName: entry.playerName,
                                 mmr: entry.mmr, winRate: entry.winRate)
            }
    }

    // DELETE /api/games/:gameId
    func deleteGame(req: Request) async throws -> HTTPStatus {
        _ = try req.jwt.verify(as: SC2JWTPayload.self)
        guard let game = try await Game.find(req.parameters.get("gameId"), on: req.db) else {
            throw Abort(.notFound)
        }
        try await game.delete(on: req.db)
        return .noContent
    }
}
