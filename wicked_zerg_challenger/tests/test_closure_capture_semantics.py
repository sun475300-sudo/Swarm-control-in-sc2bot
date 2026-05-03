# -*- coding: utf-8 -*-
"""
Closure Capture Semantics Tests
================================

Batch 1에서 수정한 27건의 lambda 클로저 캡처 패턴이
실제로 의도한 의미를 가지는지 검증하는 단위 테스트.

수정 패턴: `lambda x: ...var...` → `lambda x, v=var: ...v...`

이 테스트는 SC2 게임 객체 없이 순수 Python으로 패턴만 검증합니다.
"""


def test_late_binding_bug_demonstrates_problem():
    """
    수정 전 패턴: lambda가 var를 늦게 바인딩
    → 모든 lambda가 마지막 var 값을 사용 (버그).
    """
    fns = []
    for i in range(3):
        fns.append(lambda: i)  # noqa: B023 — intentional bug demonstration

    # 모두 마지막 i 값(2)을 캡처
    assert [f() for f in fns] == [2, 2, 2], (
        "Python late-binding 동작 자체가 변경된 것 같습니다 — "
        "이 테스트가 실패하면 호환성 영향 검토 필요."
    )


def test_default_argument_capture_fixes_bug():
    """
    수정 후 패턴: lambda 기본 인자로 즉시 바인딩
    → 각 lambda가 생성 시점의 var 값을 보존.
    """
    fns = []
    for i in range(3):
        fns.append(lambda v=i: v)  # 즉시 바인딩

    assert [f() for f in fns] == [0, 1, 2]


def test_battle_zone_center_capture():
    """
    battle_preparation_system.py 패턴 회귀:
    각 zone마다 다른 zone.center로 enemy_nearby 필터.
    """
    # 가짜 zone 객체
    class Zone:
        def __init__(self, center):
            self.center = center

    zones = [Zone((10, 10)), Zone((20, 20)), Zone((30, 30))]

    # 수정 후 패턴
    filters = []
    for zone in zones:
        zc = zone.center
        filters.append(lambda u_pos, c=zc: u_pos == c)

    # 각 lambda가 자기 zone.center만 매칭해야 함
    assert filters[0]((10, 10)) is True
    assert filters[0]((20, 20)) is False
    assert filters[1]((20, 20)) is True
    assert filters[1]((10, 10)) is False
    assert filters[2]((30, 30)) is True


def test_extractor_tag_capture_in_economy_manager():
    """
    economy_manager.py의 가스 일꾼 필터 패턴:
    각 extractor.tag로 다른 worker filter 생성.
    """
    extractor_tags = [101, 102, 103]

    filters = []
    for tag in extractor_tags:
        filters.append(lambda worker_target, t=tag: worker_target == t)

    assert filters[0](101) is True
    assert filters[0](102) is False
    assert filters[1](102) is True
    assert filters[2](103) is True


def test_overlord_tag_capture_in_overlord_vision_network():
    """
    overlord_vision_network.py의 `overlords.filter(lambda u: u.tag != overlord.tag)` 패턴:
    각 루프 반복마다 새로 할당한 overlord의 태그를 정확히 사용.
    """
    overlord_tags = [201, 202, 203]

    filters = []
    for tag in overlord_tags:
        filters.append(lambda candidate_tag, t=tag: candidate_tag != t)

    # 각 필터가 자기 태그를 올바르게 제외하는지
    assert filters[0](201) is False
    assert filters[0](202) is True
    assert filters[1](202) is False
    assert filters[2](203) is False


def test_tech_type_capture_in_bot_step_integration():
    """
    bot_step_integration.py:2138 — 가장 영향 큰 버그.
    `for tech_type, ...:` 루프 안 lambda가 마지막 tech_type만 사용해
    모든 추천이 같은 tech로 빌드되던 문제.
    """
    techs = ["LAIR", "HIVE", "SPIRE"]

    callbacks = []
    for tech_type in techs:
        callbacks.append(lambda tt=tech_type: tt)

    # 각 콜백이 자기 tech_type을 보존
    assert [cb() for cb in callbacks] == ["LAIR", "HIVE", "SPIRE"]
