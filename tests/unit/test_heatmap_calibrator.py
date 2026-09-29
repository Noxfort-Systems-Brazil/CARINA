# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: tests/unit/test_heatmap_calibrator.py
# Author: Gabriel Moraes
# Date: September 2026

import random

import pytest

from sas.heatmap_calibrator import HeatmapCalibrator


def test_heatmap_calibrator_not_enough_data():
    calibrator = HeatmapCalibrator()
    # 99 points is less than the required minimum of 100
    points = [{"occupancy": 0.5, "waiting_time": 10.0, "flow": 2.0, "bad_events": 1} for _ in range(99)]
    res = calibrator.calibrate(points)
    assert res is None


def test_heatmap_calibrator_success():
    calibrator = HeatmapCalibrator()
    if not calibrator.is_available():
        pytest.skip("Pandas/Sklearn not available in this environment")

    points = []
    for _ in range(110):
        points.append(
            {
                "occupancy": random.uniform(0.1, 0.9),
                "waiting_time": random.uniform(5.0, 50.0),
                "flow": random.uniform(1.0, 10.0),
                "bad_events": random.uniform(0.0, 5.0),
            }
        )

    res = calibrator.calibrate(points)
    assert res is not None
    assert "weight_occupancy" in res
    assert "weight_waiting_time" in res
    assert "weight_flow" in res
    assert res["weight_occupancy"] >= 0.0
    assert res["weight_waiting_time"] >= 0.0
    assert res["weight_flow"] <= 0.0
