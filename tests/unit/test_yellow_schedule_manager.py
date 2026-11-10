# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import time
from unittest.mock import MagicMock
import pytest

from src.controller.yellow_schedule_manager import YellowScheduleManager


class TestYellowScheduleManager:

    def test_is_time_in_window_daytime(self):
        start = time(1, 0)
        end = time(5, 0)

        assert not YellowScheduleManager.is_time_in_window(start, end, time(0, 30))
        assert YellowScheduleManager.is_time_in_window(start, end, time(1, 0))
        assert YellowScheduleManager.is_time_in_window(start, end, time(3, 15))
        assert not YellowScheduleManager.is_time_in_window(start, end, time(5, 0))
        assert not YellowScheduleManager.is_time_in_window(start, end, time(6, 0))

    def test_is_time_in_window_overnight(self):
        start = time(23, 0)
        end = time(5, 0)

        # Before window
        assert not YellowScheduleManager.is_time_in_window(start, end, time(22, 59))
        assert not YellowScheduleManager.is_time_in_window(start, end, time(12, 0))

        # At start and inside late-night
        assert YellowScheduleManager.is_time_in_window(start, end, time(23, 0))
        assert YellowScheduleManager.is_time_in_window(start, end, time(23, 59))

        # After midnight
        assert YellowScheduleManager.is_time_in_window(start, end, time(0, 0))
        assert YellowScheduleManager.is_time_in_window(start, end, time(2, 30))
        assert YellowScheduleManager.is_time_in_window(start, end, time(4, 59))

        # At end and after
        assert not YellowScheduleManager.is_time_in_window(start, end, time(5, 0))
        assert not YellowScheduleManager.is_time_in_window(start, end, time(5, 1))

    def test_is_time_in_window_equal_start_end(self):
        t = time(10, 0)
        assert not YellowScheduleManager.is_time_in_window(t, t, time(10, 0))
        assert not YellowScheduleManager.is_time_in_window(t, t, time(11, 0))

    def test_load_config_and_parsing(self):
        config = {
            "yellow_schedule_enabled": "True",
            "yellow_schedule_start": "22:30",
            "yellow_schedule_end": "06:15",
            "yellow_schedule_all_semaphores": "False",
            "yellow_schedule_semaphores": "TL_1, TL_2, TL_3",
        }

        mgr = YellowScheduleManager(config)

        assert mgr.enabled is True
        assert mgr.start_time == time(22, 30)
        assert mgr.end_time == time(6, 15)
        assert mgr.all_semaphores is False
        assert mgr.semaphores == {"TL_1", "TL_2", "TL_3"}

    def test_is_semaphore_scheduled(self):
        mgr = YellowScheduleManager({
            "yellow_schedule_enabled": True,
            "yellow_schedule_all_semaphores": False,
            "yellow_schedule_semaphores": "J1, J2",
        })

        assert mgr.is_semaphore_scheduled("J1") is True
        assert mgr.is_semaphore_scheduled("J2") is True
        assert mgr.is_semaphore_scheduled("J3") is False

        # Switch to all
        mgr.all_semaphores = True
        assert mgr.is_semaphore_scheduled("J3") is True
        assert mgr.is_semaphore_scheduled("ANY_ID") is True

    def test_toggle_semaphore(self):
        mgr = YellowScheduleManager({
            "yellow_schedule_semaphores": "J1",
        })

        assert "J1" in mgr.semaphores
        # Toggle off
        included = mgr.toggle_semaphore("J1")
        assert included is False
        assert "J1" not in mgr.semaphores

        # Toggle on
        included = mgr.toggle_semaphore("J1")
        assert included is True
        assert "J1" in mgr.semaphores

        # Toggle another
        included = mgr.toggle_semaphore("J2")
        assert included is True
        assert "J2" in mgr.semaphores

    def test_tick_activation_and_restoration(self):
        mock_override_mgr = MagicMock()
        mock_override_mgr.handle_ui_command = MagicMock()
        mock_override_mgr.active_overrides = {}

        mock_action_supervisor = MagicMock()
        mock_action_supervisor.apply_hardware_override = MagicMock()

        mgr = YellowScheduleManager(
            {
                "yellow_schedule_enabled": True,
                "yellow_schedule_start": "23:00",
                "yellow_schedule_end": "05:00",
                "yellow_schedule_all_semaphores": False,
                "yellow_schedule_semaphores": "TL_1, TL_2",
            },
            override_manager=mock_override_mgr,
        )

        # 1. Tick outside window (e.g. 14:00) -> nothing activated
        res = mgr.tick(action_supervisor=mock_action_supervisor, current_time=time(14, 0))
        assert res["activated"] == []
        assert res["restored"] == []
        assert len(mgr.active_scheduled_semaphores) == 0

        # 2. Tick inside window (e.g. 01:00) -> TL_1 and TL_2 activated to ALERT
        res = mgr.tick(action_supervisor=mock_action_supervisor, current_time=time(1, 0))
        assert sorted(res["activated"]) == ["TL_1", "TL_2"]
        assert mgr.active_scheduled_semaphores == {"TL_1", "TL_2"}

        # Verify command sent to override manager and action supervisor
        assert mock_override_mgr.handle_ui_command.call_count == 2
        assert mock_action_supervisor.apply_hardware_override.call_count == 2

        # 3. Tick again inside window -> no duplicate activations
        res = mgr.tick(action_supervisor=mock_action_supervisor, current_time=time(2, 0))
        assert res["activated"] == []
        assert res["restored"] == []

        # 4. Tick outside window (e.g. 05:30) -> restored to NORMAL
        res = mgr.tick(action_supervisor=mock_action_supervisor, current_time=time(5, 30))
        assert sorted(res["restored"]) == ["TL_1", "TL_2"]
        assert len(mgr.active_scheduled_semaphores) == 0
        assert mock_action_supervisor.apply_hardware_override.call_args[0] == ("TL_2", "NORMAL") or \
               mock_action_supervisor.apply_hardware_override.call_args[0] == ("TL_1", "NORMAL")

    def test_tick_when_disabled(self):
        mock_override_mgr = MagicMock()
        mock_override_mgr.handle_ui_command = MagicMock()
        mock_action_supervisor = MagicMock()

        mgr = YellowScheduleManager(
            {
                "yellow_schedule_enabled": False,
                "yellow_schedule_start": "23:00",
                "yellow_schedule_end": "05:00",
                "yellow_schedule_semaphores": "TL_1",
            },
            override_manager=mock_override_mgr,
        )

        # Tick at 01:00 with disabled schedule
        res = mgr.tick(action_supervisor=mock_action_supervisor, current_time=time(1, 0))
        assert res["activated"] == []
        assert len(mgr.active_scheduled_semaphores) == 0
