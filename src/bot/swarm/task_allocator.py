"""
Task Allocator - Assigns tasks to units in swarm control.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Task:
    """Represents a task assignment."""
    task_type: str  # "attack", "defend", "scout", "harass"
    target_position: tuple
    unit_ids: List[int]
    priority: int = 1


class TaskAllocator:
    """
    Allocates tasks to units for swarm coordination.
    
    This class assigns tasks to individual units based on their
    capabilities and current situation.
    """

    def __init__(self) -> None:
        """Initialize TaskAllocator."""
        self.tasks: List[Task] = []

    def allocate_tasks(self, units: List[Dict[str, Any]], threats: List[Dict[str, Any]]) -> List[Task]:
        """
        Allocate tasks to units based on threats and objectives.
        
        Args:
            units: List of unit information
            threats: List of threat information
            
        Returns:
            List of assigned tasks
        """
        tasks = []
        
        if not threats:
            # No threats: assign scout tasks
            for i, unit in enumerate(units[:3]):  # First 3 units scout
                tasks.append(Task(
                    task_type="scout",
                    target_position=(10.0 + i * 5.0, 10.0 + i * 5.0),
                    unit_ids=[unit.get("id", i)],
                    priority=2
                ))
        else:
            # Threats present: assign defense tasks
            for i, threat in enumerate(threats[:len(units)]):
                unit = units[i] if i < len(units) else units[0]
                tasks.append(Task(
                    task_type="defend",
                    target_position=threat.get("position", (0.0, 0.0)),
                    unit_ids=[unit.get("id", i)],
                    priority=1
                ))
        
        self.tasks = tasks
        return tasks
