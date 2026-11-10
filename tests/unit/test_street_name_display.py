# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.utils.map_processor import MapProcessor
from ui.formatting.planning_panel_presenter import PlanningPanelPresenter
from ui.loader.map_asset_loader import MapAssetLoader
from ui.managers.alias_manager import AliasManager


class DummyLocaleManager:
    def get_string(self, key, default=None, **kwargs):
        if default and kwargs:
            return default.format(**kwargs)
        return default or key


def test_map_processor_extracts_street_names():
    """Verifies that MapProcessor extracts edge names and characteristics from SUMO net."""
    mock_net = MagicMock()
    mock_net.getBBoxXY.return_value = [[0, 0], [100, 100]]

    # Edge with name
    edge1 = MagicMock()
    edge1.getID.return_value = "edge_main"
    edge1.getName.return_value = "Avenida Paulista"
    edge1.getFromNode.return_value = MagicMock(getID=lambda: "n1")
    edge1.getToNode.return_value = MagicMock(getID=lambda: "n2")
    edge1.getShape.return_value = [(0, 0), (50, 50)]
    edge1.getLaneNumber.return_value = 3
    edge1.getSpeed.return_value = 16.67
    edge1.getLength.return_value = 120.5

    # Edge without name
    edge2 = MagicMock()
    edge2.getID.return_value = "edge_unnamed"
    edge2.getName.return_value = ""
    edge2.getFromNode.return_value = MagicMock(getID=lambda: "n2")
    edge2.getToNode.return_value = MagicMock(getID=lambda: "n3")
    edge2.getShape.return_value = [(50, 50), (100, 100)]
    edge2.getLaneNumber.return_value = 1
    edge2.getSpeed.return_value = 13.89
    edge2.getLength.return_value = 75.0

    mock_net.getEdges.return_value = [edge1, edge2]
    mock_net.getNodes.return_value = []

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        output_json = tmp.name

    try:
        with patch("sumolib.net.readNet", return_value=mock_net):
            MapProcessor.extract_topology_to_json("dummy.net.xml", output_json)

        with open(output_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        edges = data.get("edges", [])
        assert len(edges) == 2

        e1 = edges[0]
        assert e1["id"] == "edge_main"
        assert e1["name"] == "Avenida Paulista"
        assert e1["lanes"] == 3
        assert e1["speed"] == 16.67
        assert e1["length"] == 120.5

        e2 = edges[1]
        assert e2["id"] == "edge_unnamed"
        assert e2["name"] == "edge_unnamed"
    finally:
        if os.path.exists(output_json):
            os.remove(output_json)


def test_alias_manager_default_and_lane_resolution(tmp_path):
    """Verifies default alias registration and smart lane resolution."""
    # Reset singleton instance for isolated test
    AliasManager._instance = None
    alias_mgr = AliasManager()
    alias_mgr.filepath = str(tmp_path / "aliases_test.json")
    alias_mgr.aliases = {}
    alias_mgr.default_aliases = {}

    alias_mgr.register_default_aliases({
        "edge_100": "Rua das Flores",
        "edge_200": "Avenida Brasil",
    })

    # Default edge resolution
    assert alias_mgr.get_alias("edge_100") == "Rua das Flores"
    assert alias_mgr.get_alias("edge_200") == "Avenida Brasil"
    assert alias_mgr.get_alias("edge_999") == "edge_999"

    # Lane resolution: <edge_id>_<lane_idx>
    assert alias_mgr.get_alias("edge_100_0") == "Rua das Flores [Faixa 0]"
    assert alias_mgr.get_alias("edge_100_1") == "Rua das Flores [Faixa 1]"
    assert alias_mgr.get_alias("edge_999_0") == "edge_999_0"

    # User custom alias overrides default
    alias_mgr.set_alias("edge_100", "Rua das Orquídeas")
    assert alias_mgr.get_alias("edge_100") == "Rua das Orquídeas"
    assert alias_mgr.get_alias("edge_100_0") == "Rua das Orquídeas [Faixa 0]"

    # Clearing custom alias restores default
    alias_mgr.set_alias("edge_100", "")
    assert alias_mgr.get_alias("edge_100") == "Rua das Flores"


def test_planning_panel_presenter_uses_street_name():
    """Verifies that PlanningPanelPresenter uses the friendly street name instead of technical ID."""
    AliasManager._instance = None
    alias_mgr = AliasManager()
    alias_mgr.register_default_alias("-103342059#0", "Rua Coronel Luiz Pinheiro de Melo")

    dto = PlanningPanelPresenter.format_edge_details(
        "-103342059#0",
        {"name": "Rua Coronel Luiz Pinheiro de Melo", "numLanes": 2, "speed": 13.89},
    )

    assert dto.node_id == "Via: Rua Coronel Luiz Pinheiro de Melo"
    assert "Rua Coronel Luiz Pinheiro de Melo" in dto.justification_str


def test_street_info_widget_displays_friendly_street_name():
    """Verifies that StreetInfoWidget displays the friendly name in the input field."""
    from ui.widgets.street_info_widget import StreetInfoWidget

    lm = DummyLocaleManager()
    AliasManager._instance = None
    alias_mgr = AliasManager()
    alias_mgr.register_default_alias("edge_77", "Rua 7 de Setembro")

    widget = StreetInfoWidget(locale_manager=lm)
    widget.update_and_show("edge_77", {"name": "Rua 7 de Setembro", "congestion": 0.25, "speed": 45.0})

    assert widget.street_id_text.value == "Rua 7 de Setembro"
    assert widget._current_street_id == "edge_77"
