# -*- coding: utf-8 -*-
"""
기능 추가 도구

새로운 빌드 오더, 적 종족별 대응 전략, 맵별 최적화 분석 및 제안
"""

import json
import time

PROJECT_ROOT = Path(__file__).parent.parent


class FeatureEnhancer:
    """기능 강화기"""
 
 def __init__(self):
 self.build_orders: List[Dict] = []
 self.race_strategies: Dict[str, List[Dict]] = {
            "Terran": [],
            "Protoss": [],
            "Zerg": []
 }
 self.map_strategies: Dict[str, List[Dict]] = {}
 
 def analyze_build_orders(self) -> List[Dict]:
        """빌드 오더 분석"""
 build_orders = []
 
 # 빌드 오더 파일 찾기
 build_order_files = [
            PROJECT_ROOT / "local_training" / "scripts" / "learned_build_orders.json",
            PROJECT_ROOT / "data" / "build_orders.json"
 ]
 
 for file_path in build_order_files:
 if file_path.exists():
 try:
                    with open(file_path, 'r', encoding='utf-8') as f:
 data = json.load(f)
 if isinstance(data, list):
 build_orders.extend(data)
 elif isinstance(data, dict):
 build_orders.append(data)
 except Exception:
 continue
 
 return build_orders
 
 def analyze_race_strategies(self) -> Dict[str, List[Dict]]:
        """적 종족별 대응 전략 분석"""
 strategies = {
            "Terran": [],
            "Protoss": [],
            "Zerg": []
 }
 
 # 전략 파일 찾기
 strategy_files = [
            PROJECT_ROOT / "data" / "race_strategies.json",
            PROJECT_ROOT / "local_training" / "scripts" / "strategy_database.py"
 ]
 
 for file_path in strategy_files:
 if file_path.exists():
                if file_path.suffix == '.json':
 try:
                        with open(file_path, 'r', encoding='utf-8') as f:
 data = json.load(f)
 for race, race_strategies in data.items():
 if race in strategies:
 strategies[race].extend(race_strategies)
 except Exception:
 continue
 
 return strategies
 
 def analyze_map_strategies(self) -> Dict[str, List[Dict]]:
        """맵별 최적화 전략 분석"""
 map_strategies = {}
 
 # 맵 전략 파일 찾기
 map_strategy_files = [
            PROJECT_ROOT / "data" / "map_strategies.json"
 ]
 
 for file_path in map_strategy_files:
 if file_path.exists():
 try:
                    with open(file_path, 'r', encoding='utf-8') as f:
 data = json.load(f)
 map_strategies.update(data)
 except Exception:
 continue
 
 return map_strategies
 
 def generate_feature_suggestions(self) -> str:
        """기능 추가 제안 생성"""
 suggestions = []
        suggestions.append("# 기능 추가 제안\n\n")
        suggestions.append(f"**생성 일시**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        suggestions.append("---\n\n")
 
 # 빌드 오더 분석
 build_orders = self.analyze_build_orders()
        suggestions.append("## 1. 새로운 빌드 오더 추가\n\n")
        suggestions.append(f"현재 빌드 오더: {len(build_orders)}개\n\n")
        suggestions.append("### 제안 빌드 오더\n\n")
        suggestions.append("1. **초반 러시 빌드**\n")
        suggestions.append("   - 6드론 풀링\n")
        suggestions.append("   - 저글링 러시\n")
        suggestions.append("   - 적 본진 조기 공격\n\n")
        suggestions.append("2. **중반 확장 빌드**\n")
        suggestions.append("   - 빠른 3멀티\n")
        suggestions.append("   - 가스 집중\n")
        suggestions.append("   - 고급 유닛 생산\n\n")
        suggestions.append("3. **후반 테크 빌드**\n")
        suggestions.append("   - 울트라리스크 빌드\n")
        suggestions.append("   - 브루들링 빌드\n")
        suggestions.append("   - 가디언 빌드\n\n")
 
 # 적 종족별 대응 전략
 race_strategies = self.analyze_race_strategies()
        suggestions.append("## 2. 적 종족별 대응 전략\n\n")
 
 for race, strategies in race_strategies.items():
            suggestions.append(f"### vs {race}\n\n")
 if strategies:
                suggestions.append(f"현재 전략: {len(strategies)}개\n\n")
 else:
                suggestions.append("**제안 전략**:\n\n")
                if race == "Terran":
                    suggestions.append("1. **메카닉 대응**\n")
                    suggestions.append("   - 히드라리스크 + 뮤탈리스크\n")
                    suggestions.append("   - 땅거미 지뢰 대응\n\n")
                elif race == "Protoss":
                    suggestions.append("1. **프로토스 대응**\n")
                    suggestions.append("   - 저글링 + 히드라리스크\n")
                    suggestions.append("   - 다크 템플러 대응\n\n")
                elif race == "Zerg":
                    suggestions.append("1. **저그전 대응**\n")
                    suggestions.append("   - 빠른 뮤탈리스크\n")
                    suggestions.append("   - 저글링 러시 대응\n\n")
            suggestions.append("\n")
 
 # 맵별 최적화
 map_strategies = self.analyze_map_strategies()
        suggestions.append("## 3. 맵별 최적화\n\n")
        suggestions.append("### 제안 맵별 전략\n\n")
        suggestions.append("1. **작은 맵 (SMALL)**\n")
        suggestions.append("   - 러시 중심 전략\n")
        suggestions.append("   - 빠른 병력 생산\n")
        suggestions.append("   - 조기 공격\n\n")
        suggestions.append("2. **중간 맵 (MEDIUM)**\n")
        suggestions.append("   - 균형잡힌 전략\n")
        suggestions.append("   - 확장과 병력 병행\n\n")
        suggestions.append("3. **큰 맵 (LARGE)**\n")
        suggestions.append("   - 확장 중심 전략\n")
        suggestions.append("   - 경제 우선\n")
        suggestions.append("   - 후반 테크\n\n")
 
        return ''.join(suggestions)


def main():
    """메인 함수"""
    print("=" * 70)
    print("기능 추가 분석")
    print("=" * 70)
 print()
 
 enhancer = FeatureEnhancer()
 
    print("빌드 오더 분석 중...")
 build_orders = enhancer.analyze_build_orders()
    print(f"  - 현재 빌드 오더: {len(build_orders)}개")
 print()
 
    print("적 종족별 전략 분석 중...")
 race_strategies = enhancer.analyze_race_strategies()
 for race, strategies in race_strategies.items():
        print(f"  - vs {race}: {len(strategies)}개 전략")
 print()
 
    print("맵별 전략 분석 중...")
 map_strategies = enhancer.analyze_map_strategies()
    print(f"  - 맵별 전략: {len(map_strategies)}개")
 print()
 
    print("기능 추가 제안 생성 중...")
 suggestions = enhancer.generate_feature_suggestions()
 
    report_path = PROJECT_ROOT / "FEATURE_ENHANCEMENT_SUGGESTIONS.md"
    with open(report_path, 'w', encoding='utf-8') as f:
 f.write(suggestions)
 
    print(f"리포트가 생성되었습니다: {report_path}")
 print()
    print("=" * 70)
    print("완료!")
    print("=" * 70)


if __name__ == "__main__":
 main()