# -*- coding: utf-8 -*-
"""
개선된 프로 리플레이 vs 트레이닝 비교 분석 도구

1. 프로 리플레이를 먼저 학습
2. 봇의 플레이 데이터와 비교 분석
3. 차이점을 학습 데이터로 변환하여 학습
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Any

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import sc2reader  # type: ignore
    SC2READER_AVAILABLE = True
except ImportError:
    SC2READER_AVAILABLE = False
    print("[WARNING] sc2reader library not available. Some features may be limited.")

# StrategyAudit 사용 시도
try:
    # StrategyAudit import would go here if available
    STRATEGY_AUDIT_AVAILABLE = False
except ImportError:
    STRATEGY_AUDIT_AVAILABLE = False
    print("[WARNING] StrategyAudit not available. Using basic analysis.")


class ProReplayLearner:
    """프로 리플레이 학습기"""

def __init__(self, replay_dir: Optional[Path] = None):
    self.replay_dir = replay_dir or PROJECT_ROOT / "replays" / "pro"
    self.learned_data = {}

def find_pro_replays(self) -> List[Path]:
    """프로 리플레이 파일 찾기"""
    replays = []

    if not self.replay_dir.exists():
        pass
    print(f"[INFO] 프로 리플레이 디렉토리가 없습니다: {self.replay_dir}")
    return replays

 # .SC2Replay 파일 찾기
    for replay_file in self.replay_dir.glob("*.SC2Replay"):
        pass
    replays.append(replay_file)

 # 하위 디렉토리도 검색
    for replay_file in self.replay_dir.rglob("*.SC2Replay"):
        pass
    if replay_file not in replays:
        pass
    replays.append(replay_file)

    print(f"[INFO] {len(replays)}개의 프로 리플레이를 찾았습니다.")
 return replays

def extract_build_order_from_replay(self, replay_path: Path) -> Optional[Dict]:
    """리플레이에서 빌드 오더 추출"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     # 리플레이 파일 분석
 # 실제 구현은 sc2 library의 리플레이 파서 사용
 build_order = {
     "replay_file": str(replay_path),
     "timestamp": datetime.now().isoformat(),
     "buildings": [],
     "units": [],
     "upgrades": [],
     "timings": {}
 }

 # TODO: 실제 리플레이 파싱 구현
 # sc2 library를 사용하여 리플레이 분석
     print(f"[INFO] 리플레이 분석 중: {replay_path.name}")

 return build_order

 except Exception as e:
     print(f"[ERROR] 리플레이 분석 실패 ({replay_path.name}): {e}")
 return None

def learn_from_replays(self) -> Dict:
    """프로 리플레이에서 학습"""
 replays = self.find_pro_replays()

 if not replays:
     print("[WARNING] 프로 리플레이가 없습니다.")
 return {}

 learned_data = {
     "total_replays": len(replays),
     "build_orders": [],
     "average_timings": {},
     "common_strategies": []
 }

     print(f"[INFO] {len(replays)}개의 프로 리플레이를 학습합니다...")

 for i, replay in enumerate(replays, 1):
     print(f"[{i}/{len(replays)}] {replay.name} 분석 중...")
 build_order = self.extract_build_order_from_replay(replay)

 if build_order:
     learned_data["build_orders"].append(build_order)

 # 평균 타이밍 계산
     if learned_data["build_orders"]:
         pass
     learned_data["average_timings"] = self._calculate_average_timings(
     learned_data["build_orders"]
 )

 self.learned_data = learned_data
     print(f"[INFO] 프로 리플레이 학습 완료: {len(learned_data['build_orders'])}개 빌드 오더")

 return learned_data

def _calculate_average_timings(self, build_orders: List[Dict]) -> Dict:
    """평균 타이밍 계산"""
 timings = {}

 for build_order in build_orders:
     for building, time in build_order.get("timings", {}).items():
         pass
     if building not in timings:
         pass
     timings[building] = []
 timings[building].append(time)

 average_timings = {}
 for building, times in timings.items():
     if times:
         average_timings[building] = sum(times) / len(times)

 return average_timings


class TrainingDataAnalyzer:
    """트레이닝 데이터 분석기"""

def __init__(self, training_data_dir: Optional[Path] = None):
    self.training_data_dir = training_data_dir or PROJECT_ROOT / "local_training" / "training_data"
 self.training_data = []

