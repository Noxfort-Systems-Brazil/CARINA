# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: tests/unit/test_volume_warrants.py
# Author: Gabriel Moraes
# Date: September 2026

from analysis.warrant_strategies import VolumeWarrant


def test_volume_warrant_mutcd_tables():
    warrant = VolumeWarrant()

    # 1. 1 lane major, 1 lane minor, standard speed (13.89 m/s = 50 km/h)
    primary_edges = {"edge1": [{"density": 10.0, "mean_speed": 13.89, "num_lanes": 1, "speed_limit": 13.89}]}
    secondary_edges = {"edge2": [{"density": 5.0, "mean_speed": 13.89, "num_lanes": 1, "speed_limit": 13.89}]}

    res = warrant.evaluate({}, primary_edges, secondary_edges, {})
    assert res["met"] is True
    assert res["threshold_primary"] == 500
    assert res["threshold_secondary"] == 150

    # 2. 2 lanes major, 2 lanes minor, standard speed
    primary_edges_2 = {"edge1": [{"density": 10.0, "mean_speed": 13.89, "num_lanes": 2, "speed_limit": 13.89}]}
    secondary_edges_2 = {"edge2": [{"density": 5.0, "mean_speed": 13.89, "num_lanes": 2, "speed_limit": 13.89}]}
    res = warrant.evaluate({}, primary_edges_2, secondary_edges_2, {})
    assert res["threshold_primary"] == 600
    assert res["threshold_secondary"] == 200

    # 3. High speed limit (20 m/s > 19.44 m/s ≈ 72 km/h)
    primary_edges_high = {"edge1": [{"density": 10.0, "mean_speed": 20.0, "num_lanes": 1, "speed_limit": 20.0}]}
    secondary_edges_high = {"edge2": [{"density": 5.0, "mean_speed": 20.0, "num_lanes": 1, "speed_limit": 20.0}]}
    res = warrant.evaluate({}, primary_edges_high, secondary_edges_high, {})
    assert res["threshold_primary"] == 350
    assert res["threshold_secondary"] == 105
