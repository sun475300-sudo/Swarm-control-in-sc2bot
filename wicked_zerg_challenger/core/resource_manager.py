"""
Resource Manager - Thread-Safe Resource Reservation System

Prevents race conditions where multiple managers try to reserve the same resources
simultaneously, leading to over-spending and failed builds.

Features:
- Atomic resource reservation with asyncio locks
- Per-manager reservation tracking
- Available resource calculation
- Automatic release on manager completion
"""

import asyncio
from typing import TYPE_CHECKING, Dict, Tuple, Optional
from wicked_zerg_challenger.utils.logger import get_logger

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI


class ResourceManager:
    """Thread-safe resource reservation system"""

    def __init__(self, bot: "BotAI"):
        self.bot = bot
        self.logger = get_logger("ResourceManager")

        # Asyncio lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Reserved resources tracking
        self._reserved_minerals = 0
        self._reserved_gas = 0

        # Per-manager reservation tracking: {manager_name: (minerals, gas)}
        self._reservations: Dict[str, Tuple[int, int]] = {}

        # Statistics
        self.total_reservations = 0
        self.total_releases = 0
        self.failed_reservations = 0

    async def try_reserve(self, minerals: int, gas: int, manager_name: str) -> bool:
        """
        Attempt to reserve resources atomically

        Args:
            minerals: Amount of minerals to reserve
            gas: Amount of gas to reserve
            manager_name: Name of the manager requesting reservation

        Returns:
            True if successful, False if insufficient resources
        """
        async with self._lock:
            # Calculate currently available resources
            available_m = self.bot.minerals - self._reserved_minerals
            available_g = self.bot.vespene - self._reserved_gas

            # Check if we have enough resources
            if available_m >= minerals and available_g >= gas:
                # Reserve resources
                self._reserved_minerals += minerals
                self._reserved_gas += gas

                # Release any previous reservation from this manager
                if manager_name in self._reservations:
                    old_m, old_g = self._reservations[manager_name]
                    self._reserved_minerals -= old_m
                    self._reserved_gas -= old_g

                # Record new reservation
                self._reservations[manager_name] = (minerals, gas)
                self.total_reservations += 1

                self.logger.debug(
                    f"[RESERVE] {manager_name}: {minerals}M/{gas}G "
                    f"(Total reserved: {self._reserved_minerals}M/{self._reserved_gas}G)"
                )

                return True
            else:
                # Insufficient resources
                self.failed_reservations += 1
                self.logger.debug(
                    f"[RESERVE FAILED] {manager_name} needs {minerals}M/{gas}G, "
                    f"but only {available_m}M/{available_g}G available"
                )
                return False

    async def release(self, manager_name: str) -> None:
        """
        Release reserved resources

        Args:
            manager_name: Name of the manager releasing resources
        """
        async with self._lock:
            if manager_name in self._reservations:
                m, g = self._reservations[manager_name]
                self._reserved_minerals -= m
                self._reserved_gas -= g
                del self._reservations[manager_name]
                self.total_releases += 1

                self.logger.debug(
                    f"[RELEASE] {manager_name}: {m}M/{g}G released "
                    f"(Total reserved: {self._reserved_minerals}M/{self._reserved_gas}G)"
                )

    async def release_partial(self, manager_name: str, minerals: int, gas: int) -> None:
        """
        Release partial resources (e.g., after spending some of reserved amount)

        Args:
            manager_name: Name of the manager
            minerals: Amount of minerals to release
            gas: Amount of gas to release
        """
        async with self._lock:
            if manager_name in self._reservations:
                current_m, current_g = self._reservations[manager_name]

                # Calculate new reservation
                new_m = max(0, current_m - minerals)
                new_g = max(0, current_g - gas)

                # Update global reserves
                self._reserved_minerals -= (current_m - new_m)
                self._reserved_gas -= (current_g - new_g)

                # Update manager reservation
                if new_m > 0 or new_g > 0:
                    self._reservations[manager_name] = (new_m, new_g)
                else:
                    del self._reservations[manager_name]

                self.logger.debug(
                    f"[RELEASE PARTIAL] {manager_name}: {minerals}M/{gas}G "
                    f"(Remaining: {new_m}M/{new_g}G)"
                )

    def get_available_resources(self) -> Tuple[int, int]:
        """
        Get currently available (unreserved) resources

        Returns:
            Tuple of (available_minerals, available_gas)
        """
        available_m = max(0, self.bot.minerals - self._reserved_minerals)
        available_g = max(0, self.bot.vespene - self._reserved_gas)
        return (available_m, available_g)

    def get_reserved_resources(self) -> Tuple[int, int]:
        """
        Get currently reserved resources

        Returns:
            Tuple of (reserved_minerals, reserved_gas)
        """
        return (self._reserved_minerals, self._reserved_gas)

    def get_manager_reservation(self, manager_name: str) -> Optional[Tuple[int, int]]:
        """
        Get reservation for a specific manager

        Args:
            manager_name: Name of the manager

        Returns:
            Tuple of (minerals, gas) or None if no reservation
        """
        return self._reservations.get(manager_name)

    def has_reservation(self, manager_name: str) -> bool:
        """
        Check if a manager has an active reservation

        Args:
            manager_name: Name of the manager

        Returns:
            True if manager has active reservation
        """
        return manager_name in self._reservations

    def get_statistics(self) -> Dict[str, any]:
        """
        Get resource manager statistics

        Returns:
            Dictionary containing statistics
        """
        return {
            "total_reservations": self.total_reservations,
            "total_releases": self.total_releases,
            "failed_reservations": self.failed_reservations,
            "active_reservations": len(self._reservations),
            "reserved_minerals": self._reserved_minerals,
            "reserved_gas": self._reserved_gas,
            "success_rate": (
                self.total_reservations / (self.total_reservations + self.failed_reservations)
                if (self.total_reservations + self.failed_reservations) > 0
                else 0.0
            )
        }

    def log_statistics(self, iteration: int) -> None:
        """Log statistics periodically"""
        if iteration % 2200 == 0 and self.total_reservations > 0:  # Every 100 seconds
            stats = self.get_statistics()
            self.logger.info(
                f"[RESOURCE MANAGER] "
                f"Reservations: {stats['total_reservations']}, "
                f"Releases: {stats['total_releases']}, "
                f"Failed: {stats['failed_reservations']}, "
                f"Success: {stats['success_rate']:.1%}"
            )

            if self._reservations:
                self.logger.info(
                    f"[ACTIVE RESERVATIONS] {len(self._reservations)} managers: "
                    f"{self._reserved_minerals}M/{self._reserved_gas}G total"
                )

    async def clear_stale_reservations(self, iteration: int) -> None:
        """
        Clear reservations that have been held too long (safety mechanism)

        This should rarely trigger if managers properly release resources.
        Called periodically as a safety net.

        Args:
            iteration: Current game iteration
        """
        # Track reservation ages
        if not hasattr(self, '_reservation_times'):
            self._reservation_times: Dict[str, int] = {}

        async with self._lock:
            stale_threshold = 220  # 10 seconds worth of frames

            stale_managers = []
            for manager_name in list(self._reservations.keys()):
                # Track first seen time
                if manager_name not in self._reservation_times:
                    self._reservation_times[manager_name] = iteration

                # Check if stale
                age = iteration - self._reservation_times[manager_name]
                if age > stale_threshold:
                    stale_managers.append(manager_name)

            # Release stale reservations
            for manager_name in stale_managers:
                m, g = self._reservations[manager_name]
                self._reserved_minerals -= m
                self._reserved_gas -= g
                del self._reservations[manager_name]
                del self._reservation_times[manager_name]

                self.logger.warning(
                    f"[STALE RESERVATION] Released stale reservation from {manager_name}: "
                    f"{m}M/{g}G (held for {age} frames)"
                )

            # Clean up times for released reservations
            for manager_name in list(self._reservation_times.keys()):
                if manager_name not in self._reservations:
                    del self._reservation_times[manager_name]