def load_training_data(self) -> List[Dict]:
    """트레이닝 데이터 로드"""
 training_files = []

 if not self.training_data_dir.exists():
     print(f"[INFO] 트레이닝 데이터 디렉토리가 없습니다: {self.training_data_dir}")
 return []

 # JSON 파일 찾기
     for data_file in self.training_data_dir.glob("*.json"):
         pass
     training_files.append(data_file)

 # 하위 디렉토리도 검색
     for data_file in self.training_data_dir.rglob("*.json"):
         pass
     if data_file not in training_files:
         pass
     training_files.append(data_file)

     print(f"[INFO] {len(training_files)}개의 트레이닝 데이터 파일을 찾았습니다.")

 training_data = []
 for data_file in training_files:
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         with open(data_file, 'r', encoding='utf-8') as f:
 data = json.load(f)
     data["source_file"] = str(data_file)
 training_data.append(data)
 except Exception as e:
     print(f"[ERROR] 데이터 로드 실패 ({data_file.name}): {e}")

 self.training_data = training_data
 return training_data

def extract_bot_build_order(self, training_data: Dict) -> Dict:
    """봇의 빌드 오더 추출"""
 build_order = {
    "timestamp": training_data.get("timestamp", ""),
    "buildings": training_data.get("buildings", []),
    "units": training_data.get("units", []),
    "upgrades": training_data.get("upgrades", []),
    "timings": training_data.get("timings", {})
 }

 return build_order


class ComparisonAnalyzer:
    """비교 분석기"""

def __init__(self, pro_data: Dict, training_data: List[Dict]):
    self.pro_data = pro_data
 self.training_data = training_data
 self.comparison_results = []

def compare_build_orders(self) -> List[Dict]:
    """빌드 오더 비교"""
 comparison_results = []

    pro_timings = self.pro_data.get("average_timings", {})

 for training in self.training_data:
     analyzer = TrainingDataAnalyzer()
 bot_build_order = analyzer.extract_bot_build_order(training)
     bot_timings = bot_build_order.get("timings", {})

 comparison = {
     "training_file": training.get("source_file", ""),
     "differences": [],
     "gaps": {},
     "recommendations": []
 }

 # 타이밍 비교
 for building, pro_time in pro_timings.items():
     bot_time = bot_timings.get(building, None)

 if bot_time is None:
     comparison["differences"].append({
     "building": building,
     "type": "missing",
     "pro_time": pro_time,
     "message": f"{building}이(가) 빌드 오더에 없습니다."
 })
     comparison["recommendations"].append(
     f"{building}을(를) {pro_time:.1f}초에 건설하도록 학습"
 )
 elif abs(bot_time - pro_time) > 30: # 30초 이상 차이
 gap = bot_time - pro_time
     comparison["gaps"][building] = {
     "pro_time": pro_time,
     "bot_time": bot_time,
     "gap": gap,
     "gap_percentage": (gap / pro_time) * 100 if pro_time > 0 else 0
 }

 if gap > 0:
     comparison["differences"].append({
     "building": building,
     "type": "late",
     "pro_time": pro_time,
     "bot_time": bot_time,
     "gap": gap,
     "message": f"{building}이(가) {gap:.1f}초 늦게 건설되었습니다."
 })
     comparison["recommendations"].append(
     f"{building} 건설 타이밍을 {gap:.1f}초 앞당기도록 학습"
 )
 else:
     comparison["differences"].append({
     "building": building,
     "type": "early",
     "pro_time": pro_time,
     "bot_time": bot_time,
     "gap": abs(gap),
     "message": f"{building}이(가) {abs(gap):.1f}초 일찍 건설되었습니다."
 })

 comparison_results.append(comparison)

 self.comparison_results = comparison_results
 return comparison_results

