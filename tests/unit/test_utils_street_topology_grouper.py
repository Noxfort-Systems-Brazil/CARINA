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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_utils_street_topology_grouper.py
# Author: Gabriel Moraes
# Date: September 2026

# CARINA - Clean Architecture & SOLID Unit Test Suite
# Tests for StreetTopologyGrouper

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from utils.street_topology_grouper import StreetTopologyGrouper


@pytest.fixture
def sample_topology_xml():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <net version="1.9">
        <junction id="J_10" type="traffic_light" />
        <junction id="J_20" type="priority" />
        <junction id="J_internal" type="internal" />
        <edge id="100" from="J_10" to="J_20" name="Avenida Central">
            <lane id="100_0" />
        </edge>
        <edge id="-100" from="J_20" to="J_10" name="Avenida Central (Volta)">
            <lane id="-100_0" />
        </edge>
        <edge id="200" from="J_20" to="J_30" name="Rua Curva">
            <lane id="200_0" />
        </edge>
        <edge id=":internal_0" from="J_10" to="J_10" />
    </net>
    """
    with tempfile.NamedTemporaryFile(suffix=".net.xml", mode="w", delete=False) as f:
        f.write(xml_content.strip())
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_extract_numeric_id():
    """Tests extracting numeric digits or hashing fallback."""
    assert StreetTopologyGrouper._extract_numeric_id("edge_12345") == 12345
    assert StreetTopologyGrouper._extract_numeric_id("J_99") == 99
    fallback_id = StreetTopologyGrouper._extract_numeric_id("no_digits_here")
    assert isinstance(fallback_id, int)
    assert fallback_id > 0


def test_parse_and_store_topology_missing_and_corrupt():
    """Tests handling of missing and corrupt XML files."""
    grouper = StreetTopologyGrouper()
    assert grouper.parse_and_store_topology("/non/existent/file.xml") is False

    with tempfile.NamedTemporaryFile(suffix=".net.xml", mode="w", delete=False) as f:
        f.write("<invalid xml")
        corrupt_path = f.name
    try:
        assert grouper.parse_and_store_topology(corrupt_path) is False
    finally:
        if os.path.exists(corrupt_path):
            os.remove(corrupt_path)


def test_parse_and_store_topology_with_mock_db(sample_topology_xml):
    """Tests dual grouping heuristics and database bulk persistence."""
    mock_db = MagicMock()
    mock_step_repo = MagicMock()
    mock_db.step_decision_repo = mock_step_repo

    grouper = StreetTopologyGrouper(db_manager=mock_db)
    success = grouper.parse_and_store_topology(sample_topology_xml)
    assert success is True

    assert mock_step_repo.bulk_save_topology_elements.called
    elements = mock_step_repo.bulk_save_topology_elements.call_args[0][0]

    # Expected: 2 intersections (J_10, J_20) + 2 streets (paired 100/-100, single 200)
    intersections = [e for e in elements if e["element_type"] == "INTERSECTION"]
    streets = [e for e in elements if e["element_type"] == "STREET"]

    assert len(intersections) == 2
    assert any(i["raw_net_id"] == "J_10" for i in intersections)

    assert len(streets) == 2
    paired_street = next(s for s in streets if s["is_bidirectional_pair"])
    assert "100" in paired_street["raw_net_id"]
    assert "-100" in paired_street["raw_net_id"]

    single_street = next(s for s in streets if not s["is_bidirectional_pair"])
    assert single_street["raw_net_id"] == "200"


def test_update_custom_name():
    """Tests updating custom name via db_manager repository."""
    mock_db = MagicMock()
    mock_step_repo = MagicMock()
    mock_step_repo.update_topology_custom_name.return_value = True
    mock_db.step_decision_repo = mock_step_repo

    grouper = StreetTopologyGrouper(db_manager=mock_db)
    result = grouper.update_custom_name("STREET", "100;-100", "Avenida Principal")
    assert result is True
    mock_step_repo.update_topology_custom_name.assert_called_once_with("STREET", "100;-100", "Avenida Principal")

    # When no db_manager is configured
    grouper_no_db = StreetTopologyGrouper()
    assert grouper_no_db.update_custom_name("STREET", "100", "Nome") is False
