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

# File: tests/unit/test_planning_architecture.py
# Author: Gabriel Moraes
# Date: 2026-08-13

from unittest.mock import MagicMock, patch

import flet as ft
import flet.canvas as cv
import pytest

from ui.controllers.planning_controller import PlanningController
from ui.renderers.planning_map_renderer import PlanningMapRenderer
from ui.widgets.planning_command_bar_widget import PlanningCommandBarWidget
from ui.widgets.planning_legend_widget import PlanningLegendWidget


def test_planning_legend_widget_initialization_and_translation():
    mock_lm = MagicMock()
    mock_lm.get_string.side_effect = lambda key, default=None: f"Mock_{key}"

    legend = PlanningLegendWidget(locale_manager=mock_lm)

    assert legend.legend_title.value == "Mock_planning_view.legend_title"
    assert legend.legend_tl_keep.value == "Mock_planning_view.legend_tl_keep"
    assert legend.legend_tl_remove.value == "Mock_planning_view.legend_tl_remove"
    assert legend.legend_tl_add.value == "Mock_planning_view.legend_tl_add"


def test_planning_command_bar_widget_status_and_translation():
    mock_lm = MagicMock()
    mock_lm.get_string.side_effect = lambda key, default=None: f"Mock_{key}"

    bar = PlanningCommandBarWidget(locale_manager=mock_lm)
    bar.set_status("Test Status", italic=True, color=ft.Colors.GREEN)

    assert bar.status_text.value == "Test Status"
    assert bar.status_text.italic is True
    assert bar.status_text.color == ft.Colors.GREEN

    bar.update_translations(mock_lm, is_analyzing=False)
    assert bar.analyze_button.text == "Mock_planning_view.analyze_button"
    assert bar.save_report_button.text == "Mock_planning_view.generate_report_button"


def test_planning_controller_trigger_analysis():
    mock_lm = MagicMock()
    mock_control_client = MagicMock()
    mock_client = MagicMock()

    controller = PlanningController(locale_manager=mock_lm, control_client=mock_control_client, client=mock_client)

    t0 = controller.trigger_analysis()

    assert controller.is_analyzing is True
    assert controller.last_report_content is None
    assert controller.last_scenario_dir is None
    mock_control_client.trigger_analysis.assert_called_once()
    mock_client.start_fetching_latest_analysis.assert_called_once_with(trigger_time=t0)


def test_planning_controller_process_analysis_response_success():
    mock_lm = MagicMock()
    controller = PlanningController(locale_manager=mock_lm)

    response = {
        "status": "success",
        "report_content": "Laudo Teste",
        "scenario_dir": "/tmp/test",
        "analysis_results": {"tl_01": "ADD"},
        "significant_change": True,
    }

    res = controller.process_analysis_response(response)

    assert controller.is_analyzing is False
    assert controller.last_report_content == "Laudo Teste"
    assert controller.last_scenario_dir == "/tmp/test"
    assert res["status"] == "success"
    assert res["analysis_results"] == {"tl_01": "ADD"}


def test_planning_controller_process_analysis_response_error():
    mock_lm = MagicMock()
    controller = PlanningController(locale_manager=mock_lm)

    response = {"status": "error", "message": "Erro de conexão"}

    res = controller.process_analysis_response(response)

    assert controller.is_analyzing is False
    assert controller.last_report_content is None
    assert res["status"] == "error"
    assert res["message"] == "Erro de conexão"


@patch("ui.controllers.planning_controller.PlanningExportHandler.export_report")
def test_planning_controller_export_report(mock_export):
    mock_export.return_value = (True, "Relatório salvo com sucesso")
    mock_lm = MagicMock()
    controller = PlanningController(locale_manager=mock_lm)
    controller.last_report_content = "Conteúdo do laudo"

    mock_page = MagicMock()
    success, msg = controller.export_report(page=mock_page, save_path="/tmp/report.docx")

    assert success is True
    assert msg == "Relatório salvo com sucesso"
    mock_export.assert_called_once()


def test_planning_map_renderer_draws_orange_nodes_for_traffic_lights_and_junctions():
    renderer = PlanningMapRenderer(base_width=1200, base_height=800)
    assert renderer.hit_radius == 35.0
    assert renderer.junction_color == ft.Colors.ORANGE_600

    topology = {
        "bounds": {"min_x": 0, "max_x": 100, "min_y": 0, "max_y": 100},
        "nodes": {
            "node_tl": {"id": "node_tl", "x": 50, "y": 50, "type": "traffic_light"},
            "node_junc": {"id": "node_junc", "x": 20, "y": 20, "type": "priority"},
            "node_dead": {"id": "node_dead", "x": 0, "y": 0, "type": "dead_end"},
        },
        "edges": [
            {"id": "e1", "from": "node_tl", "to": "node_junc", "shape": [[50, 50], [20, 20]]},
            {"id": "e2", "from": "node_junc", "to": "node_dead", "shape": [[20, 20], [0, 0]]},
            {"id": "e3", "from": "node_tl", "to": "node_dead", "shape": [[50, 50], [0, 0]]},
        ],
    }

    renderer.calculate_initial_fit(topology)

    canvas_static = cv.Canvas(shapes=[])
    canvas_dynamic = cv.Canvas(shapes=[])
    drawn_nodes_cache = []
    drawn_edges_cache = []

    renderer.draw_topology(
        topology=topology,
        canvas_static=canvas_static,
        canvas_dynamic=canvas_dynamic,
        drawn_nodes_cache=drawn_nodes_cache,
        drawn_edges_cache=drawn_edges_cache,
    )

    # Both node_tl (traffic light) and node_junc (regular junction) should be cached
    cached_ids = [n["id"] for n in drawn_nodes_cache]
    assert "node_tl" in cached_ids
    assert "node_junc" in cached_ids
    assert "node_dead" not in cached_ids

    # Verify that orange circles are drawn for BOTH node_tl and node_junc
    orange_circles = [
        s for s in canvas_dynamic.shapes if isinstance(s, cv.Circle) and s.paint.color == ft.Colors.ORANGE_600
    ]
    # There must be at least 2 orange circles (one for node_tl and one for node_junc)
    assert len(orange_circles) >= 2

    # Verify that traffic light icon shapes (Rect + Circles) are also drawn for node_tl
    tl_rects = [s for s in canvas_dynamic.shapes if isinstance(s, cv.Rect) and s.paint.color == ft.Colors.BLUE_800]
    assert len(tl_rects) == 1
