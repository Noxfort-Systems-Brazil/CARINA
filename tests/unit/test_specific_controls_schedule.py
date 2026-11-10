# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch
import pytest

from ui.handlers.specific_controls_handler import SpecificControlsHandler
from ui.widgets.specific_controls_widget import SpecificControlsWidget


class TestSpecificControlsSchedule:

    @pytest.fixture
    def mock_deps(self):
        control_client = MagicMock()
        dialog_manager = MagicMock()
        locale_manager = MagicMock()
        locale_manager.get_string.side_effect = lambda key, default=None: default or key
        return control_client, dialog_manager, locale_manager

    def test_get_schedule_status_cached(self, mock_deps):
        control_client, dialog_manager, locale_manager = mock_deps
        handler = SpecificControlsHandler(
            control_client=control_client,
            dialog_manager=dialog_manager,
            locale_manager=locale_manager,
        )
        handler.current_semaphore_id = "TL_TEST_1"

        with patch("src.utils.settings_manager.SettingsManager") as mock_sm_cls:
            mock_sm = MagicMock()
            mock_sm.load_settings.return_value = {
                "yellow_schedule_enabled": True,
                "yellow_schedule_start": "22:00",
                "yellow_schedule_end": "06:00",
                "yellow_schedule_all_semaphores": False,
                "yellow_schedule_semaphores": "TL_TEST_1, TL_TEST_2",
            }
            mock_sm_cls.return_value = mock_sm

            status = handler.get_schedule_status()

            assert status["enabled"] is True
            assert status["start"] == "22:00"
            assert status["end"] == "06:00"
            assert status["is_all"] is False
            assert status["is_scheduled"] is True

            # Second call within TTL should use cached manager
            status_cached = handler.get_schedule_status()
            assert status_cached["enabled"] is True
            # load_settings should have been called only once due to cache
            assert mock_sm.load_settings.call_count == 1

    def test_toggle_schedule_enabled(self, mock_deps):
        control_client, dialog_manager, locale_manager = mock_deps
        handler = SpecificControlsHandler(
            control_client=control_client,
            dialog_manager=dialog_manager,
            locale_manager=locale_manager,
        )

        with patch("src.utils.settings_manager.SettingsManager") as mock_sm_cls:
            mock_sm = MagicMock()
            mock_sm.load_settings.return_value = {"yellow_schedule_enabled": False}
            mock_sm_cls.return_value = mock_sm

            new_val = handler.toggle_schedule_enabled()

            assert new_val is True
            mock_sm.save_settings.assert_called_with({"yellow_schedule_enabled": True})
            control_client.set_yellow_schedule.assert_called_with({"yellow_schedule_enabled": True})

    def test_save_custom_schedule(self, mock_deps):
        control_client, dialog_manager, locale_manager = mock_deps
        handler = SpecificControlsHandler(
            control_client=control_client,
            dialog_manager=dialog_manager,
            locale_manager=locale_manager,
        )

        with patch("src.utils.settings_manager.SettingsManager") as mock_sm_cls:
            mock_sm = MagicMock()
            mock_sm_cls.return_value = mock_sm

            success = handler.save_custom_schedule(
                start="00:00",
                end="06:00",
                all_semaphores=True,
                enabled=True,
            )

            assert success is True
            expected_payload = {
                "yellow_schedule_start": "00:00",
                "yellow_schedule_end": "06:00",
                "yellow_schedule_all_semaphores": True,
                "yellow_schedule_enabled": True,
            }
            mock_sm.save_settings.assert_called_with(expected_payload)
            control_client.set_yellow_schedule.assert_called_with(expected_payload)

    def test_time_validation(self):
        assert SpecificControlsWidget._is_valid_time_str("23:00") is True
        assert SpecificControlsWidget._is_valid_time_str("05:30") is True
        assert SpecificControlsWidget._is_valid_time_str("00:00") is True
        assert SpecificControlsWidget._is_valid_time_str("23:59") is True
        assert SpecificControlsWidget._is_valid_time_str("24:00") is False
        assert SpecificControlsWidget._is_valid_time_str("12:60") is False
        assert SpecificControlsWidget._is_valid_time_str("abc") is False
        assert SpecificControlsWidget._is_valid_time_str("") is False
        assert SpecificControlsWidget._is_valid_time_str("12") is False
