# -*- coding: utf-8 -*-
"""Regression guard: prevent re-introducing shadowed/duplicated method definitions.

이 테스트는 정적 분석으로 같은 클래스 내부에 동일 이름의 메서드가 두 번 이상
정의되는 회귀를 차단한다. 과거 다음 위치에서 셰도잉으로 인해 의도한 로직이
런타임에 절대 실행되지 않는 결함이 발견된 적이 있어, 같은 회귀를 막기 위한
최후 방어선이다.

- OpponentModeling.on_step          (full strategy + tracking 버전이 단순 버전에 가려짐)
- CombatManager._find_harass_target (worker/tech 우선 풀버전이 base-only 버전에 가려짐)
- EconomyManager._prevent_resource_banking
- EconomyManager._reduce_gas_workers
"""

from __future__ import annotations

import ast
import os
import unittest


def _collect_method_duplicates(path: str):
    """반환값: {(class_name, method_name): [lineno, ...]} (중복만)."""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=path)

    seen: dict[tuple[str, str], list[int]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        local: dict[str, list[int]] = {}
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local.setdefault(item.name, []).append(item.lineno)
        for method, lines in local.items():
            if len(lines) > 1:
                seen[(node.name, method)] = lines
    return seen


_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 현재 정상 운영을 위해 점검 대상이 되는 핵심 매니저 모듈들.
# 새로운 매니저가 추가되면 이 리스트에 등록해 회귀 차단 범위를 넓힌다.
_MODULES_UNDER_GUARD = (
    "opponent_modeling.py",
    "combat_manager.py",
    "economy_manager.py",
    "intel_manager.py",
    "strategy_manager_v2.py",
    "production_controller.py",
)


class TestNoMethodShadowing(unittest.TestCase):
    def test_core_manager_modules_have_no_duplicate_methods(self):
        offenses = []
        for filename in _MODULES_UNDER_GUARD:
            path = os.path.join(_REPO_ROOT, filename)
            if not os.path.exists(path):
                # 모듈 누락은 별개의 결함이지만 이 테스트에서는 통과시킨다.
                continue
            dups = _collect_method_duplicates(path)
            for (cls, method), lines in dups.items():
                offenses.append(f"{filename}:{cls}.{method} duplicated at lines {lines}")
        self.assertFalse(
            offenses,
            "Found duplicate method definitions (shadowing — earlier copies are dead "
            "code at runtime):\n  " + "\n  ".join(offenses),
        )


if __name__ == "__main__":
    unittest.main()
