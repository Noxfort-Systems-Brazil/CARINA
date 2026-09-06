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

# File: tests/unit/test_planning_view.py
# Author: Gabriel Moraes
# Date: 2026-07-10

from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from ui.views.planning_view import PlanningView


@patch("ui.views.planning_view.InfrastructureClient")
@patch("ui.views.planning_view.InteractiveMap")
def test_planning_view_process_analysis_response_no_change(mock_map, mock_infra_client):
    """
    Verifies that when an analysis response is received with no significant change,
    the save_report_button is enabled and status text is updated appropriately.
    """
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None: f"Mock_{key}"

    view = PlanningView(locale_manager=mock_locale_manager)
    view.page = MagicMock()
    view.update = MagicMock()

    response = {
        "status": "success",
        "report_content": "Mock report content",
        "analysis_results": {"node1": "recommendation"},
        "significant_change": False,
    }

    view._process_analysis_response(response)

    # Assert report content is stored
    assert view.last_report_content == "Mock report content"

    # Assert save report button is enabled
    assert view.save_report_button.disabled is False
    assert view.status_text.value == "Mock_planning_view.status_loaded_no_change"


@patch("ui.views.planning_view.InfrastructureClient")
@patch("ui.views.planning_view.InteractiveMap")
def test_planning_view_save_report_click_triggers_save(mock_map, mock_infra_client):
    """
    Verifies that clicking save report triggers the file picker.
    """
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None: f"Mock_{key}"

    view = PlanningView(locale_manager=mock_locale_manager)
    view.page = MagicMock()
    view.update = MagicMock()
    view.file_picker = MagicMock()

    # Mocking last report content
    view.last_report_content = "Mock report content"

    view._save_report_click(None)

    # Assert file picker save_file was triggered
    view.file_picker.save_file.assert_called_once()


@patch("ui.views.planning_view.InfrastructureClient")
@patch("ui.views.planning_view.InteractiveMap")
def test_planning_view_interactive_node_selection(mock_map_cls, mock_infra_client):
    """
    Verifies that selecting a node on the map updates the side panel details card
    and sets the highlighted selection on the map widget.
    """
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None: f"Mock_{key}"

    view = PlanningView(locale_manager=mock_locale_manager)
    view.page = MagicMock()
    view.update = MagicMock()

    analysis_data = {
        "tl_101": {
            "recommendation": "Adicionar Semáforo",
            "justification": "Volume de tráfego excede o limite mínimo CONTRAN.",
            "data": {"saturation_ratio": 0.92, "average_delay": 45.3},
        }
    }
    view._process_analysis_response(
        {"status": "success", "report_content": "Content", "analysis_results": analysis_data}
    )

    # Simulate node tap
    view._handle_node_click("tl_101")

    # Assert node details panel updated
    assert view.planning_control_panel.selected_node_id == "tl_101"
    assert view.planning_control_panel.details_card.visible is True
    assert view.planning_control_panel.details_card.node_title.value == "Nó: tl_101"
    assert "ADICIONAR SEMÁFORO" in view.planning_control_panel.details_card.rec_badge.content.value
    assert view.map_widget.set_selected_node.assert_called_with("tl_101") is None


@patch("ui.views.planning_view.InfrastructureClient")
@patch("ui.views.planning_view.InteractiveMap")
def test_planning_view_recommendation_filtering(mock_map_cls, mock_infra_client):
    """
    Verifies that changing recommendation filter chips updates the map filter.
    """
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None: f"Mock_{key}"

    view = PlanningView(locale_manager=mock_locale_manager)
    view.page = MagicMock()

    view._handle_filter_change("ADD")
    view.map_widget.set_filter.assert_called_with("ADD")


@patch("ui.views.planning_view.InfrastructureClient")
@patch("ui.views.planning_view.InteractiveMap")
def test_planning_view_interactive_edge_selection(mock_map_cls, mock_infra_client):
    """
    Verifies that selecting a street edge updates both the map edge highlight and side panel.
    """
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None: f"Mock_{key}"

    view = PlanningView(locale_manager=mock_locale_manager)
    view.page = MagicMock()

    edge_data = {"name": "Avenida Central", "numLanes": 2}
    view._handle_edge_click("edge_42", edge_data)

    assert view.planning_control_panel.details_card.visible is True
    assert view.planning_control_panel.details_card.node_title.value == "Nó: Via: Avenida Central"
    assert view.map_widget.set_selected_edge.assert_called_with("edge_42") is None
