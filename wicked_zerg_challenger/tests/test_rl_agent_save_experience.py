"""save_experience_data()의 원자적 저장 보장 검증 (P2.4 백로그 항목).

과거 구현은 os.remove(dest) 후 os.rename(temp, dest)를 사용했는데, 그 사이 구간에서
실패(디스크 full, 프로세스 중단 등)하면 기존 경험 데이터가 이미 삭제된 뒤라 완전히
유실되는 문제가 있었다. repo에 남아있던 orphaned `.tmp.npz` 파일이 이 문제가 실제로
발생했었다는 증거다. 지금은 os.replace() 하나로 교체되어 진짜 원자적 스왑이 된다.
"""

import os
import sys

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from local_training.rl_agent import RLAgent

import pytest


@pytest.fixture
def agent(tmp_path):
    a = RLAgent(model_path=str(tmp_path / "model.npz"))
    a.states = [np.zeros(16, dtype=np.float32) for _ in range(3)]
    a.actions = [0, 1, 2]
    a.rewards = [1.0, 2.0, 3.0]
    return a


def test_save_experience_data_succeeds(agent, tmp_path):
    dest = tmp_path / "experience.npz"
    assert agent.save_experience_data(str(dest)) is True
    assert dest.exists()
    # no leftover temp file
    assert list(tmp_path.glob("*.tmp*.npz")) == []


def test_save_overwrites_existing_file_atomically(agent, tmp_path):
    dest = tmp_path / "experience.npz"
    assert agent.save_experience_data(str(dest)) is True
    first_mtime = dest.stat().st_mtime_ns

    agent.rewards = [9.0, 9.0, 9.0]
    assert agent.save_experience_data(str(dest)) is True
    data = np.load(str(dest))
    assert list(data["rewards"]) == [9.0, 9.0, 9.0]
    assert dest.stat().st_mtime_ns >= first_mtime


def test_disk_full_during_write_preserves_existing_file(agent, tmp_path, monkeypatch):
    dest = tmp_path / "experience.npz"
    assert agent.save_experience_data(str(dest)) is True
    original = dest.read_bytes()

    def raise_enospc(*args, **kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(np, "savez_compressed", raise_enospc)
    agent.rewards = [-1.0, -1.0, -1.0]

    assert agent.save_experience_data(str(dest)) is False
    # the pre-existing file must be untouched — the new write never got far enough
    # to touch the destination at all.
    assert dest.read_bytes() == original
    assert list(tmp_path.glob("*.tmp*.npz")) == []


def test_interrupted_rename_preserves_existing_file(agent, tmp_path, monkeypatch):
    dest = tmp_path / "experience.npz"
    assert agent.save_experience_data(str(dest)) is True
    original = dest.read_bytes()

    def raise_during_replace(*args, **kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", raise_during_replace)
    agent.rewards = [-1.0, -1.0, -1.0]

    assert agent.save_experience_data(str(dest)) is False
    # this is the regression this test guards against: the old implementation
    # removed `dest` before attempting the rename, so a failure here used to
    # wipe out the last-known-good experience data instead of just failing
    # the update.
    assert dest.exists()
    assert dest.read_bytes() == original
    # the failed temp file should be cleaned up, not left behind forever
    assert list(tmp_path.glob("*.tmp*.npz")) == []
