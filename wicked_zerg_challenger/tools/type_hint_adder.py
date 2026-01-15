# -*- coding: utf-8 -*-
"""
타입 힌트 추가 도구

Python 파일에 타입 힌트를 자동으로 추가
"""

import ast
import time

PROJECT_ROOT = Path(__file__).parent.parent


class TypeHintAdder:
    """타입 힌트 추가기"""
 
 def __init__(self):
 self.files_modified: List[str] = []
 
 def analyze_file(self, file_path: Path) -> Dict:
        """파일 분석 및 타입 힌트 필요 여부 확인"""
 analysis = {
            "file": str(file_path.relative_to(PROJECT_ROOT)),
            "functions_without_hints": [],
            "total_functions": 0
 }
 
 try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 
 for node in ast.walk(tree):
 if isinstance(node, ast.FunctionDef):
                    analysis["total_functions"] += 1
 
 # 타입 힌트가 없는 함수 찾기
 has_return_annotation = node.returns is not None
 has_arg_annotations = all(arg.annotation is not None for arg in node.args.args)
 
 if not has_return_annotation or not has_arg_annotations:
                        analysis["functions_without_hints"].append({
                            "name": node.name,
                            "line": node.lineno,
                            "missing_return": not has_return_annotation,
                            "missing_args": not has_arg_annotations
 })
 
 except Exception as e:
            analysis["error"] = str(e)
 
 return analysis
 
 def generate_type_hint_report(self, all_analyses: List[Dict]) -> str:
        """타입 힌트 리포트 생성"""
 report = []
        report.append("# 타입 힌트 추가 리포트\n\n")
        report.append(f"**생성 일시**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        report.append("---\n\n")
 
        total_functions = sum(a.get("total_functions", 0) for a in all_analyses)
        functions_without_hints = sum(len(a.get("functions_without_hints", [])) for a in all_analyses)
 
 if total_functions == 0:
            report.append("## 요약\n\n")
            report.append("- **총 함수 수**: 0개\n")
            report.append("- **타입 힌트 없는 함수**: 0개\n\n")
 else:
            report.append("## 요약\n\n")
            report.append(f"- **총 함수 수**: {total_functions}개\n")
            report.append(f"- **타입 힌트 없는 함수**: {functions_without_hints}개\n")
            report.append(f"- **타입 힌트 비율**: {(total_functions - functions_without_hints) / total_functions * 100:.1f}%\n\n")
 
        report.append("## 타입 힌트가 필요한 함수\n\n")
 
 # 상위 20개 파일만 표시
 files_with_most_missing = sorted(
            [a for a in all_analyses if a.get("functions_without_hints")],
            key=lambda x: len(x.get("functions_without_hints", [])),
 reverse=True
 )[:20]
 
 for file_analysis in files_with_most_missing:
            if file_analysis.get("functions_without_hints"):
                report.append(f"### `{file_analysis['file']}`\n\n")
                report.append(f"타입 힌트 없는 함수: {len(file_analysis['functions_without_hints'])}개\n\n")
                for func_info in file_analysis["functions_without_hints"][:10]:  # 상위 10개만
                    report.append(f"- `{func_info['name']}` (라인 {func_info['line']})\n")
                report.append("\n")
 
        report.append("---\n\n")
        report.append("## 클로드 코드 활용 제안\n\n")
        report.append("다음 작업을 클로드 코드에게 요청하세요:\n\n")
        report.append("```\n")
        report.append("타입 힌트 추가 리포트를 읽고, 타입 힌트가 없는 함수들에\n")
        report.append("적절한 타입 힌트를 추가해줘.\n\n")
        report.append("작업 순서:\n")
        report.append("1. 각 함수의 매개변수 타입 추론\n")
        report.append("2. 반환 타입 추론\n")
        report.append("3. typing 모듈 import 추가 (필요시)\n")
        report.append("4. 타입 힌트 추가\n")
        report.append("5. 변경 사항 검증\n")
        report.append("```\n\n")
 
        return ''.join(report)


def main():
    """메인 함수"""
    print("=" * 70)
    print("타입 힌트 분석")
    print("=" * 70)
 print()
 
 adder = TypeHintAdder()
 
 # 주요 파일 분석
 main_files = [
        "wicked_zerg_bot_pro.py",
        "production_manager.py",
        "combat_manager.py",
        "economy_manager.py",
        "zerg_net.py"
 ]
 
 all_analyses = []
 for main_file in main_files:
 file_path = PROJECT_ROOT / main_file
 if file_path.exists():
 analysis = adder.analyze_file(file_path)
 all_analyses.append(analysis)
            if analysis.get("functions_without_hints"):
                print(f"  - {main_file}: {len(analysis['functions_without_hints'])}개 함수에 타입 힌트 없음")
 
 print()
    print("타입 힌트 리포트 생성 중...")
 report = adder.generate_type_hint_report(all_analyses)
 
    report_path = PROJECT_ROOT / "TYPE_HINT_ANALYSIS_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
 f.write(report)
 
    print(f"리포트가 생성되었습니다: {report_path}")
 print()
    print("=" * 70)
    print("완료!")
    print("=" * 70)


if __name__ == "__main__":
 main()