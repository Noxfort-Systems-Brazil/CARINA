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

# File: tests/unit/test_sds_processors_and_buffers.py
# Author: Gabriel Moraes
# Date: September 2026

# CARINA - Clean Architecture & SOLID Unit Test Suite
# Tests for SDS StreetMetricsCalculator, DataBufferManager and WeightsManager

import configparser
import os
import tempfile

import pytest

from sds.data_buffer_manager import DataBufferManager
from sds.street_metrics_calculator import StreetMetricsCalculator
from sds.weights_manager import WeightsManager


def test_street_metrics_calculator_aggregation():
    """Tests street metric calculation and occupancy aggregation strategies (mean vs max)."""
    calc = StreetMetricsCalculator()

    raw_data = {
        "sim_step_length": 1.0,
        "lane_occupancies": {"lane1_0": 0.2, "lane1_1": 0.6},
        "lane_waiting_time": {"lane1_0": 10.0, "lane1_1": 20.0},
        "lane_vehicle_ids": {"lane1_0": ["v1"], "lane1_1": ["v2", "v3"]},
        "edge_mean_speeds": {"edge1": 10.0},
    }
    lane_to_edge = {"lane1_0": "edge1", "lane1_1": "edge1"}
    edge_to_lanes = {"edge1": ["lane1_0", "lane1_1"]}
    weights = {"weight_occupancy": 1.0, "weight_waiting_time": 1.0, "weight_flow": -0.5}

    # Test max strategy
    data_max = calc.calculate_street_data(raw_data, lane_to_edge, edge_to_lanes, weights, "max")
    assert "edge1" in data_max
    assert data_max["edge1"]["vehicles"] == 3
    assert data_max["edge1"]["speed"] == 36.0  # 10.0 m/s * 3.6

    # Test flow calculation with departed vehicle
    raw_step2 = {
        "sim_step_length": 1.0,
        "lane_occupancies": {"lane1_0": 0.0, "lane1_1": 0.3},
        "lane_waiting_time": {"lane1_0": 0.0, "lane1_1": 5.0},
        "lane_vehicle_ids": {"lane1_0": [], "lane1_1": ["v2"]},  # v1 departed, v3 departed
        "edge_mean_speeds": {"edge1": 12.0},
    }
    data_step2 = calc.calculate_street_data(raw_step2, lane_to_edge, edge_to_lanes, weights, "mean")
    assert data_step2["edge1"]["vehicles"] == 1
    assert data_step2["edge1"]["flow"] == 120  # 2 departed * 60 / 1.0


def test_data_buffer_manager_lifecycle():
    """Tests sample ingestion, time window trimming, stats and reset in DataBufferManager."""
    buf_mgr = DataBufferManager()
    assert buf_mgr.get_stats()["samples_collected"] == 0

    # Ingest samples
    sample = {"edge_A": {"occupancy": 0.5, "speed": 15.0, "queue": 2.0}}
    buf_mgr.add_sample(timestamp=100.0, edge_data=sample)

    assert buf_mgr.get_stats()["samples_collected"] == 1
    data = buf_mgr.get_buffer_data()
    assert "edge_A" in data
    assert data["edge_A"]["occ"] == [0.5]
    assert data["edge_A"]["spd"] == [15.0]

    # Ingest another sample at 200.0 and trim window of 60s
    buf_mgr.add_sample(timestamp=200.0, edge_data={"edge_B": {"occupancy": 0.1}})
    buf_mgr.trim_old_data(current_time=200.0, window=60.0)

    # edge_A timestamp (100.0) is older than 200 - 60 = 140.0, so it must be trimmed
    data_trimmed = buf_mgr.get_buffer_data()
    assert "edge_A" not in data_trimmed
    assert "edge_B" in data_trimmed

    # Reset
    buf_mgr.reset()
    assert buf_mgr.get_stats()["samples_collected"] == 0
    assert len(buf_mgr.get_buffer_data()) == 0


def test_weights_manager_loading_and_fallbacks():
    """Tests WeightsManager configuration parsing and fallback handling."""
    config = configparser.ConfigParser()
    config["HEATMAP_SCALING"] = {
        "weight_occupancy": "2.5",
        "weight_waiting_time": "3.0",
        "weight_flow": "-1.0",
        "lane_aggregation_strategy": "mean",
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        wm = WeightsManager(config, project_root=tmp_dir)
        weights = wm.get_weights()
        assert weights["weight_occupancy"] == 2.5
        assert weights["weight_waiting_time"] == 3.0
        assert weights["weight_flow"] == -1.0
        assert wm.get_aggregation_strategy() == "mean"

        # Test fallback with empty config
        empty_config = configparser.ConfigParser()
        wm_fallback = WeightsManager(empty_config, project_root=tmp_dir)
        fb_weights = wm_fallback.get_weights()
        assert fb_weights["weight_occupancy"] == 1.0
        assert fb_weights["weight_waiting_time"] == 1.5
