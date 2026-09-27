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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_controller_stages_modular.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock, patch

import pytest

from src.controller.common_types import SignalState
from src.controller.stage_definition import StageDefinition
from src.controller.stage_derivator import derive_yellow_state
from src.controller.stage_extractor import extract_green_stages
from src.controller.stage_validator import validate_stages
from src.controller.topology_loader import IntersectionData, TopologyLoader


@pytest.mark.unit
def test_stage_definition_dataclass():
    stage = StageDefinition(state_string="GGrrGGrr", yellow_string="yyrryyrr", all_red_string="rrrrrrrr")
    assert stage.state_string == "GGrrGGrr"
    assert stage.yellow_string == "yyrryyrr"
    assert stage.all_red_string == "rrrrrrrr"
    assert SignalState.GREEN.value == "GREEN"
    assert SignalState.YELLOW.value == "YELLOW"
    assert SignalState.ALL_RED.value == "ALL_RED"


@pytest.mark.unit
def test_derive_yellow_state():
    assert derive_yellow_state("GGrrgg") == "yyrryy"
    assert derive_yellow_state("rrrr") == "rrrr"
    assert derive_yellow_state("g") == "y"
    assert derive_yellow_state("") == ""


@pytest.mark.unit
def test_extract_green_stages():
    mock_stage1 = MagicMock()
    mock_stage1.state = "GGrrGGrr"
    mock_stage2 = MagicMock()
    mock_stage2.state = "rrGGrrGG"

    stages = extract_green_stages(
        tls_id="tls_1", original_stages=[mock_stage1, mock_stage2], green_chars=frozenset({"G", "g"})
    )
    assert stages == ["GGrrGGrr", "rrGGrrGG"]


@pytest.mark.unit
def test_validate_stages_success():
    stages = [
        StageDefinition("GGrr", "yyrr", "rrrr"),
        StageDefinition("rrGG", "rryy", "rrrr"),
    ]
    assert validate_stages("tls_1", stages) is True
    assert validate_stages("tls_empty", []) is True


@pytest.mark.unit
def test_validate_stages_length_mismatch():
    stages = [
        StageDefinition("GGrr", "yyrr", "rrrr"),
        StageDefinition("rrG", "rry", "rrr"),
    ]
    assert validate_stages("tls_mismatch", stages) is False


@pytest.mark.unit
def test_validate_stages_invalid_character():
    stages = [
        StageDefinition("GGxz", "yyxz", "rrrr"),
    ]
    assert validate_stages("tls_bad_char", stages) is False


@pytest.mark.unit
def test_validate_stages_shared_greens_logged():
    stages = [
        StageDefinition("GGrr", "yyrr", "rrrr"),
        StageDefinition("Grrr", "yrrr", "rrrr"),
    ]
    # Shared movement is valid in sequential execution, should return True
    assert validate_stages("tls_shared", stages) is True


@pytest.mark.unit
def test_topology_loader_sumolib_import_error():
    loader = TopologyLoader()
    with patch.dict("sys.modules", {"sumolib": None}):
        intersections, ok = loader.load_topology("/non/existent/path.net.xml")
        assert not ok
        assert intersections == []


@pytest.mark.unit
def test_topology_loader_parse_failure():
    loader = TopologyLoader()
    mock_sumolib = MagicMock()
    mock_sumolib.net.readNet.side_effect = RuntimeError("File corrupt")
    with patch.dict("sys.modules", {"sumolib": mock_sumolib}):
        intersections, ok = loader.load_topology("corrupted.net.xml")
        assert not ok
        assert intersections == []


@pytest.mark.unit
def test_topology_loader_no_tls():
    loader = TopologyLoader()
    mock_sumolib = MagicMock()
    mock_net = MagicMock()
    mock_net.getTrafficLights.return_value = []
    mock_sumolib.net.readNet.return_value = mock_net

    with patch.dict("sys.modules", {"sumolib": mock_sumolib}):
        intersections, ok = loader.load_topology("valid.net.xml")
        assert not ok
        assert intersections == []


@pytest.mark.unit
def test_topology_loader_success_and_fallback():
    loader = TopologyLoader()
    mock_sumolib = MagicMock()
    mock_net = MagicMock()

    # TLS 1: valid
    tls1 = MagicMock()
    tls1.getID.return_value = "tls_good"
    prog1 = MagicMock()
    p1 = MagicMock()
    p1.state = "GGrr"
    p2 = MagicMock()
    p2.state = "rrGG"
    prog1.getPhases.return_value = [p1, p2]
    tls1.getPrograms.return_value = {"0": prog1}

    # TLS 2: no programs
    tls2 = MagicMock()
    tls2.getID.return_value = "tls_no_prog"
    tls2.getPrograms.return_value = {}

    # TLS 3: invalid validation -> fallback to ALL_RED
    tls3 = MagicMock()
    tls3.getID.return_value = "tls_bad"
    prog3 = MagicMock()
    bad_p = MagicMock()
    bad_p.state = "INVALID_CHAR_Z"
    prog3.getPhases.return_value = [bad_p]
    tls3.getPrograms.return_value = {"0": prog3}

    mock_net.getTrafficLights.return_value = [tls1, tls2, tls3]
    mock_sumolib.net.readNet.return_value = mock_net

    with patch.dict("sys.modules", {"sumolib": mock_sumolib}):
        intersections, ok = loader.load_topology("valid.net.xml")
        assert ok
        assert len(intersections) == 2  # tls1 and tls3 (tls2 skipped)
        assert intersections[0].tls_id == "tls_good"
        assert len(intersections[0].phase_definitions) == 2
        # tls3 falls back to ALL_RED
        assert intersections[1].tls_id == "tls_bad"
        assert intersections[1].phase_definitions[0].state_string == "r" * len("INVALID_CHAR_Z")
