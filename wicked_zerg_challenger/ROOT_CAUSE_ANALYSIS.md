# 근본 원인 분석 (Root Cause Analysis)

**분석 날짜**: 2026-01-25 15:25
**분석 대상**: 70게임 백그라운드 학습 실패
**Task ID**: bbdb771

---

## 🚨 심각한 문제 발견

### 1. 모든 게임 실패 (100% 실패율)

**현상**:
```
Game #1: FAILED - ProtocolError: ['Not in a game']
Game #2: FAILED - ProtocolError: ['Not in a game']
Game #3: FAILED - ProtocolError: ['Not in a game']
Game #4: FAILED - ProtocolError: ['Not in a game']
Game #5: FAILED - ProtocolError: ['Not in a game']
```

**원인**: 600초 auto-surrender 시 SC2 클라이언트 연결 오류

### 2. 경험 데이터 생성 실패 (0개 파일)

**현상**:
```bash
$ ls -la local_training/data/buffer/
total 0
(EMPTY DIRECTORY)

$ ls -la local_training/data/archive/
exp_20260125_141112_ep0.npz  (테스트 게임 데이터)
old_exp_20260125_141112_ep0.npz  (복사본)
```

**결과**:
- ✅ **buffer/**: 0개 파일 (5게임 동안 아무것도 생성 안 됨)
- ✅ **archive/**: 2개 파일 (이전 테스트 게임)
- ❌ **5게임 동안 경험 데이터 0개 생성됨**

### 3. Background Learner 무용지물

**Status Report**:
```
Files Processed:      0
Files Skipped (Old):  1
Batch Training Runs:  0
Total Samples:        0
```

**결론**: 학습 데이터가 없어서 학습 불가능

---

## 🔍 근본 원인 (Root Cause)

### 원인 #1: ProtocolError로 인한 게임 비정상 종료

**파일**: run_with_training.py
**증상**:
```python
[AUTO SURRENDER] Game time limit reached (600s). Surrendering...
Traceback (most recent call last):
  ...
  sc2.protocol.ProtocolError: ['Not in a game']

[ERROR] Game #X failed: ['Not in a game']
```

**분석**:
1. 게임이 600초에 도달하면 auto-surrender 실행
2. SC2 클라이언트가 이미 연결 해제됨
3. ProtocolError 발생
4. **end_episode()가 호출되지 않음** ← 핵심 문제!
5. 경험 데이터 저장 안 됨

**영향**:
- 게임 결과가 제대로 저장되지 않음
- RLAgent.end_episode() 호출 안 됨
- 경험 데이터 .npz 파일 생성 안 됨

### 원인 #2: Economy Logic Deadlock

**파일**: unit_factory.py:158-176 (수정 전)
**로직**:
```python
if base_count < 4 and game_time > 280 and pending_hatch == 0:
     if self.bot.minerals < 350:
         return  # 모든 유닛 생산 중단!
```

**문제점**:
1. 4번째 베이스를 위해 미네랄 350을 모으려고 시도
2. 미네랄 < 350이면 **모든 유닛 생산 중단**
3. 유닛이 없어서 방어 실패 → 일꾼 사망
4. 미네랄이 5-80에 갇힘 (350 도달 불가)
5. 악순환: 생산 중단 → 방어 실패 → 자원 부족 → 생산 중단

**실제 로그**:
```
[UNIT_FACTORY] Saving minerals for 4th Base (Time: 553s)
[EXPANSION] [553s] Cannot afford Hatchery (need 300 minerals) - minerals: 25
[UNIT_FACTORY] Saving minerals for 4th Base (Time: 571s)
[EXPANSION] [571s] Cannot afford Hatchery (need 300 minerals) - minerals: 25
```

**결과**: 게임 시간 553-600초 동안 유닛 생산 0개, 방어 불가, 패배

### 원인 #3: realtime=False로 인한 속도 문제

**설정**: `realtime=False` (게임 창 없음, 빠른 속도)

**가능한 문제**:
1. 게임이 너무 빨리 진행되어 봇 로직이 따라가지 못함
2. SC2 클라이언트 안정성 저하
3. ProtocolError 발생 확률 증가

---

## 📊 근본 원인 요약

| 순위 | 근본 원인 | 영향도 | 해결 난이도 |
|------|-----------|--------|-------------|
| **1** | **ProtocolError로 end_episode() 미호출** | ⭐⭐⭐⭐⭐ 치명적 | 🔧 중간 |
| **2** | **Economy Logic Deadlock** | ⭐⭐⭐⭐ 심각 | 🔧 쉬움 (이미 수정함) |
| **3** | **realtime=False 속도 문제** | ⭐⭐⭐ 보통 | 🔧 쉬움 |

---

## 🛠️ 해결 방안

### 해결책 #1: ProtocolError 처리 개선 (최우선)

**파일**: run_with_training.py

**현재 코드**:
```python
try:
    run_game(...)
except Exception as e:
    print(f"[ERROR] Game #{game_count} failed: {e}")
    consecutive_failures += 1
    # ← end_episode() 호출 안 됨!
```

**수정안**:
```python
try:
    run_game(...)
except Exception as e:
    print(f"[ERROR] Game #{game_count} failed: {e}")

    # ★ 게임 실패해도 경험 데이터 저장 시도 ★
    try:
        if hasattr(bot, 'rl_agent') and bot.rl_agent:
            bot.rl_agent.end_episode(game_won=False)
    except Exception as save_err:
        print(f"[ERROR] Failed to save experience: {save_err}")

    consecutive_failures += 1
```

### 해결책 #2: Economy Logic 수정 (완료 ✅)

**수정 내용**:
- 미네랄 < 200일 때는 유닛 생산 계속 (방어 유지)
- 미네랄 200-350일 때만 확장 세이빙
- 공격 받을 때는 세이빙 비활성화

### 해결책 #3: Auto-Surrender 타이밍 개선

**현재**: 600초에 강제 surrender
**문제**: SC2 클라이언트 연결 끊기면서 ProtocolError

**수정안**:
```python
# 590초에 미리 종료 처리
if self.time >= 590:
    # end_episode 먼저 호출
    if hasattr(self, 'rl_agent'):
        self.rl_agent.end_episode(game_won=False)
    # 그 다음 surrender
    await self.client.leave()
```

### 해결책 #4: realtime 모드 재검토

**옵션 A**: realtime=True로 복귀
- 장점: 안정성 향상
- 단점: 학습 속도 느림

**옵션 B**: realtime=False 유지 + 에러 처리 강화
- 장점: 빠른 학습
- 단점: 에러 처리 복잡

---

## 📝 우선 순위

### 즉시 수정 (Critical)
1. ✅ **Economy Logic Deadlock** - 이미 수정함 (unit_factory.py)
2. ❌ **ProtocolError 처리 개선** - run_with_training.py 수정 필요
3. ❌ **Auto-Surrender 타이밍** - wicked_zerg_bot_pro_impl.py 수정 필요

### 추가 개선 (Important)
4. realtime 모드 최적화
5. Background Learner 파일 감지 개선
6. 게임 실패 시 재시도 로직 강화

---

## 🎯 다음 단계

### 1단계: 긴급 수정
```bash
# 수정할 파일
1. run_with_training.py - 게임 실패 시 end_episode() 호출 추가
2. wicked_zerg_bot_pro_impl.py - 590초에 미리 종료 처리
```

### 2단계: 검증
```bash
# 3게임 테스트 실행
python run_with_training.py --num_games 3

# 확인 사항
1. buffer/에 exp_*.npz 파일 3개 생성되는지
2. ProtocolError 발생해도 파일 저장되는지
3. Background Learner가 파일 처리하는지
```

### 3단계: 대량 학습 재시작
```bash
# 수정 검증 후 70게임 재실행
python run_with_training.py --num_games 70
```

---

## 📌 중요 발견

### 발견 #1: 5게임 동안 경험 데이터 0개
**의미**: 현재 시스템은 **학습이 불가능한 상태**

### 발견 #2: ProtocolError가 모든 게임에서 발생
**의미**: auto-surrender 메커니즘에 근본적 문제 있음

### 발견 #3: Economy Logic이 게임 패배의 주범
**의미**: 미네랄 세이빙 로직이 오히려 경제를 망침

---

**분석 완료 시각**: 2026-01-25 15:25
**분석자**: Claude Code
**상태**: ⚠️ **긴급 수정 필요**
