# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Tests for field-readiness fixes: config_path propagation, token forwarding, and phase timing alignment."""

import logging
from unittest.mock import MagicMock, patch

from src.controller.connection_operation_handler import ConnectionOperationHandler
from src.drivers.driver_factory import DriverFactory
from src.drivers.go_process_manager import _build_gateway_child_env
from src.drivers.remote_gateway_backend import RemoteGatewayBackend
from src.drivers.traffic_light_driver import TrafficLightDriver
from src.manager.stage_transition_manager import StageTransitionManager


def test_connection_handler_propagates_config_path_to_go_gateway():
    mock_client = MagicMock()
    mock_client.is_running.return_value = True
    mock_client.connect_intersection.return_value = {
        "success": True,
        "data": {"protocol": "NTCIP 1202", "brand": "Siemens", "model": "ST950"},
    }

    with (
        patch("src.drivers.driver_factory.GoGatewayClient.get_instance", return_value=mock_client),
        patch("src.drivers.traffic_light_driver.TrafficMapLoader.load_stage_states", return_value={0: "GGrr"}),
    ):
        active = {}
        saved_ips = {}
        saved_snmp = {
            "tl_campo_1": {
                "version": "v2c",
                "community": "priv_tl1",
                "config_path": "/opt/carina/profiles/siemens_st950.json",
            }
        }
        mock_repo = MagicMock()
        handler = ConnectionOperationHandler(
            active_connections=active,
            saved_ips=saved_ips,
            saved_snmp_configs=saved_snmp,
            config_repo=mock_repo,
            csv_store=mock_repo,
        )

        ok = handler.toggle_connection(
            intersection_id="tl_campo_1",
            ip_address="192.168.10.20:161",
            action="connect",
            green_stages_provider=lambda _tl: [0, 2],
            save_to_db=False,
        )
        assert ok is True
        mock_client.connect_intersection.assert_called_once()
        kwargs = mock_client.connect_intersection.call_args.kwargs
        assert kwargs["config_path"] == "/opt/carina/profiles/siemens_st950.json"
        assert kwargs["community"] == "priv_tl1"


def test_traffic_light_driver_forwards_explicit_config_path():
    mock_hw = MagicMock()
    with (
        patch("src.drivers.traffic_light_driver.TrafficMapLoader.load_stage_states", return_value={0: "GGrr"}),
        patch("src.drivers.traffic_light_driver.DriverFactory.create_and_connect_driver", return_value=mock_hw) as mf,
    ):
        drv = TrafficLightDriver(
            intersection_id="tl_custom",
            ip_address="10.0.0.5",
            port=161,
            config_path="/etc/carina/tesc_oids.json",
        )
        assert drv.is_connected is True
        assert mf.call_args.kwargs["config_path"] == "/etc/carina/tesc_oids.json"


def test_driver_factory_forwards_config_path_without_error():
    mock_client = MagicMock()
    mock_client.is_running.return_value = True
    mock_client.connect_intersection.return_value = {"success": True, "data": {"protocol": "UTMC2"}}

    with patch("src.drivers.driver_factory.GoGatewayClient.get_instance", return_value=mock_client):
        proxy = DriverFactory.create_and_connect_driver(
            ip_address="10.0.0.6",
            port=161,
            intersection_id="tl_utmc_profile",
            green_stages=[0, 1],
            config_path="/etc/carina/utmc_custom.json",
        )
        assert proxy is not None
        assert mock_client.connect_intersection.call_args.kwargs["config_path"] == "/etc/carina/utmc_custom.json"


def test_go_process_env_and_remote_gateway_sync_forward_tokens(monkeypatch):
    monkeypatch.delenv("CARINA_EVP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("CARINA_CCO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("CARINA_CCO_ALLOWED_ORIGIN", raising=False)

    fake_settings = {
        "evp_auth_token": "evp-field-tok",
        "cco_auth_token": "cco-field-tok",
        "cco_allowed_origin": "https://cco.prefeitura.gov.br",
    }

    with patch("src.utils.settings_manager.SettingsManager.load_settings", return_value=fake_settings):
        child_env = _build_gateway_child_env()
        assert child_env["CARINA_EVP_AUTH_TOKEN"] == "evp-field-tok"
        assert child_env["CARINA_CCO_AUTH_TOKEN"] == "cco-field-tok"
        assert child_env["CARINA_CCO_ALLOWED_ORIGIN"] == "https://cco.prefeitura.gov.br"

        mock_client = MagicMock()
        mock_client.is_running.return_value = True
        backend = RemoteGatewayBackend(go_client=mock_client, tailscale_adapter=MagicMock())
        backend.sync_enabled_state(True)

        calls = [c.args[0] for c in mock_client.send_command.call_args_list]
        assert "gateway_set_auth_tokens" in calls
        assert "gateway_set_enabled" in calls
        auth_call = next(c for c in mock_client.send_command.call_args_list if c.args[0] == "gateway_set_auth_tokens")
        assert auth_call.kwargs["evp_auth_token"] == "evp-field-tok"
        assert auth_call.kwargs["cco_auth_token"] == "cco-field-tok"
        assert auth_call.kwargs["allowed_origin"] == "https://cco.prefeitura.gov.br"


def test_stage_transition_manager_honors_per_intersection_yellow_duration():
    extractor = MagicMock()
    extractor.tl_green_stages = {"TL_WIDE": [0, 3]}
    extractor.tl_stage_codes = {"TL_WIDE": {0: "GGrr", 1: "yyrr", 2: "rrrr", 3: "rrGG"}}
    # Wide avenue: yellow stage 1 takes 6.0s (> SafetyRules floor of 4.0s)
    extractor.tl_stage_durations = {"TL_WIDE": {0: 25.0, 1: 6.0, 2: 2.5, 3: 20.0}}

    supervisor = MagicMock()
    supervisor._last_stage_change_time = {"TL_WIDE": 10.0}

    stm = StageTransitionManager(extractor, supervisor)
    current_stages = {"TL_WIDE": 1}

    # At elapsed=4.5s (> SafetyRules 4.0s, < configured 6.0s), must NOT prematurely advance
    stm.auto_advance_transitions(sim_time=14.5, current_stages=current_stages)
    assert current_stages["TL_WIDE"] == 1

    # At elapsed=6.0s, must advance to all-red clearance stage 2
    stm.auto_advance_transitions(sim_time=16.0, current_stages=current_stages)
    assert current_stages["TL_WIDE"] == 2

    # Safety floor guard: undersized yellow (e.g. 1.0s) must still honor SafetyRules floor (4.0s)
    extractor.tl_stage_durations["TL_WIDE"][1] = 1.0
    supervisor._last_stage_change_time["TL_WIDE"] = 20.0
    current_stages["TL_WIDE"] = 1
    stm.auto_advance_transitions(sim_time=22.0, current_stages=current_stages)
    assert current_stages["TL_WIDE"] == 1
    stm.auto_advance_transitions(sim_time=24.0, current_stages=current_stages)
    assert current_stages["TL_WIDE"] == 2
