"""
초기 데이터베이스 스키마 마이그레이션 (#175)

마이그레이션 번호: 001
설명: JARVIS 시스템의 초기 테이블 구조를 생성한다.
생성 테이블:
  - trades          : 거래 기록
  - portfolio_snapshots : 포트폴리오 스냅샷
  - api_logs        : API 호출 로그
  - bot_sessions    : SC2 봇 세션 기록
  - migrations      : 마이그레이션 이력 추적
"""

# 마이그레이션 메타데이터
MIGRATION_ID = "001_initial"
DESCRIPTION = "초기 데이터베이스 스키마 생성"
CREATED_AT = "2026-02-18"


def upgrade(conn) -> None:
    """
    마이그레이션을 적용한다 (forward).
    SQLite와 PostgreSQL 모두 호환되는 SQL을 사용한다.

    Args:
        conn: 데이터베이스 연결 객체 (sqlite3.Connection 등)
    """
    cursor = conn.cursor()

    # ── 마이그레이션 이력 테이블 ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_id TEXT    NOT NULL UNIQUE,
            description  TEXT,
            applied_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── 거래 기록 테이블 ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id        TEXT    NOT NULL UNIQUE,
            symbol          TEXT    NOT NULL,
            side            TEXT    NOT NULL CHECK(side IN ('buy', 'sell')),
            price           REAL    NOT NULL,
            quantity         REAL    NOT NULL,
            total_amount     REAL    NOT NULL,
            fee              REAL    DEFAULT 0,
            status           TEXT    NOT NULL DEFAULT 'pending'
                             CHECK(status IN ('pending', 'completed', 'failed', 'cancelled')),
            strategy         TEXT,
            dry_run          INTEGER DEFAULT 0,
            error_message    TEXT,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 거래 검색 인덱스
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)
    """)

    # ── 포트폴리오 스냅샷 테이블 ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            total_value_krw  REAL    NOT NULL,
            cash_balance_krw REAL    NOT NULL DEFAULT 0,
            positions_json   TEXT,
            snapshot_type    TEXT    DEFAULT 'auto'
                             CHECK(snapshot_type IN ('auto', 'manual', 'daily')),
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_portfolio_created_at
        ON portfolio_snapshots(created_at)
    """)

    # ── API 호출 로그 테이블 ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            service          TEXT    NOT NULL,
            endpoint         TEXT    NOT NULL,
            method           TEXT    DEFAULT 'GET',
            status_code      INTEGER,
            response_time_ms REAL,
            request_body     TEXT,
            response_body    TEXT,
            error_message    TEXT,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_logs_service ON api_logs(service)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_logs_created_at ON api_logs(created_at)
    """)

    # ── SC2 봇 세션 테이블 ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id       TEXT    NOT NULL UNIQUE,
            opponent_race    TEXT,
            map_name         TEXT,
            result           TEXT    CHECK(result IN ('win', 'loss', 'tie', 'crash', NULL)),
            duration_seconds INTEGER,
            strategy_used    TEXT,
            apm              REAL,
            score            INTEGER,
            replay_path      TEXT,
            notes            TEXT,
            started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at         TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bot_sessions_result ON bot_sessions(result)
    """)

    # ── 설정 저장 테이블 (키-값) ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key         TEXT PRIMARY KEY,
            value       TEXT,
            description TEXT,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    print(f"[마이그레이션 001] 초기 스키마 생성 완료")


def downgrade(conn) -> None:
    """
    마이그레이션을 롤백한다 (backward).
    주의: 데이터가 삭제된다!

    Args:
        conn: 데이터베이스 연결 객체
    """
    cursor = conn.cursor()

    tables = ["settings", "bot_sessions", "api_logs", "portfolio_snapshots", "trades", "migrations"]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    conn.commit()
    print(f"[마이그레이션 001] 롤백 완료 - 모든 테이블 삭제됨")
