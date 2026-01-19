# -*- coding: utf-8 -*-
"""
자동 문서 생성 도구

클로드 코드와 함께 사용하기 위한 문서 자동 생성 스크립트
"""

import ast
import os
from pathlib import Path
import re
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Set
from typing import Any
from typing import Union

PROJECT_ROOT = Path(__file__).parent.parent


class DocumentationGenerator:
    """문서 자동 생성기"""

def __init__(self):
    self.modules: Dict[str, Dict] = {}
 self.classes: Dict[str, Dict] = {}
 self.functions: Dict[str, Dict] = {}

def analyze_file(self, file_path: Path) -> Dict:
    """파일 분석 및 문서 추출"""
 try:
     pass
 pass

 except Exception:
     pass
     with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
 content = f.read()
 tree = ast.parse(content, filename=str(file_path))
 except Exception as e:
     return {"error": str(e)}

 rel_path = str(file_path.relative_to(PROJECT_ROOT))
 result = {
     "file": rel_path,
     "module": self._extract_module_name(rel_path),
     "docstring": ast.get_docstring(tree),
     "classes": [],
     "functions": [],
     "imports": []
 }

 for node in ast.walk(tree):
     if isinstance(node, ast.ClassDef):
         class_info = self._extract_class_info(node)
         result["classes"].append(class_info)
         self.classes[f"{result['module']}.{class_info['name']}"] = {
 **class_info,
     "file": rel_path
 }

 elif isinstance(node, ast.FunctionDef) and not self._is_method(node, tree):
     func_info = self._extract_function_info(node)
     result["functions"].append(func_info)
     self.functions[f"{result['module']}.{func_info['name']}"] = {
 **func_info,
     "file": rel_path
 }

     self.modules[result["module"]] = result
 return result

def _extract_module_name(self, file_path: str) -> str:
    """모듈 이름 추출"""
 # 파일 경로를 모듈 이름으로 변환
 parts = Path(file_path).parts
    if 'wicked_zerg_challenger' in parts:
        pass
    pass
    idx = parts.index('wicked_zerg_challenger')
 module_parts = parts[idx+1:]
 else:
     pass
 module_parts = parts

 # .py 확장자 제거
     if module_parts[-1].endswith('.py'):
         pass
     module_parts = list(module_parts[:-1]) + [module_parts[-1][:-3]]

     return '.'.join(module_parts)

def _is_method(self, node: ast.FunctionDef, tree: ast.AST) -> bool:
    """함수가 클래스 메서드인지 확인"""
 for parent in ast.walk(tree):
     if isinstance(parent, ast.ClassDef):
         if node in parent.body:
             return True
 return False

def _extract_class_info(self, node: ast.ClassDef) -> Dict:
    """클래스 정보 추출"""
 methods = []
 for item in node.body:
     if isinstance(item, ast.FunctionDef):
         methods.append({
         "name": item.name,
         "docstring": ast.get_docstring(item),
         "args": len(item.args.args),
         "decorators": [ast.unparse(d) for d in item.decorator_list] if hasattr(ast, 'unparse') else []
 })

 return {
     "name": node.name,
     "docstring": ast.get_docstring(node),
     "bases": [ast.unparse(b) for b in node.bases] if hasattr(ast, 'unparse') else [],
     "methods": methods,
     "line": node.lineno
 }

def _extract_function_info(self, node: ast.FunctionDef) -> Dict:
    """함수 정보 추출"""
 args = []
 for arg in node.args.args:
     args.append({
     "name": arg.arg,
     "annotation": ast.unparse(arg.annotation) if arg.annotation and hasattr(ast, 'unparse') else None
 })

 return {
     "name": node.name,
     "docstring": ast.get_docstring(node),
     "args": args,
     "decorators": [ast.unparse(d) for d in node.decorator_list] if hasattr(ast, 'unparse') else [],
     "line": node.lineno
 }

