# -*- coding: utf-8 -*-
"""
Unit Assignment Manager Module

유닛 할당 및 태스크 관리를 담당하는 모듈
"""


def cleanup_assignments(manager):
    """
    죽은 유닛의 할당 정보 정리

    Args:
        manager: CombatManager 인스턴스
    """
    if not hasattr(manager.bot, "units"):
        return

    alive_tags = set(u.tag for u in manager.bot.units)
    stale_tags = [tag for tag in manager._unit_assignments if tag not in alive_tags]
    for tag in stale_tags:
        del manager._unit_assignments[tag]


def assign_unit_to_task(manager, unit_tag, task_name):
    """
    유닛을 특정 태스크에 할당

    Args:
        manager: CombatManager 인스턴스
        unit_tag: 유닛 태그
        task_name: 태스크 이름
    """
    manager._unit_assignments[unit_tag] = task_name

    # Add unit to active task
    if task_name not in manager._active_tasks:
        manager._active_tasks[task_name] = {
            "units": set(),
            "target": None
        }

    manager._active_tasks[task_name]["units"].add(unit_tag)


def unassign_unit(manager, unit_tag):
    """
    유닛 할당 해제

    Args:
        manager: CombatManager 인스턴스
        unit_tag: 유닛 태그
    """
    if unit_tag in manager._unit_assignments:
        task_name = manager._unit_assignments[unit_tag]

        # Remove from active task
        if task_name in manager._active_tasks:
            manager._active_tasks[task_name]["units"].discard(unit_tag)

            # Remove task if no units left
            if not manager._active_tasks[task_name]["units"]:
                del manager._active_tasks[task_name]

        del manager._unit_assignments[unit_tag]


def get_unit_task(manager, unit_tag):
    """
    유닛의 현재 태스크 조회

    Args:
        manager: CombatManager 인스턴스
        unit_tag: 유닛 태그

    Returns:
        str: 태스크 이름 (할당되지 않았으면 None)
    """
    return manager._unit_assignments.get(unit_tag, None)


def get_unassigned_units(manager, units):
    """
    할당되지 않은 유닛 필터링

    Args:
        manager: CombatManager 인스턴스
        units: 유닛 리스트

    Returns:
        list: 할당되지 않은 유닛 리스트
    """
    return [u for u in units if u.tag not in manager._unit_assignments]


def get_units_by_task(manager, task_name):
    """
    특정 태스크에 할당된 유닛 조회

    Args:
        manager: CombatManager 인스턴스
        task_name: 태스크 이름

    Returns:
        set: 유닛 태그 집합
    """
    if task_name not in manager._active_tasks:
        return set()

    return manager._active_tasks[task_name]["units"].copy()


def set_task_target(manager, task_name, target_position):
    """
    태스크의 목표 위치 설정

    Args:
        manager: CombatManager 인스턴스
        task_name: 태스크 이름
        target_position: 목표 위치
    """
    if task_name not in manager._active_tasks:
        manager._active_tasks[task_name] = {
            "units": set(),
            "target": target_position
        }
    else:
        manager._active_tasks[task_name]["target"] = target_position


def get_task_target(manager, task_name):
    """
    태스크의 목표 위치 조회

    Args:
        manager: CombatManager 인스턴스
        task_name: 태스크 이름

    Returns:
        목표 위치 (없으면 None)
    """
    if task_name not in manager._active_tasks:
        return None

    return manager._active_tasks[task_name]["target"]


def clear_task(manager, task_name):
    """
    태스크와 관련된 모든 유닛 할당 해제

    Args:
        manager: CombatManager 인스턴스
        task_name: 태스크 이름
    """
    if task_name not in manager._active_tasks:
        return

    # Unassign all units in this task
    unit_tags = list(manager._active_tasks[task_name]["units"])
    for tag in unit_tags:
        if tag in manager._unit_assignments:
            del manager._unit_assignments[tag]

    # Remove task
    del manager._active_tasks[task_name]


def get_all_active_tasks(manager):
    """
    모든 활성 태스크 조회

    Args:
        manager: CombatManager 인스턴스

    Returns:
        dict: 활성 태스크 딕셔너리
    """
    return manager._active_tasks.copy()


def count_units_in_task(manager, task_name):
    """
    특정 태스크에 할당된 유닛 수 계산

    Args:
        manager: CombatManager 인스턴스
        task_name: 태스크 이름

    Returns:
        int: 유닛 수
    """
    if task_name not in manager._active_tasks:
        return 0

    return len(manager._active_tasks[task_name]["units"])
