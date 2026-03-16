
import json
import os
import threading
import tempfile
import time


class MemoryManager:
    """사용자별 정보를 JSON 파일에 저장하고 관리하는 클래스

    스레드 안전하게 동작하며, 원자적 파일 쓰기를 보장합니다.
    디바운스: 변경 10건 또는 30초마다 실제 디스크에 flush합니다.
    """

    _DEBOUNCE_COUNT = 10   # 이 횟수만큼 변경되면 flush
    _DEBOUNCE_SEC = 30.0   # 이 시간 경과 시 flush

    def __init__(self, filepath="data/memory.json"):
        self.filepath = filepath
        self.memory = {}
        self._lock = threading.Lock()  # threading.Lock (not asyncio) — sync file I/O via asyncio.to_thread()
        self._save_count = 0
        self._AUTO_BACKUP_INTERVAL = 50  # N회 저장마다 자동 백업
        self._dirty = False
        self._dirty_count = 0
        self._last_flush_time = time.monotonic()
        self.load()

    def load(self):
        with self._lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        self.memory = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"[Memory] Load failed: {e}")
                    self.memory = {}
            else:
                self.memory = {}

    def save(self):
        with self._lock:
            self._save_locked()

    def flush(self):
        """미저장 변경을 즉시 디스크에 기록 (봇 종료 시 호출)."""
        with self._lock:
            if self._dirty:
                self._save_locked()
                self._dirty = False
                self._dirty_count = 0
                self._last_flush_time = time.monotonic()

    def _mark_dirty(self):
        """변경 플래그만 세우고, 임계치 도달 시에만 실제 저장."""
        self._dirty = True
        self._dirty_count += 1
        elapsed = time.monotonic() - self._last_flush_time
        if self._dirty_count >= self._DEBOUNCE_COUNT or elapsed >= self._DEBOUNCE_SEC:
            self._save_locked()
            self._dirty = False
            self._dirty_count = 0
            self._last_flush_time = time.monotonic()

    def _save_locked(self):
        """_lock이 이미 획득된 상태에서 호출 (내부 전용)"""
        try:
            dir_path = os.path.dirname(self.filepath)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # 원자적 쓰기: 임시 파일에 먼저 쓰고 교체
            fd, tmp_path = tempfile.mkstemp(
                dir=dir_path or ".", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self.memory, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self.filepath)
            except Exception:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
                raise

            # 자동 백업
            self._save_count += 1
            if self._save_count % self._AUTO_BACKUP_INTERVAL == 0:
                self._auto_backup()

        except Exception as e:
            print(f"[Memory] Save failed: {e}")

    def _auto_backup(self):
        """주기적 자동 백업 (최근 3개 유지)"""
        import shutil
        from datetime import datetime
        try:
            if not os.path.exists(self.filepath):
                return
            backup_dir = os.path.join(os.path.dirname(self.filepath) or ".", "backups")
            os.makedirs(backup_dir, exist_ok=True)

            backup_path = os.path.join(
                backup_dir,
                f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            shutil.copy2(self.filepath, backup_path)

            # 오래된 백업 정리 (최근 3개만 유지)
            backups = sorted(
                [f for f in os.listdir(backup_dir) if f.startswith("memory_") and f.endswith(".json")]
            )
            for old_backup in backups[:-3]:
                try:
                    os.remove(os.path.join(backup_dir, old_backup))
                except OSError:
                    pass
        except Exception as e:
            print(f"[Memory] Auto-backup failed: {e}")

    def get_user_memory(self, user_id):
        with self._lock:
            return self.memory.get(str(user_id), {}).copy()

    def update_user_memory(self, user_id, key, value):
        with self._lock:
            uid = str(user_id)
            if uid not in self.memory:
                self.memory[uid] = {}
            self.memory[uid][key] = value
            self._mark_dirty()

    def get_context_string(self, user_id, max_facts=10, max_value_len=100):
        with self._lock:
            mem = self.memory.get(str(user_id), {})
            if not mem:
                return ""
            lines = []
            count = 0
            for k, v in mem.items():
                if k == "chat_history":
                    continue
                lines.append(f"- {k}: {str(v)[:max_value_len]}")
                count += 1
                if count >= max_facts:
                    break
            return "\n".join(lines)

    MAX_CHAT_HISTORY = 100

    def add_chat_history(self, user_id, role, content, limit=10):
        """대화 내용을 저장하고 파일에 즉시 반영"""
        with self._lock:
            uid = str(user_id)
            if uid not in self.memory:
                self.memory[uid] = {}

            if "chat_history" not in self.memory[uid]:
                self.memory[uid]["chat_history"] = []

            history = self.memory[uid]["chat_history"]
            history.append({"role": role, "content": content})

            # limit 개수만큼 유지 (오래된 것 삭제)
            if len(history) > limit:
                self.memory[uid]["chat_history"] = history[-limit:]

            # Hard cap to prevent unbounded memory growth
            if len(self.memory[uid]["chat_history"]) > self.MAX_CHAT_HISTORY:
                self.memory[uid]["chat_history"] = self.memory[uid]["chat_history"][-self.MAX_CHAT_HISTORY:]

            self._mark_dirty()

    def get_chat_history(self, user_id):
        """저장된 대화 내용 반환"""
        with self._lock:
            uid = str(user_id)
            return list(self.memory.get(uid, {}).get("chat_history", []))

    def search_memory(self, query: str) -> list:
        """모든 사용자 메모리에서 키워드 검색"""
        with self._lock:
            results = []
            query_lower = query.lower()
            for uid, data in self.memory.items():
                for key, value in data.items():
                    if key == "chat_history":
                        continue
                    if query_lower in str(key).lower() or query_lower in str(value).lower():
                        results.append({"user_id": uid, "key": key, "value": value})
            return results

    def get_all_users(self) -> list:
        """메모리에 저장된 모든 사용자 ID 반환"""
        with self._lock:
            return list(self.memory.keys())

    def backup(self) -> str:
        """메모리 파일 백업 생성"""
        import shutil
        from datetime import datetime
        with self._lock:
            backup_path = f"{self.filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                if os.path.exists(self.filepath):
                    shutil.copy2(self.filepath, backup_path)
                    return f"백업 완료: {backup_path}"
                return "백업 대상 파일이 없습니다"
            except Exception as e:
                return f"백업 실패: {e}"

    def get_user_stats(self, user_id) -> dict:
        """사용자의 메모리 통계 반환"""
        with self._lock:
            uid = str(user_id)
            data = self.memory.get(uid, {})
            history = data.get("chat_history", [])
            keys = [k for k in data.keys() if k != "chat_history"]
            return {
                "user_id": uid,
                "stored_facts": len(keys),
                "fact_keys": keys,
                "chat_messages": len(history),
                "memory_size_bytes": len(json.dumps(data, ensure_ascii=False).encode("utf-8")),
            }

    def clear_user(self, user_id) -> bool:
        """사용자의 모든 메모리 삭제"""
        with self._lock:
            uid = str(user_id)
            if uid in self.memory:
                del self.memory[uid]
                self._save_locked()
                return True
            return False

    def export_user(self, user_id) -> dict:
        """사용자 메모리 전체 내보내기"""
        with self._lock:
            return self.memory.get(str(user_id), {}).copy()
