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

# File: tests/unit/test_planning_panel_presenter.py
# Author: Gabriel Moraes
# Date: August 13, 2026

import pytest

from ui.formatting.planning_panel_presenter import PlanningPanelPresenter


def test_compute_statistics_empty():
    stats = PlanningPanelPresenter.compute_statistics({})
    assert stats.total == 0
    assert stats.add_count == 0
    assert stats.remove_count == 0
    assert stats.keep_count == 0
    assert stats.no_signal_count == 0


def test_compute_statistics_counts():
    raw_data = {
        "j1": {"recommendation": "Adicionar Semáforo"},
        "j2": {"recommendation": "Remover Semáforo"},
        "j3": {"recommendation": "Manter Semáforo"},
        "j4": {"recommendation": "Manter Interseção Não Sinalizada"},
        "j5": {"recommendation": "Adicionar Sinalização"},
    }
    stats = PlanningPanelPresenter.compute_statistics(raw_data)
    assert stats.total == 5
    assert stats.add_count == 2
    assert stats.remove_count == 1
    assert stats.keep_count == 1
    assert stats.no_signal_count == 1


def test_format_node_details_valid():
    node_data = {
        "recommendation": "Adicionar Semáforo",
        "justification": "Warrant de volume atingido.",
        "data": {
            "vol_primary_val": 1000.0,
            "vol_secondary_val": 450.0,
            "saturation_ratio": 0.88,
            "avg_delay": 32.5,
            "queue_p95": 12,
        },
    }
    dto = PlanningPanelPresenter.format_node_details("j1", node_data)
    assert dto.node_id == "j1"
    assert dto.rec_label == "ADICIONAR SEMÁFORO"
    assert dto.saturation_str == "X = 0.88"
    assert dto.delay_str == "32.5 s"
    assert dto.flow_str == "1450 v/h"
    assert "W1 (Volume)" in dto.warrant_str
    assert dto.justification_str == "Warrant de volume atingido."


def test_format_node_details_none():
    dto = PlanningPanelPresenter.format_node_details("unknown_node", None)
    assert dto.node_id == "unknown_node"
    assert dto.rec_label == "MANTER SEMÁFORO"
    assert dto.saturation_str.startswith("X =")
    assert dto.delay_str.endswith("s")


def test_format_edge_details():
    edge_data = {"name": "Av. Brasil", "numLanes": 3, "maxSpeed": 60, "flow": 1200}
    dto = PlanningPanelPresenter.format_edge_details("e1", edge_data)
    assert dto.node_id == "Via: Av. Brasil"
    assert dto.rec_label == "VIA / RUA SELECIONADA"
    assert dto.saturation_str == "3 faixa(s)"
    assert dto.delay_str == "60 km/h"
    assert dto.flow_str == "1200 v/h"
