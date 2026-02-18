"""
마이그레이션 실행기 (#175)

데이터베이스 마이그레이션을 순차적으로 실행하고 관리한다.

사용법:
    # 모든 미적용 마이그레이션 실행
    python migrations/migrate.py

    # 특정 마이그레이션까지만 실행
    python migrations/migrate.py --target 001_initial

    # 마이그레이션 상태 확인
    python migrations/migrate.py --status

    # 마지막 마이그레이션 롤백
    python migrations/migrate.py --rollback

    # 커스텀 DB 경로 지정
    python migrations/migrate.py --db ./data/jarvis.db
"""

import argparse
import importlib
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 마이그레이션 파일 디렉토리
MIGRATIONS_DIR = Path(__file__).parent

# 기본 DB 경로
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "jarvis.db"


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    SQLite 데이터베이스 연결을 반환한다.

    Args:
        db_path: 데이터베이스 파일 경로 (없으면 기본 경로 사용)

    Returns:
        sqlite3.Connection 객체
    """
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    """마이그레이션 이력 테이블이 존재하는지 확인하고 없으면 생성한다."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_id TEXT    NOT NULL UNIQUE,
            description  TEXT,
            applied_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def get_applied_migrations(conn: sqlite3.Connection) -> List[str]:
    """이미 적용된 마이그레이션 ID 목록을 반환한다."""
    ensure_migrations_table(conn)
    cursor = conn.execute(
        "SELECT migration_id FROM migrations ORDER BY id ASC"
    )
    return [row[0] for row in cursor.fetchall()]


def discover_migrations() -> List[Tuple[str, Path]]:
    """
    migrations/ 디렉토리에서 마이그레이션 파일을 탐색한다.
    파일명 패턴: NNN_description.py (예: 001_initial.py)

    Returns:
        (마이그레이션 ID, 파일 경로) 튜플 리스트 (번호순 정렬)
    """
    migrations = []
    for f in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.py")):
        migration_id = f.stem  # 예: "001_initial"
        migrations.append((migration_id, f))
    return migrations


def load_migration_module(migration_id: str, file_path: Path):
    """마이그레이션 파일을 Python 모듈로 로드한다."""
    spec = importlib.util.spec_from_file_location(
        f"migration_{migration_id}", str(file_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_upgrade(
    conn: sqlite3.Connection,
    target: Optional[str] = None,
) -> int:
    """
    미적용 마이그레이션을 순차적으로 실행한다.

    Args:
        conn: 데이터베이스 연결
        target: 목표 마이그레이션 ID (없으면 전체 실행)

    Returns:
        적용된 마이그레이션 수
    """
    applied = get_applied_migrations(conn)
    all_migrations = discover_migrations()
    applied_count = 0

    for migration_id, file_path in all_migrations:
        if migration_id in applied:
            continue

        print(f"[마이그레이션] 적용 중: {migration_id}...")
        module = load_migration_module(migration_id, file_path)

        if not hasattr(module, "upgrade"):
            print(f"  경고: {migration_id}에 upgrade() 함수가 없습니다. 건너뜁니다.")
            continue

        try:
            module.upgrade(conn)
            # 마이그레이션 이력에 기록
            description = getattr(module, "DESCRIPTION", "")
            conn.execute(
                "INSERT INTO migrations (migration_id, description) VALUES (?, ?)",
                (migration_id, description),
            )
            conn.commit()
            applied_count += 1
            print(f"  완료: {migration_id}")
        except Exception as e:
            conn.rollback()
            print(f"  실패: {migration_id} - {e}")
            raise

        if target and migration_id == target:
            print(f"[마이그레이션] 목표 {target}에 도달했습니다.")
            break

    if applied_count == 0:
        print("[마이그레이션] 적용할 마이그레이션이 없습니다. 이미 최신 상태입니다.")
    else:
        print(f"[마이그레이션] 총 {applied_count}개 마이그레이션 적용 완료")

    return applied_count


def run_rollback(conn: sqlite3.Connection, steps: int = 1) -> int:
    """
    최근 마이그레이션을 롤백한다.

    Args:
        conn: 데이터베이스 연결
        steps: 롤백할 마이그레이션 수

    Returns:
        롤백된 마이그레이션 수
    """
    applied = get_applied_migrations(conn)
    if not applied:
        print("[롤백] 적용된 마이그레이션이 없습니다.")
        return 0

    all_migrations = {mid: fp for mid, fp in discover_migrations()}
    rolled_back = 0

    for migration_id in reversed(applied[-steps:]):
        file_path = all_migrations.get(migration_id)
        if not file_path:
            print(f"  경고: {migration_id}의 파일을 찾을 수 없습니다.")
            continue

        print(f"[롤백] 되돌리는 중: {migration_id}...")
        module = load_migration_module(migration_id, file_path)

        if not hasattr(module, "downgrade"):
            print(f"  경고: {migration_id}에 downgrade() 함수가 없습니다.")
            continue

        try:
            module.downgrade(conn)
            conn.execute(
                "DELETE FROM migrations WHERE migration_id = ?",
                (migration_id,),
            )
            conn.commit()
            rolled_back += 1
            print(f"  완료: {migration_id} 롤백됨")
        except Exception as e:
            conn.rollback()
            print(f"  실패: {migration_id} 롤백 실패 - {e}")
            raise

    print(f"[롤백] 총 {rolled_back}개 마이그레이션 롤백 완료")
    return rolled_back


def show_status(conn: sqlite3.Connection) -> None:
    """마이그레이션 적용 상태를 표시한다."""
    applied = get_applied_migrations(conn)
    all_migrations = discover_migrations()

    print("=" * 60)
    print("  JARVIS 데이터베이스 마이그레이션 상태")
    print("=" * 60)

    if not all_migrations:
        print("  마이그레이션 파일이 없습니다.")
        return

    for migration_id, file_path in all_migrations:
        status = "적용됨" if migration_id in applied else "미적용"
        marker = "[O]" if migration_id in applied else "[ ]"
        print(f"  {marker} {migration_id:30s} ({status})")

    print("-" * 60)
    print(f"  전체: {len(all_migrations)}개 | "
          f"적용: {len(applied)}개 | "
          f"미적용: {len(all_migrations) - len(applied)}개")
    print("=" * 60)


def main() -> None:
    """CLI 메인 함수."""
    parser = argparse.ArgumentParser(
        description="JARVIS 데이터베이스 마이그레이션 도구",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help=f"데이터베이스 파일 경로 (기본: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="목표 마이그레이션 ID (예: 001_initial)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="마이그레이션 적용 상태 확인",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="마지막 마이그레이션 롤백",
    )
    parser.add_argument(
        "--rollback-steps",
        type=int,
        default=1,
        help="롤백할 마이그레이션 수 (기본: 1)",
    )

    args = parser.parse_args()
    conn = get_connection(args.db)

    try:
        if args.status:
            show_status(conn)
        elif args.rollback:
            run_rollback(conn, steps=args.rollback_steps)
        else:
            run_upgrade(conn, target=args.target)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
