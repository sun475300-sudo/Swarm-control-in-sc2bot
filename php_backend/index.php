<?php
/**
 * P102: PHP - Web Backend API
 * REST API for game statistics and bot control
 */

header('Content-Type: application/json');

class GameAPIController {
    private $db;
    
    public function __construct() {
        $this->db = new SQLite3('game_data.db');
        $this->initDatabase();
    }
    
    private function initDatabase() {
        $this->db->exec("CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY,
            map TEXT,
            result TEXT,
            enemy_race TEXT,
            duration INTEGER,
            units_killed INTEGER,
            units_lost INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )");
    }
    
    public function getGames($limit = 10) {
        $stmt = $this->db->prepare("SELECT * FROM games ORDER BY timestamp DESC LIMIT :limit");
        $stmt->bindValue(':limit', $limit, SQLITE3_INTEGER);
        $result = $stmt->execute();
        
        $games = [];
        while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
            $games[] = $row;
        }
        return $games;
    }
    
    public function addGame($data) {
        $stmt = $this->db->prepare("INSERT INTO games (map, result, enemy_race, duration, units_killed, units_lost) 
            VALUES (:map, :result, :enemy_race, :duration, :killed, :lost)");
        $stmt->bindValue(':map', $data['map']);
        $stmt->bindValue(':result', $data['result']);
        $stmt->bindValue(':enemy_race', $data['enemy_race']);
        $stmt->bindValue(':duration', $data['duration']);
        $stmt->bindValue(':killed', $data['units_killed']);
        $stmt->bindValue(':lost', $data['units_lost']);
        return $stmt->execute();
    }
    
    public function getStats() {
        $result = $this->db->query("SELECT 
            COUNT(*) as total_games,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
            AVG(duration) as avg_duration
            FROM games");
        return $result->fetchArray(SQLITE3_ASSOC);
    }
}

$api = new GameAPIController();
$action = $_GET['action'] ?? 'stats';

switch ($action) {
    case 'games':
        echo json_encode($api->getGames($_GET['limit'] ?? 10));
        break;
    case 'add':
        $api->addGame(json_decode(file_get_contents('php://input'), true));
        echo json_encode(['status' => 'success']);
        break;
    case 'stats':
    default:
        echo json_encode($api->getStats());
}
