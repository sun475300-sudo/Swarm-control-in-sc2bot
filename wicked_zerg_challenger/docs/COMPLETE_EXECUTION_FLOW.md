# ? 전체 실행 흐름 가이드

**작성일**: 2026-01-14  
**목적**: 프로젝트의 전체 실행 로직을 처음부터 끝까지 한 곳에 정리

---

## ? 목차

1. [시스템 초기화](#1-시스템-초기화)
2. [봇 초기화](#2-봇-초기화)
3. [게임 실행](#3-게임-실행)
4. [실시간 업데이트](#4-실시간-업데이트)
5. [게임 종료](#5-게임-종료)
6. [실행 방법](#실행-방법)

---

## 1. 시스템 초기화

### 1.1 환경 설정

#### SC2 경로 설정
```python
# run.py 또는 main_integrated.py
def _ensure_sc2_path():
    """StarCraft II 설치 경로 자동 탐지"""
    # 1. 환경 변수 확인
    if "SC2PATH" in os.environ:
        return
    
    # 2. Windows 레지스트리에서 탐지
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Blizzard Entertainment\StarCraft II")
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        os.environ["SC2PATH"] = install_path
    except:
        pass
    
    # 3. 일반적인 설치 경로 확인
    common_paths = [
        "C:\\Program Files (x86)\\StarCraft II",
        "C:\\Program Files\\StarCraft II",
        "D:\\StarCraft II",
    ]
    for path in common_paths:
        if os.path.exists(path):
            os.environ["SC2PATH"] = path
            return
```

#### Python 경로 설정
```python
# main_integrated.py
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# sys.path에 프로젝트 경로 추가
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
```

#### 가상 환경 설정
```python
# main_integrated.py
def get_venv_dir() -> Path:
    """가상 환경 디렉토리 탐지"""
    venv_dir = os.environ.get("VENV_DIR")
    if venv_dir and Path(venv_dir).exists():
        return Path(venv_dir)
    
    # 일반적인 경로 확인
    possible_paths = [
        PROJECT_DIR / ".venv",
        Path.home() / ".venv",
        Path(".venv"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    
    return PROJECT_DIR / ".venv"
```

### 1.2 로깅 시스템 초기화

```python
# main_integrated.py
from loguru import logger

logger.remove()
logger.add(sys.stderr, colorize=True, enqueue=True, catch=True, level="INFO")
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logger.add(
    str(log_dir / "training_log.log"),
    rotation="10 MB",
    enqueue=True,
    catch=True,
    level="DEBUG",
    encoding="utf-8",
)
```

### 1.3 PyTorch 설정

```python
# main_integrated.py
import torch

# CPU 스레드 설정
num_threads = int(os.environ.get("TORCH_NUM_THREADS", "12"))
torch.set_num_threads(num_threads)
os.environ["OMP_NUM_THREADS"] = str(num_threads)
os.environ["MKL_NUM_THREADS"] = str(num_threads)

# GPU 설정
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    print(f"[DEVICE] GPU: {gpu_name}")
```

### 1.4 이벤트 루프 설정

```python
# main_integrated.py
import asyncio

# 이벤트 루프 생성
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Windows 전용 설정
if sys.platform == "win32":
    try:
        if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except:
        pass
```

---

## 2. 봇 초기화

### 2.1 WickedZergBotPro 인스턴스 생성

```python
# run.py 또는 main_integrated.py
from wicked_zerg_bot_pro import WickedZergBotPro
from sc2.data import Race

# 봇 인스턴스 생성
bot = WickedZergBotPro(
    train_mode=True,
    instance_id=0,
    personality="serral",
    opponent_race=None,
    game_count=0
)
```

### 2.2 봇 초기화 과정 (__init__)

```python
# wicked_zerg_bot_pro.py
class WickedZergBotPro(BotAI):
    def __init__(self, train_mode=True, instance_id=0, personality="serral", ...):
        super().__init__()
        
        # 1. 기본 설정
        self.instance_id = instance_id
        self.personality = personality.lower()
        self.opponent_race = opponent_race
        self.game_count = game_count
        
        # 2. Personality Manager 초기화
        self.personality_manager = PersonalityManager(self, personality)
        
        # 3. 로깅 시스템 설정
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        self.log_path = os.path.join(project_root, "logs")
        self.data_path = os.path.join(script_dir, "data")
        os.makedirs(self.log_path, exist_ok=True)
        os.makedirs(self.data_path, exist_ok=True)
        
        # 4. GPU/CPU 디바이스 설정
        if PYTORCH_AVAILABLE and torch is not None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = None
        
        # 5. Neural Network 초기화
        if self.use_neural_network:
            model = ZergNet(input_size=15, hidden_size=64, output_size=4)
            if self.device:
                model = model.to(self.device)
            self.neural_network = model
        
        # 6. Manager 변수 선언 (나중에 초기화)
        self.intel: Optional[IntelManager] = None
        self.economy: Optional[EconomyManager] = None
        self.production: Optional[ProductionManager] = None
        self.combat: Optional[CombatManager] = None
        self.scout: Optional[ScoutingSystem] = None
        self.micro: Optional[MicroController] = None
        self.queen_manager: Optional[QueenManager] = None
        # ... 기타 매니저들
        
        # 7. Telemetry Logger 초기화
        from monitoring.telemetry_logger import TelemetryLogger
        self.telemetry_logger = TelemetryLogger(self, instance_id)
        
        # 8. Curriculum Manager 초기화
        from local_training.curriculum_manager import CurriculumManager
        self.curriculum_manager = CurriculumManager()
        
        # 9. GenAI Self-Healing 초기화
        from genai_self_healing import GenAISelfHealing
        self.genai_self_healing = GenAISelfHealing()
        
        # 10. Strategy Audit 초기화
        from local_training.strategy_audit import StrategyAudit
        self.strategy_audit = StrategyAudit()
```

### 2.3 게임 시작 시 초기화 (on_start)

```python
# wicked_zerg_bot_pro.py
async def on_start(self):
    """게임 시작 시 한 번만 실행"""
    
    # 1. Intel Manager 초기화 (가장 먼저 - 다른 매니저들이 의존)
    self.intel = IntelManager(self)
    
    # 2. Economy Manager 초기화
    self.economy = EconomyManager(self)
    
    # 3. Production Manager 초기화
    self.production = ProductionManager(self)
    
    # 4. Combat Manager 초기화
    self.combat = CombatManager(self)
    self.combat.initialize()
    
    # 5. Scouting System 초기화
    self.scout = ScoutingSystem(self)
    self.scout.initialize()
    
    # 6. Micro Controller 초기화
    self.micro = MicroController(self)
    
    # 7. Queen Manager 초기화
    self.queen_manager = QueenManager(self)
    
    # 8. Strategy Analyzer 초기화
    self.strategy_analyzer = StrategyAnalyzer(self)
    
    # 9. Combat Tactics 초기화
    self.combat_tactics = CombatTactics(self)
    
    # 10. Production Resilience 초기화
    self.production_resilience = ProductionResilience(self)
    
    # 11. Telemetry Logger 초기화
    self.telemetry_logger.clear_telemetry()
    
    # 12. 게임 상태 초기화
    self.game_phase = GamePhase.OPENING
    self.current_win_rate = 50.0
    
    # 13. Manus Dashboard 클라이언트 초기화 (환경 변수 확인)
    if os.environ.get("MANUS_DASHBOARD_ENABLED", "0") == "1":
        from monitoring.manus_dashboard_client import ManusDashboardClient
        self.manus_client = ManusDashboardClient()
        # 게임 세션 생성
        await self.manus_client.create_game_session()
```

---

## 3. 게임 실행

### 3.1 게임 시작

```python
# run.py
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2 import maps

def main():
    bot = Bot(Race.Zerg, WickedZergBotPro())
    
    # 로컬 게임 실행
    map_name = "AbyssalReefLE"
    run_game(
        maps.get(map_name),
        [
            bot,
            Computer(Race.Terran, Difficulty.VeryHard)
        ],
        realtime=False
    )
```

### 3.2 매 프레임 실행 (on_step)

```python
# wicked_zerg_bot_pro.py
async def on_step(self, iteration: int):
    """매 게임 프레임마다 실행"""
    
    try:
        # 1. Intel Manager 업데이트 (매 프레임)
        if self.intel is None:
            self.intel = IntelManager(self)
        await self.intel.update()
        
        # 2. Micro Controller 업데이트 (매 프레임)
        if self.micro is None:
            self.micro = MicroController(self)
        await self.micro.update()
        
        # 3. Combat Manager 업데이트 (4프레임마다)
        if iteration % 4 == 0:
            if self.combat is None:
                self.combat = CombatManager(self)
                self.combat.initialize()
            await self.combat.update()
        
        # 4. Production & Economy Manager 업데이트 (22프레임마다)
        if iteration % 22 == 0:
            if self.economy is None:
                self.economy = EconomyManager(self)
            if self.production is None:
                self.production = ProductionManager(self)
            
            await self.economy.update()
            await self.production.update()
        
        # 5. Scouting System 업데이트 (8프레임마다)
        if iteration % 8 == 0:
            if self.scout is None:
                self.scout = ScoutingSystem(self)
                self.scout.initialize()
            await self.scout.update()
        
        # 6. Queen Manager 업데이트 (16프레임마다)
        if iteration % 16 == 0:
            if self.queen_manager is None:
                self.queen_manager = QueenManager(self)
            await self.queen_manager.update()
        
        # 7. Telemetry 로깅 (100프레임마다)
        if self.telemetry_logger.should_log_telemetry(iteration):
            combat_unit_types = {UnitTypeId.ZERGLING, UnitTypeId.ROACH, ...}
            self.telemetry_logger.log_game_state(combat_unit_types)
        
        # 8. 상태 파일 업데이트 (16프레임마다 또는 매 프레임)
        write_interval = 16 if self.instance_id > 0 else 1
        if self.iteration % write_interval == 0:
            status_data = {
                "instance_id": self.instance_id,
                "current_game_time": time_formatted,
                "current_minerals": int(self.minerals),
                "current_supply": f"{self.supply_used}/{self.supply_cap}",
                "status": "GAME_RUNNING",
                "timestamp": time.time(),
            }
            # stats/instance_{id}/status.json에 저장
            write_status_file(self.instance_id, status_data)
        
        # 9. Manus Dashboard 실시간 동기화 (5초마다)
        if hasattr(self, 'manus_client') and iteration % 150 == 0:  # 약 5초
            await self.manus_client.update_game_state({
                "minerals": self.minerals,
                "vespene": self.vespene,
                "supply_used": self.supply_used,
                "supply_cap": self.supply_cap,
                # ... 기타 상태
            })
        
        # 10. Neural Network 추론 (24프레임마다)
        if self.use_neural_network and iteration % self.neural_network_inference_interval == 0:
            state = self._get_neural_network_state()
            action = self.neural_network(state)
            self._cached_neural_action = action
        
    except Exception as e:
        # 에러 처리
        if iteration - self.last_error_log_frame >= 50:
            print(f"[WARNING] on_step 오류: {e}")
            self.last_error_log_frame = iteration
```

---

## 4. 실시간 업데이트

### 4.1 대시보드 서버 시작

```python
# monitoring/dashboard_api.py 또는 monitoring/dashboard.py
# FastAPI 서버 (권장)
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/game-state")
async def get_game_state():
    """게임 상태 조회"""
    base_dir = get_base_dir()
    status = _find_latest_instance_status(base_dir)  # stats/instance_*_status.json 읽기
    if status:
        return {
            "minerals": status.get("current_minerals", 0),
            "vespene": status.get("current_vespene", 0),
            "supply_used": status.get("supply_used", 0),
            "supply_cap": status.get("supply_cap", 0),
            "is_running": status.get("status") == "GAME_RUNNING",
            # ...
        }
    return game_state_cache  # 캐시 반환

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 4.2 클라이언트 Polling

```python
# Android 앱 (Kotlin)
lifecycleScope.launch {
    while (true) {
        try {
            val gameState = apiClient.getGameState()  // /api/game-state 호출
            updateUI(gameState)  // 화면 업데이트
        } catch (e: Exception) {
            showServerDisconnected(e.message)
        }
        delay(1000)  // 1초마다
    }
}
```

---

## 5. 게임 종료

### 5.1 게임 종료 처리 (on_end)

```python
# wicked_zerg_bot_pro.py
async def on_end(self, game_result: Result):
    """게임 종료 시 실행"""
    
    try:
        # 1. 게임 결과 기록
        self.last_result = str(game_result)
        loss_reason = self._analyze_loss_reason()
        loss_details = self._get_loss_details()
        
        # 2. Telemetry Logger에 결과 기록
        self.telemetry_logger.record_game_result(
            game_result,
            loss_reason,
            loss_details
        )
        
        # 3. Telemetry 데이터 저장
        await self.telemetry_logger.save_telemetry()
        
        # 4. Strategy Audit (패배 시)
        if game_result == Result.Defeat:
            gap_analysis = self.strategy_audit.analyze_bot_performance(
                bot_build_order=self._get_build_order(),
                pro_baseline=self.curriculum_manager.get_build_order_priorities()
            )
            
            if gap_analysis:
                feedback = self.strategy_audit.generate_gemini_feedback(gap_analysis)
                # GenAI Self-Healing에 피드백 전달
                await self.genai_self_healing.analyze_gap_feedback(feedback)
        
        # 5. Curriculum Manager 업데이트
        if game_result == Result.Victory:
            self.curriculum_manager.record_victory()
        else:
            self.curriculum_manager.record_defeat()
        
        # 6. Manus Dashboard에 게임 결과 전송
        if hasattr(self, 'manus_client'):
            await self.manus_client.send_game_result({
                "result": str(game_result),
                "duration": int(self.time),
                "final_minerals": self.minerals,
                "final_vespene": self.vespene,
                # ...
            })
        
        # 7. 통계 출력
        self.telemetry_logger.print_statistics()
        
    except Exception as e:
        print(f"[WARNING] on_end 오류: {e}")
```

---

## 실행 방법

### 방법 1: 간단한 로컬 게임

```bash
# run.py 실행
cd wicked_zerg_challenger
python run.py
```

**실행 흐름**:
1. SC2 경로 자동 탐지
2. WickedZergBotPro 인스턴스 생성
3. 로컬 게임 시작 (Terran VeryHard vs Zerg Bot)
4. 게임 실행 및 종료

### 방법 2: 통합 학습 실행

```bash
# main_integrated.py 실행
cd wicked_zerg_challenger/local_training
python main_integrated.py
```

**실행 흐름**:
1. 시스템 초기화 (SC2 경로, 로깅, PyTorch)
2. Curriculum Manager 로드
3. 봇 인스턴스 생성 및 초기화
4. 게임 루프 실행
5. 게임 종료 시 결과 기록 및 통계 업데이트

### 방법 3: 전체 학습 파이프라인

```bash
# start_full_training.bat 실행
cd wicked_zerg_challenger/bat
start_full_training.bat
```

**실행 흐름**:
1. 리플레이 추출 및 필터링
2. 리플레이 빌드오더 학습
3. 게임 학습 (Neural Network)
4. 정리 및 아카이브
5. 자동 커밋

### 방법 4: Manus 대시보드 통합

```bash
# start_with_manus.bat 실행
cd wicked_zerg_challenger/bat
start_with_manus.bat
```

**실행 흐름**:
1. 환경 변수 설정 (MANUS_DASHBOARD_URL, MANUS_DASHBOARD_ENABLED)
2. Manus 연결 테스트
3. 봇 실행 (게임 데이터 자동 전송)

### 방법 5: 대시보드 서버 실행

```bash
# FastAPI 서버 (권장)
cd wicked_zerg_challenger/monitoring
python dashboard_api.py

# 또는 Flask 서버
python dashboard.py
```

**실행 흐름**:
1. FastAPI/Flask 서버 시작 (포트 8000)
2. API 엔드포인트 등록
3. 클라이언트 요청 대기
4. 실시간 게임 상태 제공

---

## 전체 실행 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 시스템 초기화                                              │
│    - SC2 경로 설정                                            │
│    - Python 경로 설정                                         │
│    - 로깅 시스템 초기화                                        │
│    - PyTorch 설정                                             │
│    - 이벤트 루프 설정                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 봇 초기화                                                  │
│    - WickedZergBotPro 인스턴스 생성                          │
│    - Personality Manager 초기화                             │
│    - Neural Network 초기화                                   │
│    - Manager 변수 선언                                        │
│    - Telemetry Logger 초기화                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 게임 시작 (on_start)                                       │
│    - Intel Manager 초기화                                    │
│    - Economy Manager 초기화                                  │
│    - Production Manager 초기화                                │
│    - Combat Manager 초기화                                    │
│    - Scouting System 초기화                                  │
│    - Micro Controller 초기화                                  │
│    - Queen Manager 초기화                                     │
│    - Manus Dashboard 클라이언트 초기화                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. 게임 실행 (on_step - 매 프레임)                            │
│    - Intel Manager 업데이트 (매 프레임)                       │
│    - Micro Controller 업데이트 (매 프레임)                    │
│    - Combat Manager 업데이트 (4프레임마다)                     │
│    - Production & Economy 업데이트 (22프레임마다)              │
│    - Scouting 업데이트 (8프레임마다)                          │
│    - Queen Manager 업데이트 (16프레임마다)                     │
│    - Telemetry 로깅 (100프레임마다)                           │
│    - 상태 파일 업데이트 (16프레임마다)                         │
│    - Manus 동기화 (5초마다)                                   │
│    - Neural Network 추론 (24프레임마다)                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. 게임 종료 (on_end)                                         │
│    - 게임 결과 기록                                            │
│    - Telemetry 데이터 저장                                    │
│    - Strategy Audit (패배 시)                                 │
│    - Curriculum Manager 업데이트                              │
│    - Manus Dashboard 결과 전송                                │
│    - 통계 출력                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 주요 파일 위치

### 실행 파일
- `run.py` - 간단한 로컬 게임 실행
- `local_training/main_integrated.py` - 통합 학습 실행
- `monitoring/dashboard_api.py` - FastAPI 대시보드 서버
- `monitoring/dashboard.py` - Flask 대시보드 서버

### 배치 스크립트
- `bat/start_full_training.bat` - 전체 학습 파이프라인
- `bat/start_with_manus.bat` - Manus 대시보드 통합 실행
- `bat/start_game_training.bat` - 게임 학습만 실행
- `bat/start_replay_learning.bat` - 리플레이 학습만 실행

### 핵심 모듈
- `wicked_zerg_bot_pro.py` - 메인 봇 클래스
- `monitoring/telemetry_logger.py` - 데이터 수집
- `local_training/curriculum_manager.py` - 학습 난이도 관리
- `genai_self_healing.py` - AI 자가 수복
- `local_training/strategy_audit.py` - 빌드오더 분석

---

## 환경 변수

### 필수
- `SC2PATH` - StarCraft II 설치 경로

### 선택적
- `TORCH_NUM_THREADS` - PyTorch CPU 스레드 수 (기본: 12)
- `GPU_USAGE_TARGET` - GPU 사용률 목표 (기본: 0.3)
- `MANUS_DASHBOARD_URL` - Manus 대시보드 URL
- `MANUS_DASHBOARD_ENABLED` - Manus 대시보드 활성화 (0/1)
- `MANUS_SYNC_INTERVAL` - Manus 동기화 간격 (초)
- `INSTANCE_ID` - 인스턴스 ID (병렬 실행 시)
- `NUM_INSTANCES` - 인스턴스 수
- `DRY_RUN_MODE` - 드라이런 모드 (true/false)

---

## 문제 해결

### SC2 경로를 찾을 수 없는 경우
```bash
# 환경 변수 설정
set SC2PATH=C:\Program Files (x86)\StarCraft II
```

### 대시보드 서버가 시작되지 않는 경우
```bash
# 포트 확인
netstat -ano | findstr :8000

# 다른 포트 사용
python dashboard_api.py --port 8001
```

### Android 앱 연결 실패
- 에뮬레이터: `http://10.0.2.2:8000`
- 실제 기기: PC의 IP 주소로 변경 필요

---

**마지막 업데이트**: 2026-01-14
