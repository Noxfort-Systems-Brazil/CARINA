# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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

# File: tests/unit/test_traffic_modular_components.py
# Author: Gabriel Moraes
# Date: September 2026

import gzip
import os
from unittest.mock import MagicMock, patch

import pytest

from src.drivers.go_pipe_transport import GoPipeTransport
from src.drivers.snmp_pdu_parser import SnmpPduParser
from src.drivers.traffic_color_logger import TrafficColorLogger
from src.drivers.traffic_map_loader import TrafficMapLoader


@pytest.mark.unit
def test_traffic_map_loader_xml_and_gz(tmp_path):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<net version="1.16" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <tlLogic id="J_TEST_LOADER" type="static" programID="0" offset="0">
        <phase duration="30" state="GGGG"/>
        <phase duration="3" state="yyyy"/>
        <phase duration="20" state="rrrr"/>
    </tlLogic>
</net>
"""
    # 1. Plain XML file
    plain_map = os.path.join(tmp_path, "map.net.xml")
    with open(plain_map, "w", encoding="utf-8") as f:
        f.write(xml_content)

    states = TrafficMapLoader.load_stage_states(intersection_id="J_TEST_LOADER", map_file=plain_map)
    assert states == {0: "GGGG", 1: "yyyy", 2: "rrrr"}

    # 2. GZipped XML file
    gz_map = os.path.join(tmp_path, "map.net.xml.gz")
    with gzip.open(gz_map, "wt", encoding="utf-8") as f:
        f.write(xml_content)

    states_gz = TrafficMapLoader.load_stage_states(intersection_id="J_TEST_LOADER", map_file=gz_map)
    assert states_gz == {0: "GGGG", 1: "yyyy", 2: "rrrr"}

    # 3. Non-existent intersection
    states_none = TrafficMapLoader.load_stage_states(intersection_id="J_NON_EXISTENT", map_file=plain_map)
    assert states_none == {}


@pytest.mark.unit
def test_traffic_color_logger(tmp_path):
    log_file_path = os.path.join(tmp_path, "carina_colors.log")

    with patch.object(TrafficColorLogger, "_get_log_filepath", return_value=log_file_path):
        active_states = {0: "GGGG", 1: "yyyy", 2: "rrrr"}

        # Log stage 0 (green)
        TrafficColorLogger.log_stage(intersection_id="J1", current_stage_idx=0, active_states=active_states)
        # Log all-red stage (stage 2)
        TrafficColorLogger.log_stage(intersection_id="J1", current_stage_idx=2, active_states=active_states)
        # Log manual override
        TrafficColorLogger.log_override(intersection_id="J1", override_type="ALERT")
        TrafficColorLogger.log_override(intersection_id="J1", override_type="DARK")

        assert os.path.exists(log_file_path)
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

        assert len(lines) == 4
        assert lines[0] == "estágio 1: GGGG"
        assert lines[1] == "estágio 0: rrrr"
        assert lines[2] == "estágio flash: flash"
        assert lines[3] == "estágio desligado: desligado"


@pytest.mark.unit
def test_snmp_pdu_parser():
    # 1. Custom TRAP| prefix
    raw_custom = b"prefix TRAP|1.3.6.1.4.1.2825.4.1|CRITICAL|Red Light Defect Error"
    parsed_custom = SnmpPduParser.parse(raw_custom)
    assert parsed_custom["trap_oid"] == "1.3.6.1.4.1.2825.4.1"
    assert parsed_custom["level"] == "CRITICAL"
    assert parsed_custom["message"] == "Red Light Defect Error"

    # 2. Raw binary ASN.1 simulation with ASCII strings
    raw_asn1 = b"\x30\x1f\x02\x01\x01\x04\x06public\xa4\x12\x06\x08Controller Conflict Detected"
    parsed_asn1 = SnmpPduParser.parse(raw_asn1)
    assert parsed_asn1["level"] == "CRITICAL"
    assert "Controller Conflict Detected" in parsed_asn1["message"]


@pytest.mark.unit
def test_go_pipe_transport_send_command_timeout():
    mock_process = MagicMock()
    mock_process.stdin = MagicMock()

    transport = GoPipeTransport()
    # Sending command to a mock that never replies on stdout should trigger timeout cleanly
    res = transport.send_command(mock_process, "ping", timeout=0.1)
    assert res.get("success") is False
    assert "Timeout" in res.get("error", "")
