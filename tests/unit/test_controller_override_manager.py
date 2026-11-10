# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/controller/override_manager.py
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from src.controller.override_manager import OverrideManager


class TestOverrideManager:
    @pytest.fixture
    def mock_locale(self):
        lm = MagicMock()
        lm.get_string.side_effect = lambda k, default=None, **kw: default or k
        return lm

    def test_init_persistence_and_load_state(self, mock_locale):
        with tempfile.TemporaryDirectory() as tmp_dir:
            mgr = OverrideManager(mock_locale)
            # 1. No scenario name
            mgr.init_persistence("")
            assert mgr.state_file_path is None

            # 2. Valid scenario name
            with patch("src.utils.paths.get_base_output_dir", return_value=tmp_dir):
                # Write an initial state file
                scenario_dir = os.path.join(tmp_dir, "results", "city1")
                os.makedirs(scenario_dir, exist_ok=True)
                state_file = os.path.join(scenario_dir, "override_state.json")
                with open(state_file, "w") as f:
                    json.dump({"semaphores": {"tl_1": "ALERT"}, "streets": {"st_1": "BLOCKED"}}, f)

                mgr.init_persistence("city1")
                assert mgr.active_overrides == {"tl_1": "ALERT"}
                assert mgr.active_street_overrides == {"st_1": "BLOCKED"}

    def test_save_state_and_error_handling(self, mock_locale):
        with tempfile.TemporaryDirectory() as tmp_dir:
            mgr = OverrideManager(mock_locale)
            # Attempt save before init
            mgr._save_state_to_disk()

            mgr.state_file_path = os.path.join(tmp_dir, "state.json")
            mgr.active_overrides = {"tl_1": "OFF"}
            mgr._save_state_to_disk()

            with open(mgr.state_file_path, "r") as f:
                data = json.load(f)
            assert data["semaphores"]["tl_1"] == "OFF"

            # Test IOError handling
            with patch("builtins.open", side_effect=IOError("Permission denied")):
                mgr._save_state_to_disk()

    def test_handle_ui_command(self, mock_locale):
        mgr = OverrideManager(mock_locale)
        sumo_conn = MagicMock()
        sumo_conn.trafficlight.getIDList.return_value = ["tl_1", "tl_2"]

        # Missing params
        mgr.handle_ui_command({}, sumo_conn)

        # Semaphore not in simulation
        mgr.active_overrides["tl_unknown"] = "ALERT"
        mgr.handle_ui_command({"semaphore_id": "tl_unknown", "state": "ALERT"}, sumo_conn)
        assert "tl_unknown" not in mgr.active_overrides

        # Alert
        mgr.handle_ui_command({"semaphore_id": "tl_1", "state": "ALERT"}, sumo_conn)
        assert mgr.active_overrides["tl_1"] == "ALERT"

        # Off
        mgr.handle_ui_command({"semaphore_id": "tl_1", "state": "OFF"}, sumo_conn)
        assert mgr.active_overrides["tl_1"] == "OFF"

        # Normal
        mgr.handle_ui_command({"semaphore_id": "tl_1", "state": "NORMAL"}, sumo_conn)
        assert "tl_1" not in mgr.active_overrides

    def test_restore_sumo_state(self, mock_locale):
        mgr = OverrideManager(mock_locale)
        # Empty
        mgr.restore_sumo_state(None)

        mgr.active_overrides = {"tl_1": "ALERT"}
        sumo_conn = MagicMock()
        sumo_conn.trafficlight.getIDList.return_value = ["tl_1"]

        mgr.restore_sumo_state(sumo_conn)
        assert mgr.active_overrides["tl_1"] == "ALERT"

    def test_handle_street_command(self, mock_locale):
        mgr = OverrideManager(mock_locale)
        # Missing params
        mgr.handle_street_command({})

        # Blocked
        mgr.handle_street_command({"street_id": "main_st", "state": "BLOCKED"})
        assert mgr.active_street_overrides["main_st"] == "BLOCKED"

        # Normal
        mgr.handle_street_command({"street_id": "main_st", "state": "NORMAL"})
        assert "main_st" not in mgr.active_street_overrides

    def test_is_ai_command_blocked(self, mock_locale):
        mgr = OverrideManager(mock_locale)
        mgr.active_overrides["tl_1"] = "ALERT"

        # Blocked
        assert mgr.is_ai_command_blocked(("trafficlight", "setPhase", ["tl_1", 2], {})) is True

        # Not blocked (different light)
        assert mgr.is_ai_command_blocked(("trafficlight", "setPhase", ["tl_2", 2], {})) is False

        # Not blocked (different function)
        assert mgr.is_ai_command_blocked(("trafficlight", "getPhase", ["tl_1"], {})) is False

        # Malformed request
        assert mgr.is_ai_command_blocked(("invalid",)) is False
