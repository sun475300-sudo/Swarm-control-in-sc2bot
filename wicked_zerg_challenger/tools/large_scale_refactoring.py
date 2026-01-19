# -*- coding: utf-8 -*-
"""
대규모 리팩토링 계획 및 실행 도구

1. 파일 구조 재구성 계획
2. 클래스 분리 및 통합 계획
3. 의존성 최적화 계획
"""

import ast
import os
from pathlib import Path
from typing import Dict
from typing import List
from typing import Set
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent


class LargeScaleRefactoringPlanner:
    """대규모 리팩토링 계획자"""

def __init__(self):
    self.class_info: Dict[str, Dict] = {}
 self.dependencies: Dict[str, Set[str]] = defaultdict(set)
 self.file_structure: Dict[str, List[str]] = defaultdict(list)

def analyze_classes(self) -> Dict[str, Dict]:
    """클래스 분석"""
 classes = {}

 for root, dirs, files in os.walk(PROJECT_ROOT):
     dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]

 for file in files:
     if file.endswith('.py'):
         pass
     file_path = Path(root) / file
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
     with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))

 for node in ast.walk(tree):
     if isinstance(node, ast.ClassDef):
         methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
         class_key = f"{file_path.relative_to(PROJECT_ROOT)}.{node.name}"
 classes[class_key] = {
     "file": str(file_path.relative_to(PROJECT_ROOT)),
     "name": node.name,
     "methods": len(methods),
     "line": node.lineno,
     "bases": [ast.unparse(b) for b in node.bases] if hasattr(ast, 'unparse') else []
 }
 except Exception:
     continue

 return classes

def analyze_dependencies(self) -> Dict[str, Set[str]]:
    """의존성 분석"""
 dependencies = defaultdict(set)

 for root, dirs, files in os.walk(PROJECT_ROOT):
     dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', '.venv', 'venv'}]

 for file in files:
     if file.endswith('.py'):
         pass
     file_path = Path(root) / file
 rel_path = str(file_path.relative_to(PROJECT_ROOT))

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
     with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))

 for node in ast.walk(tree):
     if isinstance(node, ast.ImportFrom):
         if node.module and not node.module.startswith('.'):
         # 로컬 모듈인지 확인
         if node.module.startswith('wicked_zerg_challenger') or \
         any(Path(PROJECT_ROOT / node.module.replace('.', '/')).exists() for _ in [1]):
         dependencies[rel_path].add(node.module)
 except Exception:
     continue

 return dict(dependencies)

def generate_refactoring_plan(self) -> str:
    """리팩토링 계획 생성"""
 plan = []
    plan.append("# 대규모 리팩토링 계획\n\n")
    plan.append("**생성 일시**: 2026-01-15\n")
    plan.append("**목적**: 파일 구조 재구성, 클래스 분리/통합, 의존성 최적화\n\n")
    plan.append("---\n\n")

 # 클래스 분석
 classes = self.analyze_classes()
    plan.append("## 1. 클래스 분석\n\n")
    plan.append(f"총 {len(classes)}개의 클래스를 발견했습니다.\n\n")

 # 큰 클래스 찾기
    large_classes = {k: v for k, v in classes.items() if v['methods'] > 20}
 if large_classes:
         plan.append("### 큰 클래스 (메서드 20개 이상) - 분리 권장\n\n")
     for class_key, info in sorted(large_classes.items(), key=lambda x: x[1]['methods'], reverse=True)[:10]:
             pass
     plan.append(f"- `{info['file']}:{info['line']}` - `{info['name']}` ({info['methods']}개 메서드)\n")
     plan.append("\n")

 # 의존성 분석
 dependencies = self.analyze_dependencies()
     plan.append("## 2. 의존성 분석\n\n")
     plan.append(f"총 {len(dependencies)}개 파일의 의존성을 분석했습니다.\n\n")

 # 순환 의존성 찾기
     plan.append("### 순환 의존성 검사\n\n")
     plan.append("순환 의존성을 찾아 최적화가 필요합니다.\n\n")

 # 파일 구조 제안
     plan.append("## 3. 파일 구조 재구성 제안\n\n")
     plan.append("### 현재 구조\n\n")
     plan.append("```\n")
     plan.append("wicked_zerg_challenger/\n")
     plan.append("├── bat/\n")
     plan.append("├── tools/\n")
     plan.append("├── monitoring/\n")
     plan.append("├── local_training/\n")
     plan.append("└── 설명서/\n")
     plan.append("```\n\n")

     plan.append("### 제안 구조\n\n")
     plan.append("```\n")
     plan.append("wicked_zerg_challenger/\n")
     plan.append("├── core/              # 핵심 봇 로직\n")
     plan.append("│   ├── bot.py\n")
     plan.append("│   ├── managers/      # 매니저 클래스들\n")
     plan.append("│   └── utils/         # 공통 유틸리티\n")
     plan.append("├── training/          # 훈련 관련\n")
     plan.append("├── tools/             # 유틸리티 도구\n")
     plan.append("├── monitoring/        # 모니터링\n")
     plan.append("└── docs/             # 문서\n")
     plan.append("```\n\n")

 # 클래스 분리 제안
     plan.append("## 4. 클래스 분리 및 통합 제안\n\n")
 if large_classes:
         plan.append("### 분리 권장 클래스\n\n")
 for class_key, info in list(large_classes.items())[:5]:
         plan.append(f"#### `{info['name']}` ({info['file']})\n\n")
     plan.append(f"- **메서드 수**: {info['methods']}개\n")
     plan.append(f"- **제안**: 기능별로 여러 클래스로 분리\n")
     plan.append(f"  - 예: `{info['name']}Core`, `{info['name']}Manager`, `{info['name']}Utils`\n\n")

 # 의존성 최적화 제안
     plan.append("## 5. 의존성 최적화 제안\n\n")
     plan.append("### 최적화 방안\n\n")
     plan.append("1. **공통 유틸리티 모듈 생성**\n")
     plan.append("   - `core/utils/common.py`에 공통 함수 통합\n")
     plan.append("   - 중복 import 제거\n\n")
     plan.append("2. **인터페이스 추상화**\n")
     plan.append("   - 공통 인터페이스 정의\n")
     plan.append("   - 의존성 역전 원칙 적용\n\n")
     plan.append("3. **모듈 재구성**\n")
     plan.append("   - 관련 기능을 같은 모듈로 그룹화\n")
     plan.append("   - 순환 의존성 제거\n\n")

     return ''.join(plan)


def main():
    """메인 함수"""
    print("=" * 70)
    print("대규모 리팩토링 계획 생성")
    print("=" * 70)
 print()

 planner = LargeScaleRefactoringPlanner()

    print("클래스 분석 중...")
 classes = planner.analyze_classes()
    print(f"  - 총 {len(classes)}개 클래스 발견")

    large_classes = {k: v for k, v in classes.items() if v['methods'] > 20}
 if large_classes:
         print(f"  - 큰 클래스: {len(large_classes)}개 (메서드 20개 이상)")
 print()

    print("의존성 분석 중...")
 dependencies = planner.analyze_dependencies()
    print(f"  - 총 {len(dependencies)}개 파일 분석")
 print()

    print("리팩토링 계획 생성 중...")
 plan = planner.generate_refactoring_plan()

    plan_path = PROJECT_ROOT / "LARGE_SCALE_REFACTORING_PLAN.md"
    with open(plan_path, 'w', encoding='utf-8') as f:
 f.write(plan)

    print(f"리팩토링 계획이 생성되었습니다: {plan_path}")
 print()
    print("=" * 70)
    print("완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
