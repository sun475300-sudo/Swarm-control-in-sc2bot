"""
Phase 375: Auto Updater
Blue-green deployment system for zero-downtime model updates.
Handles version checking, model download, hot-swapping, and rollback.
"""

import hashlib
import json
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class VersionInfo:
    version: str
    release_date: float
    model_url: str
    config_url: str
    checksum_sha256: str
    changelog: str = ""
    is_stable: bool = True

    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "release_date": self.release_date,
            "model_url": self.model_url,
            "config_url": self.config_url,
            "checksum_sha256": self.checksum_sha256,
            "changelog": self.changelog,
            "is_stable": self.is_stable,
        }


class VersionManager:
    """Manages local model versions and selects active slot (blue/green)."""

    SLOTS = ["blue", "green"]

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self._active_slot: str = "blue"
        self._slot_versions: Dict[str, Optional[str]] = {"blue": None, "green": None}
        self._version_registry: Dict[str, VersionInfo] = {}
        os.makedirs(self._slot_path("blue"), exist_ok=True)
        os.makedirs(self._slot_path("green"), exist_ok=True)

    def _slot_path(self, slot: str) -> str:
        return os.path.join(self.base_dir, f"model_{slot}")

    @property
    def active_slot(self) -> str:
        return self._active_slot

    @property
    def standby_slot(self) -> str:
        return "green" if self._active_slot == "blue" else "blue"

    def register_version(self, info: VersionInfo):
        self._version_registry[info.version] = info

    def active_version(self) -> Optional[str]:
        return self._slot_versions.get(self._active_slot)

    def standby_version(self) -> Optional[str]:
        return self._slot_versions.get(self.standby_slot)

    def set_slot_version(self, slot: str, version: str):
        self._slot_versions[slot] = version

    def swap_slots(self):
        """Atomically switch the active slot."""
        self._active_slot = self.standby_slot

    def get_active_model_path(self) -> str:
        return os.path.join(self._slot_path(self._active_slot), "model.pt")

    def get_standby_model_path(self) -> str:
        return os.path.join(self._slot_path(self.standby_slot), "model.pt")


class AutoUpdater:
    """
    Manages the full lifecycle of bot model updates:
    check → download → verify → hot-swap → rollback on failure.
    """

    CHECK_INTERVAL_S = 3600  # check for updates every hour
    MAX_RETRIES = 3

    def __init__(
        self,
        version_manager: VersionManager,
        update_manifest_path: str,
        on_swap_callback: Optional[Callable[[str], None]] = None,
    ):
        self.vm = version_manager
        self.manifest_path = update_manifest_path
        self._on_swap = on_swap_callback
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._update_history: List[Dict] = []

    # ------------------------------------------------------------------
    # Version checking
    # ------------------------------------------------------------------

    def check_for_updates(self) -> Optional[VersionInfo]:
        """
        Read the local update manifest and return new version info if available.
        Returns None if already on the latest version.
        """
        if not os.path.exists(self.manifest_path):
            return None
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        latest_ver = data.get("latest_version", "")
        current_ver = self.vm.active_version() or ""

        if latest_ver == current_ver:
            return None

        info = VersionInfo(
            version=latest_ver,
            release_date=data.get("release_date", time.time()),
            model_url=data.get("model_url", ""),
            config_url=data.get("config_url", ""),
            checksum_sha256=data.get("checksum_sha256", ""),
            changelog=data.get("changelog", ""),
            is_stable=data.get("is_stable", True),
        )
        self.vm.register_version(info)
        return info

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download_new_model(self, version_info: VersionInfo) -> bool:
        """
        Download model file to standby slot.
        Simulates download in offline mode; real impl would use requests/urllib.
        Returns True on success.
        """
        dest_dir = self.vm._slot_path(self.vm.standby_slot)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, "model.pt")

        # Simulate download: write a placeholder file
        try:
            if version_info.model_url.startswith("file://"):
                src = version_info.model_url[7:]
                if os.path.exists(src):
                    shutil.copy2(src, dest_path)
                else:
                    # Create stub model file for testing
                    with open(dest_path, "wb") as f:
                        f.write(b"STUB_MODEL_" + version_info.version.encode())
            else:
                # Offline fallback: create stub
                with open(dest_path, "wb") as f:
                    f.write(b"STUB_MODEL_" + version_info.version.encode())

            self.vm.set_slot_version(self.vm.standby_slot, version_info.version)
            return True
        except OSError:
            return False

    def _verify_checksum(self, file_path: str, expected_sha256: str) -> bool:
        """Verify SHA-256 checksum of downloaded model file."""
        if not expected_sha256 or not os.path.exists(file_path):
            return True  # Skip verification if no checksum provided
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest() == expected_sha256

    # ------------------------------------------------------------------
    # Hot swap
    # ------------------------------------------------------------------

    def hot_swap_model(self, version_info: VersionInfo) -> bool:
        """
        Swap standby slot to active.
        Calls on_swap_callback so the bot can reload weights.
        Returns True on success.
        """
        with self._lock:
            standby_path = self.vm.get_standby_model_path()
            if not os.path.exists(standby_path):
                return False

            if not self._verify_checksum(standby_path, version_info.checksum_sha256):
                return False

            prev_version = self.vm.active_version()
            self.vm.swap_slots()

            record = {
                "timestamp": time.time(),
                "from_version": prev_version,
                "to_version": version_info.version,
                "success": True,
            }
            self._update_history.append(record)

            if self._on_swap:
                try:
                    self._on_swap(self.vm.get_active_model_path())
                except Exception as exc:
                    # Callback failure triggers rollback
                    self.rollback_on_failure(prev_version, str(exc))
                    return False

            return True

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def rollback_on_failure(self, previous_version: Optional[str], reason: str = ""):
        """
        Swap back to previous slot if the new model caused failures.
        """
        with self._lock:
            current = self.vm.active_version()
            # Swap back
            self.vm.swap_slots()
            record = {
                "timestamp": time.time(),
                "action": "rollback",
                "from_version": current,
                "to_version": previous_version,
                "reason": reason,
            }
            self._update_history.append(record)
            if self._on_swap:
                try:
                    self._on_swap(self.vm.get_active_model_path())
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Background update loop
    # ------------------------------------------------------------------

    def start_background_checks(self):
        """Launch a background thread that polls for updates."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def stop_background_checks(self):
        self._running = False

    def _update_loop(self):
        while self._running:
            try:
                new_version = self.check_for_updates()
                if new_version and new_version.is_stable:
                    downloaded = self.download_new_model(new_version)
                    if downloaded:
                        self.hot_swap_model(new_version)
            except Exception:
                pass
            for _ in range(self.CHECK_INTERVAL_S):
                if not self._running:
                    break
                time.sleep(1)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict:
        return {
            "active_slot": self.vm.active_slot,
            "active_version": self.vm.active_version(),
            "standby_slot": self.vm.standby_slot,
            "standby_version": self.vm.standby_version(),
            "background_running": self._running,
            "update_count": len([r for r in self._update_history if r.get("success")]),
            "rollback_count": len(
                [r for r in self._update_history if r.get("action") == "rollback"]
            ),
        }
