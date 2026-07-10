"""RLAgent 모델/경험 데이터 저장 가드 테스트.

save_model()과 save_experience_data()는 "임시 파일 기록 후 원자적 rename"
방식으로 구현되어 있다. 두 가지 회귀를 검증한다:

1. save_model()이 실제로 최종 경로에 파일을 만드는지 (numpy가 .npz 확장자를
   자동으로 덧붙이는 탓에, 존재 확인/이름 변경 시 잘못된 경로를 참조하면
   저장이 조용히 스킵되는 버그가 있었다).
2. 저장 도중 예외가 나도(디스크 풀 등) 기존 파일이 삭제된 채로 남지 않는지.
"""

import os
from pathlib import Path

import pytest
from wicked_zerg_challenger.local_training.rl_agent import RLAgent


@pytest.fixture
def agent(tmp_path):
    model_path = tmp_path / "rl_agent_model.npz"
    return RLAgent(model_path=str(model_path))


class TestSaveModel:
    def test_save_model_creates_file_at_exact_path(self, agent):
        assert agent.save_model() is True
        assert agent.model_path.exists()
        assert agent.model_path.is_file()
        # No stray temp file left behind.
        assert not Path(str(agent.model_path) + ".tmp").exists()
        assert not Path(str(agent.model_path)[:-4] + ".tmp.npz").exists()

    def test_save_model_round_trips_weights(self, agent):
        agent.policy.W1[:] = 3.0
        assert agent.save_model() is True

        reloaded = RLAgent(model_path=str(agent.model_path))
        assert reloaded._load_model() is True
        assert (reloaded.policy.W1 == 3.0).all()

    def test_save_model_preserves_previous_file_on_write_failure(
        self, agent, monkeypatch
    ):
        assert agent.save_model() is True
        original_bytes = agent.model_path.read_bytes()

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", boom)
        assert agent.save_model() is False

        # The previously-saved model must still be intact and untouched.
        assert agent.model_path.exists()
        assert agent.model_path.read_bytes() == original_bytes


class TestSaveExperienceData:
    def test_save_experience_data_creates_file_at_exact_path(self, agent, tmp_path):
        agent.states = [[0.0] * agent.policy.input_dim]
        agent.actions = [0]
        agent.rewards = [1.0]

        out_path = tmp_path / "experience.npz"
        assert agent.save_experience_data(str(out_path)) is True
        assert out_path.exists()

    def test_save_experience_data_preserves_previous_file_on_write_failure(
        self, agent, tmp_path, monkeypatch
    ):
        agent.states = [[0.0] * agent.policy.input_dim]
        agent.actions = [0]
        agent.rewards = [1.0]

        out_path = tmp_path / "experience.npz"
        assert agent.save_experience_data(str(out_path)) is True
        original_bytes = out_path.read_bytes()

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", boom)
        assert agent.save_experience_data(str(out_path)) is False

        assert out_path.exists()
        assert out_path.read_bytes() == original_bytes
