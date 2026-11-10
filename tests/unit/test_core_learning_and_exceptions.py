# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/core/learning_coordinator.py and src/core/exceptions.py
"""

from unittest.mock import MagicMock, patch
import pytest
import torch

from src.core.exceptions import (
    CarinaError,
    ConfigurationError,
    DatabaseError,
    EVPError,
    FailsafeActivationError,
    HardwareCommunicationError,
    SafetyViolationError,
    SecurityError,
    TelemetryDispatchError,
)
from src.core.learning_coordinator import LearningCoordinator


class TestCoreExceptions:
    def test_exception_hierarchy(self):
        assert issubclass(SafetyViolationError, CarinaError)
        assert issubclass(HardwareCommunicationError, CarinaError)
        assert issubclass(FailsafeActivationError, CarinaError)
        assert issubclass(ConfigurationError, CarinaError)
        assert issubclass(TelemetryDispatchError, CarinaError)
        assert issubclass(DatabaseError, CarinaError)
        assert issubclass(SecurityError, CarinaError)
        assert issubclass(EVPError, CarinaError)

    def test_exception_instantiation(self):
        err = SafetyViolationError("Minimum green violated")
        assert str(err) == "Minimum green violated"
        assert isinstance(err, CarinaError)
        db_err = DatabaseError("Query failed")
        assert isinstance(db_err, CarinaError)
        sec_err = SecurityError("Auth failed")
        assert isinstance(sec_err, CarinaError)
        evp_err = EVPError("Preemption conflict")
        assert isinstance(evp_err, CarinaError)



class TestLearningCoordinator:
    @pytest.fixture
    def mock_locale(self):
        lm = MagicMock()
        lm.get_string.side_effect = lambda k, default=None, fallback=None, **kw: default or fallback or k
        return lm

    @pytest.fixture
    def mock_agent(self):
        agent = MagicMock()
        agent.hyperparams = {"lr": 0.001}
        agent.current_reward_bonus = 0.5
        agent.steps_done = 10
        agent.policy_net = MagicMock()
        agent.optimizer = MagicMock()
        agent.evaluate = MagicMock()

        memory = MagicMock()
        memory.__len__.return_value = 4
        # Returns batch of transitions
        dummy_s = torch.zeros((4, 4, 10))
        dummy_a = torch.zeros(4)
        dummy_logp = torch.zeros(4)
        dummy_r = [1.0] * 4
        dummy_d = [False] * 4
        dummy_v = torch.zeros(4)
        memory.get_batch.return_value = (dummy_s, dummy_a, dummy_logp, dummy_r, dummy_d, dummy_v)
        agent.memory = memory
        return agent

    def test_init_with_shared_pae(self, mock_locale, mock_agent):
        shared_pae = MagicMock()
        shared_pae.history_len = 4
        shared_pae.input_dim = 10

        with (
            patch("torch.utils.tensorboard.SummaryWriter"),
            patch("src.utils.paths.get_base_output_dir", return_value="/tmp"),
        ):
            coord = LearningCoordinator(
                agents={"tl_1": mock_agent},
                state_history={},
                locale_manager=mock_locale,
                shared_pae=shared_pae,
            )
            assert coord.pae_memory is not None
            assert coord.writer is not None
            coord.close()
            assert coord.writer is None

    def test_store_experience(self, mock_locale, mock_agent):
        with (
            patch("torch.utils.tensorboard.SummaryWriter"),
            patch("src.utils.paths.get_base_output_dir", return_value="/tmp"),
        ):
            coord = LearningCoordinator(
                agents={"tl_1": mock_agent},
                state_history={},
                locale_manager=mock_locale,
            )

            decision_data = {
                "tl_1": {
                    "state_sequence": [1, 2, 3],
                    "action": 1,
                    "log_prob": 0.5,
                    "state_val": 0.2,
                }
            }
            coord.store_experience(decision_data, rewards={"tl_1": 2.0}, done=False)

            mock_agent.push_memory.assert_called_once_with(
                state_sequence=[1, 2, 3],
                action=1,
                log_prob=0.5,
                reward=2.5,  # 2.0 + current_reward_bonus 0.5
                done=False,
                state_value=0.2,
            )
            coord.close()

    def test_update_agents_and_pae_training(self, mock_locale, mock_agent):
        shared_pae = MagicMock()
        shared_pae.pad_to_input_dim.side_effect = lambda x: x

        with (
            patch("torch.utils.tensorboard.SummaryWriter") as mock_writer_cls,
            patch("src.utils.paths.get_base_output_dir", return_value="/tmp"),
        ):
            mock_writer = MagicMock()
            mock_writer_cls.return_value = mock_writer

            coord = LearningCoordinator(
                agents={"tl_1": mock_agent},
                state_history={},
                locale_manager=mock_locale,
                shared_pae=shared_pae,
            )

            # Mock pae_optimizer step
            coord.pae_optimizer = MagicMock()
            coord.pae_optimizer.step.return_value = 0.15
            coord.pae_optimizer.step_from_memory.return_value = 0.12
            coord.ppo_optimizer = MagicMock()
            coord.ppo_optimizer.step.return_value = 0.42

            coord.update_agents(last_states={}, last_done=False)

            assert coord.ppo_optimizer.step.called
            assert mock_agent.memory.clear.called

            # Check writer was called
            assert mock_writer.add_scalar.called
            coord.close()

    def test_update_agents_fallback_memory_style(self, mock_locale):
        mock_agent = MagicMock()
        mock_agent.memory = [1, 2, 3]  # No get_batch method
        with (
            patch("torch.utils.tensorboard.SummaryWriter"),
            patch("src.utils.paths.get_base_output_dir", return_value="/tmp"),
        ):
            coord = LearningCoordinator(
                agents={"tl_1": mock_agent},
                state_history={},
                locale_manager=mock_locale,
            )
            coord.update_agents(last_states={}, last_done=False)
            coord.close()

    def test_close_handles_exception(self, mock_locale):
        with (
            patch("torch.utils.tensorboard.SummaryWriter") as mock_writer_cls,
            patch("src.utils.paths.get_base_output_dir", return_value="/tmp"),
        ):
            mock_writer = MagicMock()
            mock_writer.close.side_effect = RuntimeError("I/O error")
            mock_writer_cls.return_value = mock_writer

            coord = LearningCoordinator(
                agents={},
                state_history={},
                locale_manager=mock_locale,
            )
            coord.close()  # Must not raise
            assert coord.writer is None


class TestStructuralGraphBuilder:
    @pytest.fixture
    def mock_locale(self):
        lm = MagicMock()
        lm.get_string.side_effect = lambda k, default=None, fallback=None, **kw: default or fallback or k
        return lm

    def test_build_network_graph_empty_tls_raises(self, mock_locale):
        from src.core.structural_graph_builder import StructuralGraphBuilder

        conn = MagicMock()
        conn.trafficlight.getIDList.return_value = []
        with pytest.raises(ValueError, match="No traffic lights found"):
            StructuralGraphBuilder.build_network_graph(conn, torch.device("cpu"), mock_locale)

    def test_build_network_graph_success(self, mock_locale):
        from src.core.structural_graph_builder import StructuralGraphBuilder

        conn = MagicMock()
        conn.simulation.getOption.return_value = "net.xml"
        conn.trafficlight.getIDList.return_value = ["tl_1", "tl_2"]
        conn.junction.getPosition.side_effect = lambda tl: (0.0, 0.0) if tl == "tl_1" else (100.0, 0.0)
        conn.trafficlight.getControlledLanes.return_value = ["lane_1", "lane_2"]

        phase_g = MagicMock()
        phase_g.state = "GGGrrr"
        phase_y = MagicMock()
        phase_y.state = "yyyrrr"
        logic = MagicMock()
        logic.phases = [phase_g, phase_y]
        conn.trafficlight.getCompleteRedYellowGreenDefinition.return_value = [logic]

        with patch(
            "src.core.structural_graph_builder.build_structural_neighborhood_map",
            return_value={"tl_1": ["tl_2"], "tl_2": ["tl_1"]},
        ):
            res = StructuralGraphBuilder.build_network_graph(conn, torch.device("cpu"), mock_locale)
            edge_idx, max_dim, tl_to_idx, idx_to_tl, n_nodes, n_edges = res
            assert n_nodes == 2
            assert n_edges == 2
            assert max_dim > 0
            assert "tl_1" in tl_to_idx
            assert idx_to_tl[0] in ("tl_1", "tl_2")

    def test_extract_padded_features(self, mock_locale):
        from src.core.structural_graph_builder import StructuralGraphBuilder

        current_states = {
            "tl_1": [1.0, 2.0],  # Needs padding
            "tl_2": None,        # Invalid/missing -> zeros
            "tl_3": [1.0, 2.0, 3.0, 4.0, 5.0],  # Truncated
        }
        tl_idx_to_id = {0: "tl_1", 1: "tl_2", 2: "tl_3"}
        feats, valid_idx = StructuralGraphBuilder.extract_padded_features(
            current_states_dict=current_states,
            tl_idx_to_id=tl_idx_to_id,
            num_agents=3,
            max_state_dim=4,
            sim_time=100.0,
            lm=mock_locale,
        )

        assert len(feats) == 3
        assert feats[0] == [1.0, 2.0, 0.0, 0.0]
        assert feats[1] == [0.0, 0.0, 0.0, 0.0]
        assert feats[2] == [1.0, 2.0, 3.0, 4.0]
        assert valid_idx == [0, 2]

