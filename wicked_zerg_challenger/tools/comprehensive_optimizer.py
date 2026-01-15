# -*- coding: utf-8 -*-
"""
종합 최적화 도구

게임 성능 개선, 학습 속도 향상, 코드 스타일 통일을 한 번에 수행
"""

import subprocess
import sys

PROJECT_ROOT = Path(__file__).parent.parent


def main():
    """메인 함수"""
    print("=" * 70)
    print("종합 최적화 시스템")
    print("=" * 70)
 print()
    print("이 도구는 다음을 수행합니다:")
    print("  1. 게임 성능 개선")
    print("  2. 학습 속도 향상")
    print("  3. 코드 스타일 통일 (PEP 8)")
 print()
 
 results = {
        "performance": False,
        "learning": False,
        "style": False,
        "errors": []
 }
 
 # 1. 게임 성능 최적화
    print("[1/3] 게임 성능 최적화 중...")
 try:
 result = subprocess.run(
            [sys.executable, "tools/game_performance_optimizer.py"],
 cwd=PROJECT_ROOT,
 capture_output=True,
 text=True,
 timeout=300
 )
 if result.returncode == 0:
            print("  완료")
            results["performance"] = True
 else:
            print(f"  오류: {result.stderr[:200]}")
            results["errors"].append(f"Performance: {result.stderr[:200]}")
 except Exception as e:
        print(f"  실패: {e}")
        results["errors"].append(f"Performance: {e}")
 print()
 
 # 2. 학습 속도 향상
    print("[2/3] 학습 속도 향상 중...")
 try:
 result = subprocess.run(
            [sys.executable, "tools/learning_speed_enhancer.py"],
 cwd=PROJECT_ROOT,
 capture_output=True,
 text=True,
 timeout=300
 )
 if result.returncode == 0:
            print("  완료")
            results["learning"] = True
 else:
            print(f"  오류: {result.stderr[:200]}")
            results["errors"].append(f"Learning: {result.stderr[:200]}")
 except Exception as e:
        print(f"  실패: {e}")
        results["errors"].append(f"Learning: {e}")
 print()
 
 # 3. 코드 스타일 통일
    print("[3/3] 코드 스타일 통일 중...")
 try:
 result = subprocess.run(
            [sys.executable, "tools/code_style_unifier.py"],
 cwd=PROJECT_ROOT,
 capture_output=True,
 text=True,
 timeout=300
 )
 if result.returncode == 0:
            print("  완료")
            results["style"] = True
 else:
            print(f"  오류: {result.stderr[:200]}")
            results["errors"].append(f"Style: {result.stderr[:200]}")
 except Exception as e:
        print(f"  실패: {e}")
        results["errors"].append(f"Style: {e}")
 print()
 
 # 결과 요약
    print("=" * 70)
    print("최적화 결과 요약")
    print("=" * 70)
    print(f"  게임 성능: {'완료' if results['performance'] else '실패'}")
    print(f"  학습 속도: {'완료' if results['learning'] else '실패'}")
    print(f"  코드 스타일: {'완료' if results['style'] else '실패'}")
 
    if results["errors"]:
 print()
        print("오류:")
        for error in results["errors"]:
            print(f"  - {error}")
 
 print()
    print("=" * 70)
    print("완료!")
    print("=" * 70)


if __name__ == "__main__":
 main()