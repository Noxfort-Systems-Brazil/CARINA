# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_traffic_light_driver.py
# Author: Gabriel Moraes
# Date: September 2026

import os
from unittest.mock import MagicMock, patch

import pytest

from src.drivers.traffic_light_driver import TrafficLightDriver


@pytest.mark.unit
def test_traffic_light_driver_log_carina_colors(tmp_path):
    # Setup dummy driver
    driver = TrafficLightDriver(intersection_id="J1", ip_address="127.0.0.1", port=161, green_stages=[0, 2])
    driver.is_connected = True
    driver.hardware_driver = MagicMock()

    stage_codes = {0: "GgOrrOGGO", 2: "yyyrrrGyy"}

    # Redirect logging path to tmp_path/carina_colors.log
    log_file_path = os.path.join(tmp_path, "carina_colors.log")

    original_join = os.path.join

    with patch("os.path.abspath") as mock_abspath, patch("os.path.join") as mock_join:
        # We want to intercept os.path.join(project_root, "carina_colors.log")
        def side_effect_join(*args):
            if len(args) >= 2 and args[-1] == "carina_colors.log":
                return log_file_path
            return original_join(*args)

        mock_abspath.side_effect = lambda x: x
        mock_join.side_effect = side_effect_join

        # 1. Test stage index 0
        driver.log_carina_colors(current_stage_idx=0, stage_codes=stage_codes)

        # Verify content
        assert os.path.exists(log_file_path)
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == "estágio 1: GgOrrOGGO"

        # 2. Test stage index 2
        driver.log_carina_colors(current_stage_idx=2, stage_codes={0: "GgOrrOGGO", 2: "yyyrrrGyy"})

        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert lines[1].strip() == "estágio 3: yyyrrrGyy"

        # 3. Test all-red stage index 4
        driver.log_carina_colors(current_stage_idx=4, stage_codes={4: "rrrrrrrrr"})
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 3
        assert lines[2].strip() == "estágio 0: rrrrrrrrr"


@pytest.mark.unit
def test_traffic_light_driver_load_states_from_map(tmp_path):
    # Create a dummy net.xml file
    net_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<net version="1.16" junctionCornerDetail="5" limitTurnSpeed="5.50" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/net_file.xsd">
    <tlLogic id="J_MAP_TEST" type="static" programID="0" offset="0">
        <phase duration="42" state="GgOrrOGGO_MAP"/>
        <phase duration="3" state="yyyrrrGyy_MAP"/>
    </tlLogic>
</net>
"""
    map_file_path = os.path.join(tmp_path, "test_map.net.xml")
    with open(map_file_path, "w", encoding="utf-8") as f:
        f.write(net_xml_content)

    with patch("src.controller.map_discoverer.MapTopologyDiscoverer.get_map_file", return_value=map_file_path):
        driver = TrafficLightDriver(intersection_id="J_MAP_TEST", ip_address="127.0.0.1", port=161, green_stages=[0, 1])

        # Verify that it loaded states correctly from the map file
        assert driver.stage_states == {0: "GgOrrOGGO_MAP", 1: "yyyrrrGyy_MAP"}


@pytest.mark.unit
def test_traffic_light_driver_shutdown_calls_release_control():
    with patch.object(TrafficLightDriver, "_connect"):
        driver = TrafficLightDriver(
            intersection_id="J_SHUTDOWN_TEST", ip_address="127.0.0.1", port=161, green_stages=[0, 1]
        )
        mock_hw = MagicMock()
        driver.hardware_driver = mock_hw
        driver.is_connected = True

        driver.shutdown()

        mock_hw.release_control.assert_called_once()
        mock_hw.stop_heartbeat.assert_called_once()
        mock_hw.shutdown.assert_called_once()
        assert driver.is_connected is False
        assert driver.hardware_driver is None


@pytest.mark.unit
def test_go_traffic_driver_proxy_release_control():
    from src.drivers.go_driver_proxy import GoTrafficDriverProxy

    mock_client = MagicMock()
    mock_client.apply_action.return_value = True

    proxy = GoTrafficDriverProxy(
        ip_address="127.0.0.1",
        port=161,
        intersection_id="J_PROXY",
        client=mock_client,
    )

    result = proxy.release_control()
    assert result is True
    mock_client.apply_action.assert_called_once_with("J_PROXY", {"action_type": "release_hold"})


@pytest.mark.unit
def test_go_traffic_driver_proxy_apply_decision():
    from src.drivers.go_driver_proxy import GoTrafficDriverProxy

    mock_client = MagicMock()
    mock_client.apply_decision.return_value = True

    proxy = GoTrafficDriverProxy(
        ip_address="127.0.0.1",
        port=161,
        intersection_id="J_PROXY_DECISION",
        client=mock_client,
    )

    result = proxy.apply_decision("ADVANCE")
    assert result is True
    mock_client.apply_decision.assert_called_once_with("J_PROXY_DECISION", "ADVANCE")