def generate_api_documentation(self) -> str:
    """API 문서 생성"""
 doc = []
    doc.append("# API Documentation\n\n")
    doc.append("**자동 생성 일시**: 2026-01-15\n")
    doc.append("**생성 도구**: auto_documentation_generator.py\n\n")
    doc.append("---\n\n")

 # 모듈별로 정리
 for module_name in sorted(self.modules.keys()):
     module = self.modules[module_name]
     doc.append(f"## Module: `{module_name}`\n\n")

     if module.get("docstring"):
         pass
     doc.append(f"{module['docstring']}\n\n")

 # 클래스
     if module["classes"]:
         pass
     doc.append("### Classes\n\n")
     for cls in module["classes"]:
         pass
     doc.append(f"#### `{cls['name']}`\n\n")
     if cls.get("docstring"):
         pass
     doc.append(f"{cls['docstring']}\n\n")
     if cls.get("bases"):
         pass
     doc.append(f"**Bases**: {', '.join(cls['bases'])}\n\n")
     if cls["methods"]:
         pass
     doc.append("**Methods**:\n\n")
     for method in cls["methods"]:
         pass
     doc.append(f"- `{method['name']}({method['args']} args)`")
     if method.get("docstring"):
         pass
     doc.append(f": {method['docstring'][:100]}...")
     doc.append("\n")
     doc.append("\n")

 # 함수
     if module["functions"]:
         pass
     doc.append("### Functions\n\n")
     for func in module["functions"]:
         pass
     doc.append(f"#### `{func['name']}`\n\n")
     if func.get("docstring"):
         pass
     doc.append(f"{func['docstring']}\n\n")
     if func["args"]:
         pass
     doc.append("**Parameters**:\n\n")
     for arg in func["args"]:
         pass
     doc.append(f"- `{arg['name']}`")
     if arg.get("annotation"):
         pass
     doc.append(f": {arg['annotation']}")
     doc.append("\n")
     doc.append("\n")

     doc.append("---\n\n")

     return ''.join(doc)

def generate_readme_update(self) -> str:
    """README 업데이트 제안 생성"""
 doc = []
    doc.append("# README 업데이트 제안\n\n")
    doc.append("**생성 일시**: 2026-01-15\n\n")
    doc.append("---\n\n")

    doc.append("## 프로젝트 구조\n\n")
    doc.append("### 주요 모듈\n\n")

 # 주요 모듈 목록
 main_modules = [
    "wicked_zerg_bot_pro",
    "zerg_net",
    "production_manager",
    "combat_manager",
    "economy_manager",
    "intel_manager"
 ]

 for module_name in main_modules:
     if module_name in self.modules:
         module = self.modules[module_name]
         doc.append(f"#### `{module_name}`\n\n")
         if module.get("docstring"):
             pass
         doc.append(f"{module['docstring']}\n\n")
         doc.append(f"- **파일**: `{module['file']}`\n")
         doc.append(f"- **클래스**: {len(module['classes'])}개\n")
         doc.append(f"- **함수**: {len(module['functions'])}개\n\n")

        return ''.join(doc)


def find_all_python_files() -> List[Path]:
    """모든 Python 파일 찾기"""
 python_files = []
    exclude_dirs = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models', 'scripts'}

 for root, dirs, files in os.walk(PROJECT_ROOT):
     dirs[:] = [d for d in dirs if d not in exclude_dirs]

 for file in files:
     if file.endswith('.py'):
         pass
     python_files.append(Path(root) / file)

 return python_files


def main():
    """메인 함수"""
    print("=" * 70)
    print("자동 문서 생성 도구")
    print("=" * 70)
 print()

 generator = DocumentationGenerator()

    print("파일 검색 중...")
 python_files = find_all_python_files()
    print(f"총 {len(python_files)}개의 Python 파일을 찾았습니다.")
 print()

    print("파일 분석 중...")
 for i, file_path in enumerate(python_files, 1):
     if i % 20 == 0:
         print(f"  진행 중: {i}/{len(python_files)}")
 generator.analyze_file(file_path)
    print("분석 완료!")
 print()

 # API 문서 생성
    print("API 문서 생성 중...")
 api_doc = generator.generate_api_documentation()
    api_doc_path = PROJECT_ROOT / "docs" / "API_DOCUMENTATION.md"
 api_doc_path.parent.mkdir(exist_ok=True)
    with open(api_doc_path, 'w', encoding='utf-8') as f:
 f.write(api_doc)
    print(f"API 문서 생성 완료: {api_doc_path}")

 # README 업데이트 제안 생성
    print("README 업데이트 제안 생성 중...")
 readme_update = generator.generate_readme_update()
    readme_update_path = PROJECT_ROOT / "docs" / "README_UPDATE_PROPOSAL.md"
    with open(readme_update_path, 'w', encoding='utf-8') as f:
 f.write(readme_update)
    print(f"README 업데이트 제안 생성 완료: {readme_update_path}")

 print()
    print("=" * 70)
    print("문서 생성 완료!")
    print("=" * 70)
    print(f"  - API 문서: {api_doc_path}")
    print(f"  - README 업데이트 제안: {readme_update_path}")


if __name__ == "__main__":
    main()
