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

# File: tests/unit/test_sas_data_transducer.py
# Author: Gabriel Moraes
# Date: August 13, 2026

from sas.sas_data_transducer import SASDataTransducer


def test_transduce_junction_data_with_backend_result():
    j_data = {
        "recommendation": "ADICIONAR SEMÁFORO",
        "justification": "Cruzamento de alta criticidade.",
        "data": {
            "vol_primary_val": 600.0,
            "vol_secondary_val": 200.0,
            "avg_delay": 32.5,
            "saturation_ratio": 0.85,
            "queue_p95": 10,
        },
    }

    res = SASDataTransducer.transduce_junction_data("tl_101", j_data)

    assert res["junction_id"] == "tl_101"
    assert res["recommendation"] == "ADICIONAR SEMÁFORO"
    assert res["saturation_ratio"] == 0.85
    assert res["avg_delay"] == 32.5
    assert res["total_flow"] == 800.0
    assert "W1 (Volume)" in res["warrant_label"]
    assert "W4 (Saturação)" in res["warrant_label"]


def test_transduce_junction_data_fallback_topology():
    topology = {"edges": {"e1": {"from": "102", "to": "103"}, "e2": {"from": "102", "to": "104"}}}

    res = SASDataTransducer.transduce_junction_data("tl_102", None, topology=topology)

    assert res["junction_id"] == "tl_102"
    assert res["saturation_ratio"] > 0.0
    assert res["avg_delay"] > 0.0
    assert res["total_flow"] > 0.0
    assert "Parecer Técnico SAS" in res["justification"]