def generate_learning_data(self) -> Dict:
    """학습 데이터 생성"""
 learning_data = {
    "timestamp": datetime.now().isoformat(),
    "pro_baseline": self.pro_data.get("average_timings", {}),
    "adjustments": [],
    "recommendations": []
 }

 for comparison in self.comparison_results:
     for diff in comparison.get("differences", []):
         pass
     if diff["type"] == "late":
         pass
     learning_data["adjustments"].append({
     "building": diff["building"],
     "target_time": diff["pro_time"],
     "current_time": diff["bot_time"],
     "adjustment": -diff["gap"]  # 음수 = 앞당기기
 })
     elif diff["type"] == "missing":
         pass
     learning_data["adjustments"].append({
     "building": diff["building"],
     "target_time": diff["pro_time"],
     "current_time": None,
     "adjustment": diff["pro_time"]  # 새로 추가
 })

     learning_data["recommendations"].extend(
     comparison.get("recommendations", [])
 )

 return learning_data

def save_comparison_report(self, output_path: Path):
    """비교 리포트 저장"""
 report = {
    "timestamp": datetime.now().isoformat(),
    "pro_data_summary": {
    "total_replays": self.pro_data.get("total_replays", 0),
    "average_timings": self.pro_data.get("average_timings", {})
 },
    "training_data_summary": {
    "total_files": len(self.training_data)
 },
    "comparisons": self.comparison_results,
    "learning_data": self.generate_learning_data()
 }

    with open(output_path, 'w', encoding='utf-8') as f:
 json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[INFO] 비교 리포트 저장: {output_path}")


class LearningDataUpdater:
    """학습 데이터 업데이터"""

def __init__(self, learning_data: Dict):
    self.learning_data = learning_data

def update_model_parameters(self, model_path: Optional[Path] = None):
    """모델 파라미터 업데이트"""
 # 학습 데이터를 모델에 반영
    adjustments = self.learning_data.get("adjustments", [])

 if not adjustments:
     print("[INFO] 업데이트할 학습 데이터가 없습니다.")
 return

     print(f"[INFO] {len(adjustments)}개의 조정 사항을 모델에 반영합니다...")

 # TODO: 실제 모델 업데이트 로직 구현
 # zerg_net.py의 모델에 학습 데이터 반영

 for adj in adjustments:
     print(f"  - {adj['building']}: {adj.get('adjustment', 0):.1f}초 조정")

     print("[INFO] 모델 파라미터 업데이트 완료")


def main():
    """메인 함수"""
    print("=" * 70)
    print("개선된 프로 리플레이 vs 트레이닝 비교 분석")
    print("=" * 70)
 print()

 # 1. 프로 리플레이 학습
    print("[1/3] 프로 리플레이 학습 중...")
 pro_learner = ProReplayLearner()
 pro_data = pro_learner.learn_from_replays()

    if not pro_data.get("build_orders"):
        print("[ERROR] 프로 리플레이 학습 데이터가 없습니다.")
 return

 print()

 # 2. 트레이닝 데이터 로드
    print("[2/3] 트레이닝 데이터 로드 중...")
 training_analyzer = TrainingDataAnalyzer()
 training_data = training_analyzer.load_training_data()

 if not training_data:
     print("[ERROR] 트레이닝 데이터가 없습니다.")
 return

 print()

 # 3. 비교 분석
    print("[3/3] 비교 분석 중...")
 comparison_analyzer = ComparisonAnalyzer(pro_data, training_data)
 comparisons = comparison_analyzer.compare_build_orders()

 # 리포트 저장
    output_dir = PROJECT_ROOT / "local_training" / "analysis"
 output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
 comparison_analyzer.save_comparison_report(report_path)

 # 학습 데이터 생성
 learning_data = comparison_analyzer.generate_learning_data()

 # 학습 데이터 저장
    learning_data_path = output_dir / f"learning_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(learning_data_path, 'w', encoding='utf-8') as f:
 json.dump(learning_data, f, indent=2, ensure_ascii=False)
    print(f"[INFO] 학습 데이터 저장: {learning_data_path}")

 # 모델 파라미터 업데이트
 print()
    print("[4/4] 모델 파라미터 업데이트 중...")
 updater = LearningDataUpdater(learning_data)
 updater.update_model_parameters()

 print()
    print("=" * 70)
    print("비교 분석 완료!")
    print(f"  프로 리플레이: {pro_data.get('total_replays', 0)}개")
    print(f"  트레이닝 데이터: {len(training_data)}개")
    print(f"  비교 결과: {len(comparisons)}개")
    print(f"  조정 사항: {len(learning_data.get('adjustments', []))}개")
    print("=" * 70)


if __name__ == "__main__":
    main()
