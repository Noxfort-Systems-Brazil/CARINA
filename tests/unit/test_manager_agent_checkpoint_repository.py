# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/manager/agent_checkpoint_repository.py
"""

import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest
import torch

from src.manager.agent_checkpoint_repository import AgentCheckpointRepository


class TestAgentCheckpointRepository:
    def test_get_checkpoint_dir(self):
        with patch("src.manager.agent_checkpoint_repository.get_base_output_dir", return_value="/tmp/carina"):
            d = AgentCheckpointRepository.get_checkpoint_dir("/data/maps/grid4x4.net.xml")
            assert d == os.path.join("/tmp/carina", "results", "grid4x4", "checkpoints")

    def test_save_system_state_all_components_and_errors(self):
        # Empty map_path
        AgentCheckpointRepository.save_system_state("", {}, None)

        with tempfile.TemporaryDirectory() as tmp_dir:
            map_path = os.path.join(tmp_dir, "test.net.xml")

            with patch("src.manager.agent_checkpoint_repository.get_base_output_dir", return_value=tmp_dir):
                agent_ok = MagicMock()
                agent_err = MagicMock()
                agent_err.save.side_effect = RuntimeError("Disk error")

                strat_ok = MagicMock()
                pae_mock = MagicMock()
                pae_mock.state_dict.return_value = {"pae_weight": torch.tensor([1.0])}

                guardian_mock = MagicMock()
                guardian_mock.policy_net.state_dict.return_value = {"g_weight": torch.tensor([2.0])}

                with patch("torch.save") as mock_torch_save:
                    AgentCheckpointRepository.save_system_state(
                        map_path=map_path,
                        agents={"tl:1": agent_ok, "tl:2": agent_err},
                        strategist=strat_ok,
                        shared_pae=pae_mock,
                        guardians={"tl:1": guardian_mock},
                    )

                    assert agent_ok.save.called
                    assert strat_ok.save_checkpoint.called
                    assert mock_torch_save.call_count >= 2

    def test_restore_system_state_success_and_missing(self):
        # Empty map_path
        AgentCheckpointRepository.restore_system_state("", {}, None)

        with tempfile.TemporaryDirectory() as tmp_dir:
            map_path = os.path.join(tmp_dir, "test.net.xml")

            with patch("src.manager.agent_checkpoint_repository.get_base_output_dir", return_value=tmp_dir):
                # 1. Non-existent checkpoint dir
                AgentCheckpointRepository.restore_system_state(map_path, {"tl_1": MagicMock()}, None)

                # 2. Existing checkpoint dir with files
                ckpt_dir = AgentCheckpointRepository.get_checkpoint_dir(map_path)
                os.makedirs(ckpt_dir, exist_ok=True)

                open(os.path.join(ckpt_dir, "agent_tl_1.pth"), "w").close()
                open(os.path.join(ckpt_dir, "strategist_global.pth"), "w").close()
                open(os.path.join(ckpt_dir, "pae_universal.pth"), "w").close()
                open(os.path.join(ckpt_dir, "guardian_tl_1.pth"), "w").close()

                agent = MagicMock()
                strat = MagicMock()
                pae = MagicMock()
                guardian = MagicMock()

                with patch("torch.load", return_value={"mock_w": 1}):
                    AgentCheckpointRepository.restore_system_state(
                        map_path=map_path,
                        agents={"tl_1": agent},
                        strategist=strat,
                        shared_pae=pae,
                        guardians={"tl_1": guardian},
                        device=torch.device("cpu"),
                    )

                    assert agent.load.called
                    assert strat.load_checkpoint.called
                    assert pae.load_state_dict.called
                    assert guardian.policy_net.load_state_dict.called
                    assert guardian.target_net.load_state_dict.called
