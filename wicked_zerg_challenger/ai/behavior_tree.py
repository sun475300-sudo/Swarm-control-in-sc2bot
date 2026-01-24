"""
Behavior Tree (행동 트리) 시스템

복잡한 if-else 구조를 체계적인 트리 구조로 변환하여
전략 로직을 명확하고 유지보수 가능하게 만듭니다.

노드 타입:
1. Composite Nodes: Sequence, Selector, Parallel
2. Decorator Nodes: Inverter, Repeater
3. Leaf Nodes: Condition, Action
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Callable, Any
from enum import Enum


class NodeStatus(Enum):
    """노드 실행 상태"""
    SUCCESS = "SUCCESS"    # 성공
    FAILURE = "FAILURE"    # 실패
    RUNNING = "RUNNING"    # 실행 중


class BehaviorNode(ABC):
    """행동 트리 노드 기본 클래스"""

    def __init__(self, name: str = ""):
        self.name = name
        self.status = NodeStatus.FAILURE

    @abstractmethod
    async def tick(self, bot: Any) -> NodeStatus:
        """노드 실행"""
        pass

    def reset(self):
        """노드 상태 초기화"""
        self.status = NodeStatus.FAILURE


# ==================== Composite Nodes ====================

class Sequence(BehaviorNode):
    """
    시퀀스 노드 (AND 로직)

    모든 자식 노드를 순서대로 실행:
    - 모든 자식이 SUCCESS → SUCCESS
    - 하나라도 FAILURE → FAILURE
    - 하나라도 RUNNING → RUNNING
    """

    def __init__(self, name: str, children: List[BehaviorNode]):
        super().__init__(name)
        self.children = children

    async def tick(self, bot: Any) -> NodeStatus:
        for child in self.children:
            status = await child.tick(bot)

            if status == NodeStatus.FAILURE:
                self.status = NodeStatus.FAILURE
                return NodeStatus.FAILURE

            if status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING

        self.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS


class Selector(BehaviorNode):
    """
    셀렉터 노드 (OR 로직)

    자식 노드를 순서대로 실행하여 첫 번째 성공을 찾음:
    - 하나라도 SUCCESS → SUCCESS
    - 모두 FAILURE → FAILURE
    - 하나라도 RUNNING → RUNNING
    """

    def __init__(self, name: str, children: List[BehaviorNode]):
        super().__init__(name)
        self.children = children

    async def tick(self, bot: Any) -> NodeStatus:
        for child in self.children:
            status = await child.tick(bot)

            if status == NodeStatus.SUCCESS:
                self.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS

            if status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING

        self.status = NodeStatus.FAILURE
        return NodeStatus.FAILURE


class Parallel(BehaviorNode):
    """
    병렬 노드

    모든 자식 노드를 동시에 실행:
    - success_threshold 이상 성공 → SUCCESS
    - failure_threshold 이상 실패 → FAILURE
    - 그 외 → RUNNING
    """

    def __init__(
        self,
        name: str,
        children: List[BehaviorNode],
        success_threshold: int = None,
        failure_threshold: int = None
    ):
        super().__init__(name)
        self.children = children
        self.success_threshold = success_threshold or len(children)
        self.failure_threshold = failure_threshold or 1

    async def tick(self, bot: Any) -> NodeStatus:
        success_count = 0
        failure_count = 0

        for child in self.children:
            status = await child.tick(bot)

            if status == NodeStatus.SUCCESS:
                success_count += 1
            elif status == NodeStatus.FAILURE:
                failure_count += 1

        if success_count >= self.success_threshold:
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        if failure_count >= self.failure_threshold:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

        self.status = NodeStatus.RUNNING
        return NodeStatus.RUNNING


# ==================== Decorator Nodes ====================

class Inverter(BehaviorNode):
    """
    인버터 노드

    자식 노드의 결과를 반전:
    - SUCCESS → FAILURE
    - FAILURE → SUCCESS
    - RUNNING → RUNNING
    """

    def __init__(self, name: str, child: BehaviorNode):
        super().__init__(name)
        self.child = child

    async def tick(self, bot: Any) -> NodeStatus:
        status = await self.child.tick(bot)

        if status == NodeStatus.SUCCESS:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        elif status == NodeStatus.FAILURE:
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        else:
            self.status = NodeStatus.RUNNING
            return NodeStatus.RUNNING


class Repeater(BehaviorNode):
    """
    리피터 노드

    자식 노드를 반복 실행:
    - max_repeats: 최대 반복 횟수 (None이면 무한)
    """

    def __init__(self, name: str, child: BehaviorNode, max_repeats: Optional[int] = None):
        super().__init__(name)
        self.child = child
        self.max_repeats = max_repeats
        self.repeat_count = 0

    async def tick(self, bot: Any) -> NodeStatus:
        if self.max_repeats and self.repeat_count >= self.max_repeats:
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        status = await self.child.tick(bot)

        if status == NodeStatus.SUCCESS or status == NodeStatus.FAILURE:
            self.repeat_count += 1

        self.status = NodeStatus.RUNNING
        return NodeStatus.RUNNING

    def reset(self):
        super().reset()
        self.repeat_count = 0
        self.child.reset()


# ==================== Leaf Nodes ====================

class Condition(BehaviorNode):
    """
    조건 노드

    조건 함수를 평가하여 SUCCESS/FAILURE 반환
    """

    def __init__(self, name: str, condition_func: Callable[[Any], bool]):
        super().__init__(name)
        self.condition_func = condition_func

    async def tick(self, bot: Any) -> NodeStatus:
        try:
            result = self.condition_func(bot)
            self.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
            return self.status
        except Exception:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE


class Action(BehaviorNode):
    """
    액션 노드

    실제 행동을 수행하는 노드
    """

    def __init__(self, name: str, action_func: Callable[[Any], Any]):
        super().__init__(name)
        self.action_func = action_func

    async def tick(self, bot: Any) -> NodeStatus:
        try:
            result = await self.action_func(bot)

            # None이면 SUCCESS로 간주
            if result is None:
                self.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS

            # bool 타입이면 SUCCESS/FAILURE
            if isinstance(result, bool):
                self.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
                return self.status

            # NodeStatus 타입이면 그대로 반환
            if isinstance(result, NodeStatus):
                self.status = result
                return result

            # 그 외에는 SUCCESS로 간주
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        except Exception as e:
            print(f"[BT ERROR] Action '{self.name}' failed: {e}")
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE


# ==================== Behavior Tree ====================

class BehaviorTree:
    """
    행동 트리 메인 클래스

    트리 구조를 관리하고 실행합니다.
    """

    def __init__(self, name: str, root: BehaviorNode):
        self.name = name
        self.root = root

    async def tick(self, bot: Any) -> NodeStatus:
        """트리 실행"""
        return await self.root.tick(bot)

    def reset(self):
        """트리 초기화"""
        self.root.reset()


# ==================== 헬퍼 함수 ====================

def create_condition(name: str, condition_func: Callable[[Any], bool]) -> Condition:
    """조건 노드 생성 헬퍼"""
    return Condition(name, condition_func)


def create_action(name: str, action_func: Callable[[Any], Any]) -> Action:
    """액션 노드 생성 헬퍼"""
    return Action(name, action_func)


def create_sequence(name: str, *children: BehaviorNode) -> Sequence:
    """시퀀스 노드 생성 헬퍼"""
    return Sequence(name, list(children))


def create_selector(name: str, *children: BehaviorNode) -> Selector:
    """셀렉터 노드 생성 헬퍼"""
    return Selector(name, list(children))
