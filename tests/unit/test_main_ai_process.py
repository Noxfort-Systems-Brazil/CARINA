# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from unittest.mock import MagicMock, patch
import pytest

from src.main import run_ai_process


@pytest.fixture
def base_mocks(tmp_path):
    mock_pipe = MagicMock()
    mock_guardian_state = MagicMock()
    mock_guardian_signal = MagicMock()
    mock_db_queue = MagicMock()

    return {
        "pipe": mock_pipe,
        "g_state": mock_guardian_state,
        "g_signal": mock_guardian_signal,
        "db_queue": mock_db_queue,
        "tmp_path": tmp_path,
    }


def test_run_ai_process_success(base_mocks):
    mock_trainer = MagicMock()

    with patch("src.utils.paths.get_base_output_dir", return_value=str(base_mocks["tmp_path"])), \
         patch("src.utils.logging_setup.setup_logging"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.setup_environment"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.detect_gpu", return_value={"gpu": "CUDA"}), \
         patch("src.utils.process_monitor.ProcessMonitor.start_background_monitor"), \
         patch("src.utils.settings_manager.SettingsManager.load_config", return_value=configparser.ConfigParser()), \
         patch("src.engine.engine_factory.EngineFactory.create_trainer", return_value=mock_trainer), \
         patch("os._exit") as mock_exit:

        run_ai_process(
            base_mocks["pipe"],
            base_mocks["g_state"],
            base_mocks["g_signal"],
            base_mocks["db_queue"],
        )

        mock_trainer.start_continuous_service.assert_called_once()
        mock_exit.assert_called_once_with(0)


def test_run_ai_process_hardware_import_error(base_mocks):
    with patch("src.utils.paths.get_base_output_dir", return_value=str(base_mocks["tmp_path"])), \
         patch("src.utils.logging_setup.setup_logging"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.setup_environment", side_effect=ImportError("No torch")), \
         patch("os._exit") as mock_exit:

        run_ai_process(
            base_mocks["pipe"],
            base_mocks["g_state"],
            base_mocks["g_signal"],
            base_mocks["db_queue"],
        )

        assert not mock_exit.called


def test_run_ai_process_hardware_generic_error(base_mocks):
    with patch("src.utils.paths.get_base_output_dir", return_value=str(base_mocks["tmp_path"])), \
         patch("src.utils.logging_setup.setup_logging"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.setup_environment", side_effect=RuntimeError("GPU failure")), \
         patch("os._exit") as mock_exit:

        run_ai_process(
            base_mocks["pipe"],
            base_mocks["g_state"],
            base_mocks["g_signal"],
            base_mocks["db_queue"],
        )

        assert not mock_exit.called


def test_run_ai_process_settings_error(base_mocks):
    with patch("src.utils.paths.get_base_output_dir", return_value=str(base_mocks["tmp_path"])), \
         patch("src.utils.logging_setup.setup_logging"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.setup_environment"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.detect_gpu"), \
         patch("src.utils.process_monitor.ProcessMonitor.start_background_monitor"), \
         patch("src.utils.settings_manager.SettingsManager.load_config", side_effect=RuntimeError("INI invalid")), \
         patch("os._exit") as mock_exit:

        run_ai_process(
            base_mocks["pipe"],
            base_mocks["g_state"],
            base_mocks["g_signal"],
            base_mocks["db_queue"],
        )

        assert not mock_exit.called


def test_run_ai_process_interrupt(base_mocks):
    mock_trainer = MagicMock()
    mock_trainer.start_continuous_service.side_effect = KeyboardInterrupt()

    with patch("src.utils.paths.get_base_output_dir", return_value=str(base_mocks["tmp_path"])), \
         patch("src.utils.logging_setup.setup_logging"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.setup_environment"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.detect_gpu"), \
         patch("src.utils.process_monitor.ProcessMonitor.start_background_monitor"), \
         patch("src.utils.settings_manager.SettingsManager.load_config", return_value=configparser.ConfigParser()), \
         patch("src.engine.engine_factory.EngineFactory.create_trainer", return_value=mock_trainer), \
         patch("os._exit") as mock_exit:

        run_ai_process(
            base_mocks["pipe"],
            base_mocks["g_state"],
            base_mocks["g_signal"],
            base_mocks["db_queue"],
        )

        mock_exit.assert_called_once_with(0)


def test_run_ai_process_fatal_error(base_mocks):
    mock_trainer = MagicMock()
    mock_trainer.start_continuous_service.side_effect = RuntimeError("Fatal loop crash")

    with patch("src.utils.paths.get_base_output_dir", return_value=str(base_mocks["tmp_path"])), \
         patch("src.utils.logging_setup.setup_logging"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.setup_environment"), \
         patch("src.utils.hardware_initializer.HardwareInitializer.detect_gpu"), \
         patch("src.utils.process_monitor.ProcessMonitor.start_background_monitor"), \
         patch("src.utils.settings_manager.SettingsManager.load_config", return_value=configparser.ConfigParser()), \
         patch("src.engine.engine_factory.EngineFactory.create_trainer", return_value=mock_trainer), \
         patch("sys.exit") as mock_sys_exit, \
         patch("os._exit") as mock_exit:

        run_ai_process(
            base_mocks["pipe"],
            base_mocks["g_state"],
            base_mocks["g_signal"],
            base_mocks["db_queue"],
        )

        mock_sys_exit.assert_called_once_with(1)
        mock_exit.assert_called_once_with(0)
