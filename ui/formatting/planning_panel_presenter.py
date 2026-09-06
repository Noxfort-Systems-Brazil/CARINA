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

# File: ui/formatting/planning_panel_presenter.py
# Author: Gabriel Moraes
# Date: August 13, 2026

from dataclasses import dataclass
from typing import Any, Dict, Optional

import flet as ft


@dataclass
class PlanningStatsDTO:
    total: int = 0
    add_count: int = 0
    remove_count: int = 0
    keep_count: int = 0
    no_signal_count: int = 0


@dataclass
class NodeDetailsDTO:
    node_id: str
    rec_label: str
    rec_bg_color: str
    saturation_str: str
    delay_str: str
    flow_str: str
    warrant_str: str
    justification_str: str


@dataclass
class RecommendationStyle:
    label: str
    bg_color: str


class PlanningPanelPresenter:
    """
    Decoupled Data Presenter & Normalizer for Planning UI Components.
    Single Responsibility: Data parsing, statistics calculation, and string formatting.
    Open/Closed: Extensible recommendation style mappings.
    """

    RECOMMENDATION_STYLES = {
        "ADD": RecommendationStyle(label="ADICIONAR SEMÁFORO", bg_color=ft.Colors.GREEN_700),
        "REMOVE": RecommendationStyle(label="REMOVER SEMÁFORO", bg_color=ft.Colors.RED_700),
        "UNSIGNALIZED": RecommendationStyle(label="NÃO SINALIZADO", bg_color=ft.Colors.ORANGE_700),
        "KEEP": RecommendationStyle(label="MANTER SEMÁFORO", bg_color=ft.Colors.BLUE_700),
        "UNKNOWN": RecommendationStyle(label="SEM DADOS DE LAUDO", bg_color=ft.Colors.GREY_700),
    }

    @classmethod
    def compute_statistics(cls, analysis_results: Dict[str, Any]) -> PlanningStatsDTO:
        """Parses raw analysis results dictionary and returns structured network statistics."""
        if not analysis_results:
            return PlanningStatsDTO()

        total = len(analysis_results)
        add_c = 0
        remove_c = 0
        keep_c = 0
        no_sig_c = 0

        for j_id, j_data in analysis_results.items():
            if isinstance(j_data, dict):
                rec_str = str(j_data.get("recommendation", "")).lower()
            else:
                rec_str = str(j_data).lower()

            if "adicionar" in rec_str or "add" in rec_str:
                add_c += 1
            elif "remover" in rec_str or "remove" in rec_str:
                remove_c += 1
            elif "não sinalizad" in rec_str or "no_signal" in rec_str or "unsignalized" in rec_str:
                no_sig_c += 1
            else:
                keep_c += 1

        return PlanningStatsDTO(
            total=total, add_count=add_c, remove_count=remove_c, keep_count=keep_c, no_signal_count=no_sig_c
        )

    @classmethod
    def format_node_details(
        cls, node_id: str, node_data: Optional[Dict[str, Any]], topology: Optional[Dict[str, Any]] = None
    ) -> NodeDetailsDTO:
        """Formats junction node data using SASDataTransducer into a clean, display-ready DTO."""
        from sas.sas_data_transducer import SASDataTransducer

        transduced = SASDataTransducer.transduce_junction_data(
            junction_id=node_id, junction_data=node_data, topology=topology
        )

        rec_str = transduced["recommendation"]
        rec_lower = rec_str.lower()

        if "adicionar" in rec_lower or "add" in rec_lower:
            style_key = "ADD"
        elif "remover" in rec_lower or "remove" in rec_lower:
            style_key = "REMOVE"
        elif "não sinalizad" in rec_lower or "unsignalized" in rec_lower:
            style_key = "UNSIGNALIZED"
        else:
            style_key = "KEEP"

        style = cls.RECOMMENDATION_STYLES.get(style_key, cls.RECOMMENDATION_STYLES["KEEP"])

        sat_str = f"X = {transduced['saturation_ratio']:.2f}"
        delay_str = f"{transduced['avg_delay']:.1f} s"
        flow_str = f"{int(transduced['total_flow'])} v/h"
        warrant_str = transduced["warrant_label"]
        just_str = transduced["justification"]

        return NodeDetailsDTO(
            node_id=node_id,
            rec_label=style.label,
            rec_bg_color=style.bg_color,
            saturation_str=sat_str,
            delay_str=delay_str,
            flow_str=flow_str,
            warrant_str=warrant_str,
            justification_str=just_str,
        )

    @classmethod
    def format_edge_details(cls, edge_id: str, edge_data: Optional[Dict[str, Any]] = None) -> NodeDetailsDTO:
        """Formats street/via edge data into a display-ready Data Transfer Object."""
        name = edge_id
        lanes = "1"
        speed = "60 km/h"
        flow = "Normal"
        just = "Trecho viário monitorado pela malha tática."

        if isinstance(edge_data, dict):
            name = edge_data.get("name", edge_id) or edge_id
            lanes = str(edge_data.get("numLanes", edge_data.get("lanes", "1")))
            speed_val = edge_data.get("speed", edge_data.get("maxSpeed", None))
            if speed_val is not None:
                speed = (
                    f"{float(speed_val) * 3.6:.0f} km/h" if float(speed_val) < 40 else f"{float(speed_val):.0f} km/h"
                )
            flow_val = edge_data.get("flow", edge_data.get("traffic_flow", None))
            if flow_val is not None:
                flow = f"{int(flow_val)} v/h"
            just = edge_data.get("description", f"Via {name} integrante da malha viária tática.")

        return NodeDetailsDTO(
            node_id=f"Via: {name}",
            rec_label="VIA / RUA SELECIONADA",
            rec_bg_color=ft.Colors.CYAN_800,
            saturation_str=f"{lanes} faixa(s)",
            delay_str=speed,
            flow_str=flow,
            warrant_str="Normal",
            justification_str=just,
        )
