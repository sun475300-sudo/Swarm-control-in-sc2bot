"""
Regression tests for RLAgent.save_experience_data / save_model atomic-write behavior.

Both methods write to a `.tmp` sibling file and then must move it into place with a
single atomic syscall (`os.replace`). The prior implementation deleted the
destination file *before* renaming the temp file into place (or, for save_model,
fell back to `copy + delete` on failure) — leaving a window where a crash mid-save
destroys the previous good file without producing a complete new one. These tests
pin the fixed behavior: no leftover `.tmp` files, and the destination always ends
up with valid, loadable data.
"""

import numpy as np

import pytest

try:
    from wicked_zerg_challenger.local_training.rl_agent import RLAgent
except ImportError:
    pytest.skip("rl_agent dependencies missing", allow_module_level=True)


@pytest.fixture
def agent(temp_dir):
    a = RLAgent(model_path=str(temp_dir / "model.npz"))
    a.states = [np.zeros(15, dtype=np.float32) for _ in range(3)]
    a.actions = [0, 1, 2]
    a.rewards = [1.0, 0.5, -0.5]
    return a


class TestSaveExperienceDataAtomicity:
    def test_no_leftover_tmp_file(self, agent, temp_dir):
        exp_path = temp_dir / "experience.npz"
        assert agent.save_experience_data(str(exp_path)) is True
        assert exp_path.exists()
        assert not (temp_dir / "experience.tmp.npz").exists()

    def test_saved_file_is_loadable_with_correct_data(self, agent, temp_dir):
        exp_path = temp_dir / "experience.npz"
        agent.save_experience_data(str(exp_path))
        data = np.load(str(exp_path))
        assert list(data["actions"]) == [0, 1, 2]

    def test_overwrite_replaces_previous_file_cleanly(self, agent, temp_dir):
        exp_path = temp_dir / "experience.npz"
        agent.save_experience_data(str(exp_path))

        agent.rewards = [9.0, 9.0, 9.0]
        assert agent.save_experience_data(str(exp_path)) is True

        data = np.load(str(exp_path))
        assert list(data["rewards"]) == [9.0, 9.0, 9.0]
        assert not (temp_dir / "experience.tmp.npz").exists()


class TestSaveModelAtomicity:
    def test_no_leftover_tmp_file(self, agent, temp_dir):
        model_path = temp_dir / "model.npz"
        assert agent.save_model(str(model_path)) is True
        assert model_path.exists()
        assert not model_path.with_suffix(".tmp").exists()

    def test_overwrite_replaces_previous_file_cleanly(self, agent, temp_dir):
        model_path = temp_dir / "model.npz"
        agent.save_model(str(model_path))

        agent.episode_count = 42
        assert agent.save_model(str(model_path)) is True

        data = np.load(str(model_path))
        assert int(data["episode_count"][0]) == 42
        assert not model_path.with_suffix(".tmp").exists()
