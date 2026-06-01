# -*- coding: utf-8 -*-
import os
import sys
import unittest

import pytest

try:
    import numpy as np
except ImportError:
    pytest.skip("numpy not available", allow_module_level=True)

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from local_training.hierarchical_rl.improved_hierarchical_rl import ActorCriticNetwork
except ImportError:
    pytest.skip("hierarchical_rl dependencies not available", allow_module_level=True)


class TestActorCriticNetwork(unittest.TestCase):
    def test_forward_returns_policy_and_value_shapes(self):
        network = ActorCriticNetwork(obs_dim=16, action_dim=7)
        policy, value = network(np.zeros((1, 16), dtype=np.float32))

        self.assertEqual(policy.shape, (1, 7))
        self.assertEqual(value.shape, (1, 1))
        self.assertAlmostEqual(float(policy.sum()), 1.0, places=5)

    def test_compute_gae_returns_matching_lengths(self):
        network = ActorCriticNetwork(obs_dim=16, action_dim=7)
        advantages, returns = network.compute_gae(
            rewards=[1.0, 0.5, -1.0],
            values=[0.2, 0.1, 0.0],
            dones=[0, 0, 1],
        )

        self.assertEqual(len(advantages), 3)
        self.assertEqual(len(returns), 3)


if __name__ == "__main__":
    unittest.main()
