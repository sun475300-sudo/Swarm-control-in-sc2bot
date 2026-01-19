# ConnectionAlreadyClosedError 해결 가이드

**작성일**: 2026-01-15  
**목적**: `ConnectionAlreadyClosedError` 오류 해결 및 예방

---

## ? 오류 원인

`ConnectionAlreadyClosedError`는 StarCraft II 클라이언트와의 WebSocket 연결이 예기치 않게 종료되었을 때 발생합니다.

### 주요 원인

1. **이전 게임 세션이 완전히 종료되지 않음**
   - 게임이 끝난 후 SC2 프로세스가 완전히 종료되기 전에 새 게임 시작
   - WebSocket 연결이 아직 열려있는 상태에서 새 연결 시도

2. **SC2 클라이언트 크래시**
   - 게임 중 비정상 종료
   - 메모리 부족 또는 시스템 리소스 부족

3. **너무 빠른 연속 게임 시작**
   - 게임 간 대기 시간 부족 (기존: 3초)
   - SC2 클라이언트가 완전히 정리되기 전에 새 게임 시작

4. **포트 충돌**
   - 이전 게임의 포트가 아직 사용 중
   - 네트워크 리소스 충돌

---

## ? 해결 방법

### 1. 게임 간 대기 시간 증가

**변경 사항**:
- 기존: 3초 대기
- 개선: 10초 대기 (SC2 클라이언트 완전 종료 대기)

**코드 위치**: `run_with_training.py` line 277-279

```python
# IMPROVED: Longer wait time between games
wait_between_games = 10  # Increased from 3 to 10 seconds
print(f"[NEXT] Automatically starting next game in {wait_between_games} seconds...")
```

### 2. 연결 오류 특별 처리

**변경 사항**:
- 연결 오류 감지 및 더 긴 대기 시간 (15초)
- 상세한 오류 메시지 및 해결 방법 안내

**코드 위치**: `run_with_training.py` line 284-298

```python
# IMPROVED: Handle connection errors with longer wait time
error_msg = str(game_error).lower()
is_connection_error = (
    "connection" in error_msg or
    "connectionalreadyclosed" in error_msg or
    "websocket" in error_msg or
    "closing transport" in error_msg
)

if is_connection_error:
    wait_time = 15  # Longer wait for connection errors
    print(f"[ERROR] Connection error detected")
    print(f"[INFO] Waiting {wait_time} seconds for SC2 client to fully close...")
```

### 3. SC2 프로세스 모니터링

**변경 사항**:
- `psutil`을 사용하여 SC2 프로세스가 완전히 종료되었는지 확인
- 프로세스가 종료될 때까지 대기

**코드 위치**: `run_with_training.py` line 280-297

```python
# IMPROVED: Check if SC2 processes are still running before next game
try:
    import psutil
    for _ in range(wait_between_games):
        sc2_running = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if 'sc2' in proc_name or 'starcraft' in proc_name:
                    sc2_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if not sc2_running:
            # SC2 processes closed, can proceed
            break
        
        time.sleep(1)
except ImportError:
    # psutil not available, use simple sleep
    time.sleep(wait_between_games)
```

### 4. 의존성 추가

**변경 사항**:
- `psutil>=5.9.0` 추가 (프로세스 모니터링용)

**파일**: `wicked_zerg_challenger/requirements.txt`

```txt
# System and process utilities (for SC2 process monitoring)
psutil>=5.9.0
```

---

## ? 사용 방법

### 1. 의존성 설치

```bash
pip install psutil>=5.9.0
```

또는

```bash
pip install -r wicked_zerg_challenger/requirements.txt
```

### 2. 훈련 시작

```bash
python wicked_zerg_challenger/run_with_training.py
```

또는

```bash
wicked_zerg_challenger\bat\start_model_training.bat
```

### 3. 오류 발생 시

연결 오류가 발생하면:
1. 자동으로 15초 대기
2. SC2 프로세스 종료 확인
3. 자동 재시도

---

## ? 예방 방법

### 1. 수동 확인

게임이 끝난 후 다음을 확인:
- SC2 게임 창이 완전히 닫혔는지 확인
- 작업 관리자에서 SC2 프로세스가 종료되었는지 확인

### 2. 시스템 리소스 확인

- 메모리 사용량 확인 (최소 4GB 여유 공간 권장)
- CPU 사용률 확인 (과도한 부하 방지)

### 3. 게임 간 충분한 대기 시간

- 자동 대기 시간: 10초 (기본값)
- 연결 오류 시: 15초
- 수동으로 더 긴 대기 시간 설정 가능

---

## ? 개선 효과

### Before (기존)
- 게임 간 대기: 3초
- 연결 오류 시 대기: 5초
- 프로세스 확인: 없음
- 오류 발생 빈도: 높음

### After (개선)
- 게임 간 대기: 10초 (SC2 프로세스 종료 확인)
- 연결 오류 시 대기: 15초
- 프로세스 확인: `psutil`로 자동 확인
- 오류 발생 빈도: 낮음 (예상)

---

## ? 추가 개선 사항

### 향후 개선 가능 사항

1. **동적 대기 시간 조정**
   - 시스템 리소스에 따라 대기 시간 자동 조정
   - 프로세스 종료 시간에 따라 대기 시간 조정

2. **강제 프로세스 종료**
   - 일정 시간 후에도 프로세스가 종료되지 않으면 강제 종료
   - `psutil`을 사용하여 프로세스 종료

3. **연결 상태 모니터링**
   - WebSocket 연결 상태 실시간 모니터링
   - 연결 끊김 감지 및 자동 재연결

---

## ? 문제 해결 체크리스트

연결 오류가 계속 발생하는 경우:

- [ ] SC2 게임 창이 완전히 닫혔는지 확인
- [ ] 작업 관리자에서 SC2 프로세스가 종료되었는지 확인
- [ ] 시스템 메모리가 충분한지 확인 (최소 4GB 여유)
- [ ] 다른 SC2 인스턴스가 실행 중인지 확인
- [ ] 방화벽이 SC2 연결을 차단하지 않는지 확인
- [ ] `psutil`이 설치되어 있는지 확인 (`pip install psutil`)

---

**최종 상태**: ? **연결 오류 처리 개선 완료**

연결 오류 발생 시 자동으로 더 긴 대기 시간을 사용하고, SC2 프로세스 종료를 확인한 후 재시도합니다.
