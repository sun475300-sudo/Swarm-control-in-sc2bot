-- Phase 60: Release Validation Query (SQLite)
-- 릴리스 준비 상태 데이터베이스 검증

-- 버전 정보 테이블 생성
CREATE TABLE IF NOT EXISTS release_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,
    phase INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending'
);

-- 체크리스트 결과 테이블
CREATE TABLE IF NOT EXISTS release_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    duration_ms INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 게임 데이터 테이블
CREATE TABLE IF NOT EXISTS game_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    enemy_race TEXT,
    result TEXT,
    duration_seconds INTEGER,
    map_name TEXT
);

-- 테스트 결과 테이블
CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    status TEXT NOT NULL,
    file_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Phase 60 체크리스트 삽입
INSERT OR REPLACE INTO release_checks (check_name, status, message) VALUES
    ('Python Syntax', 'pending', 'Checking Python files...'),
    ('TypeScript Compile', 'pending', 'Checking TypeScript...'),
    ('Test Suite', 'pending', 'Checking tests...'),
    ('Package Structure', 'pending', 'Checking package...'),
    ('Documentation', 'pending', 'Checking docs...'),
    ('Rust Check', 'pending', 'Checking Rust...');

-- 버전 정보 삽입
INSERT INTO release_version (version, phase, status) VALUES ('1.0.0', 60, 'in_progress');

-- 쿼리: 릴리스 준비 상태 요약
SELECT 
    'Phase 60 Release Status' AS title,
    COUNT(*) AS total_checks,
    SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN status = 'fail' THEN 1 ELSE 0 END) AS failed
FROM release_checks;

-- 쿼리: 최근 게임 결과 통계
SELECT 
    enemy_race,
    COUNT(*) AS total_games,
    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) AS losses,
    ROUND(CAST(SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1) AS win_rate
FROM game_results
GROUP BY enemy_race;

-- 쿼리: 테스트 통과율
SELECT 
    COUNT(*) AS total_tests,
    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
FROM test_results;
