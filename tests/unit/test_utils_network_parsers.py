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

# File: tests/unit/test_utils_network_parsers.py
# Author: Gabriel Moraes
# Date: September 2026

# CARINA - Clean Architecture & SOLID Unit Test Suite
# Tests for network_parser and network_topology_parser

import gzip
import os
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock

import pytest

from utils.network_parser import build_lane_to_edge_map, build_structural_neighborhood_map
from utils.network_topology_parser import NetworkTopologyParser


@pytest.fixture
def sample_net_xml_path():
    """Generates a temporary SUMO network XML file with nodes, edges and lanes."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <net version="1.9" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <junction id="J1" type="traffic_light" x="0.0" y="0.0" />
        <junction id="J2" type="traffic_light" x="100.0" y="0.0" />
        <junction id="J3" type="dead_end" x="200.0" y="0.0" />
        <edge id="E1" from="J1" to="J2" priority="1">
            <lane id="E1_0" index="0" speed="13.89" length="100.0" />
            <lane id="E1_1" index="1" speed="13.89" length="100.0" />
        </edge>
        <edge id="E2" from="J2" to="J3" priority="1">
            <lane id="E2_0" index="0" speed="16.67" length="95.5" />
        </edge>
        <edge id=":internal_0" from="J1" to="J1">
            <lane id=":internal_0_0" index="0" speed="5.0" length="5.0" />
        </edge>
    </net>
    """
    with tempfile.NamedTemporaryFile(suffix=".net.xml", mode="w", delete=False) as f:
        f.write(xml_content.strip())
        path = f.name

    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def sample_net_gz_path(sample_net_xml_path):
    """Generates a compressed .gz network XML file."""
    gz_path = sample_net_xml_path + ".gz"
    with open(sample_net_xml_path, "rb") as f_in:
        with gzip.open(gz_path, "wb") as f_out:
            f_out.writelines(f_in)
    yield gz_path
    if os.path.exists(gz_path):
        os.remove(gz_path)


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, **kwargs: f"[{key}]"
    return lm


def test_build_lane_to_edge_map_standard_and_gz(sample_net_xml_path, sample_net_gz_path, mock_locale):
    """Tests building lane-to-edge dictionary from normal and gzipped net files."""
    lane_map = build_lane_to_edge_map(sample_net_xml_path, mock_locale)
    assert lane_map["E1_0"] == "E1"
    assert lane_map["E1_1"] == "E1"
    assert lane_map["E2_0"] == "E2"
    assert ":internal_0_0" not in lane_map

    lane_map_gz = build_lane_to_edge_map(sample_net_gz_path, mock_locale)
    assert lane_map_gz == lane_map


def test_build_lane_to_edge_map_missing_file(mock_locale):
    """Verifies graceful handling of non-existent files."""
    lane_map = build_lane_to_edge_map("/non/existent/path.xml", mock_locale)
    assert lane_map == {}


def test_build_structural_neighborhood_map(sample_net_xml_path, sample_net_gz_path, mock_locale):
    """Tests building BFS structural neighborhood maps across intersections."""
    neighborhood = build_structural_neighborhood_map(sample_net_xml_path, ["J1", "J2"], mock_locale)
    assert "J1" in neighborhood
    assert "J2" in neighborhood["J1"]

    neighborhood_gz = build_structural_neighborhood_map(sample_net_gz_path, ["J1", "J2"], mock_locale)
    assert "J2" in neighborhood_gz["J1"]


def test_network_topology_parser(sample_net_xml_path, mock_locale):
    """Tests extracting junction types and incoming edges with speeds and lengths."""
    parser = NetworkTopologyParser(mock_locale)
    j_types, incoming_edges = parser.build(sample_net_xml_path)

    assert j_types.get("J1") == "traffic_light"
    assert j_types.get("J2") == "traffic_light"
    assert "E1" in incoming_edges["J2"]
    assert incoming_edges["J2"]["E1"]["speed_limit"] == 13.89
    assert incoming_edges["J2"]["E1"]["length"] == 100.0
    assert incoming_edges["J2"]["E1"]["lanes"] == ["E1_0", "E1_1"]
