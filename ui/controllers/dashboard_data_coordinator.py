# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, Optional, Tuple


class DashboardDataCoordinator:
    """
    Coordinates real-time telemetry caching, ID resolution (tl_ prefix variations),
    hardware metadata querying, and street alias binding for the dashboard view.
    """

    def __init__(self):
        self.latest_data_packet: Dict[str, Any] = {}
        self.latest_panel_data: Dict[str, Any] = {}
        self.latest_street_data: Dict[str, Any] = {}
        self.maturity_phases: Dict[str, str] = {}
        self.edge_names: Dict[str, str] = {}

    def initialize_from_map_data(self, nodes: dict, edges: list) -> None:
        """Extracts initial edge names and traffic light maturity phase defaults."""
        self.edge_names = {e["id"]: e.get("name", e["id"]) for e in edges if isinstance(e, dict)}
        traffic_light_ids = [node_id for node_id, data in nodes.items() if data.get("type") == "traffic_light"]
        self.maturity_phases = {tl_id: "UNKNOWN" for tl_id in traffic_light_ids}

    def process_live_packet(self, data_packet: dict) -> None:
        """Selectively merges telemetry packets into internal UI caches."""
        self.latest_data_packet = data_packet

        hw_status = data_packet.get("hardware_status")
        if isinstance(hw_status, dict) and hw_status:
            try:
                from src.controller.connection_manager import HardwareConnectionManager

                HardwareConnectionManager.get_instance().update_remote_hardware_status(hw_status)
            except Exception:
                pass

        if "panel_data" in data_packet and data_packet["panel_data"]:
            self.latest_panel_data = data_packet["panel_data"]

        if "street_data" in data_packet and data_packet["street_data"]:
            self.latest_street_data = data_packet["street_data"]

        raw_maturity_data = data_packet.get("maturity_phases", {})
        if "agent_maturity" in raw_maturity_data:
            self.maturity_phases = raw_maturity_data["agent_maturity"]
        elif raw_maturity_data:
            self.maturity_phases = {k: v for k, v in raw_maturity_data.items() if k not in ("run_id", "scenario_name")}

    def resolve_semaphore_info(self, semaphore_id: str) -> Tuple[str, dict]:
        """Resolves maturity phase and hardware attributes for the given semaphore ID."""
        possible_ids = [semaphore_id]
        if semaphore_id.startswith("tl_"):
            possible_ids.append(semaphore_id.replace("tl_", ""))
        else:
            possible_ids.append(f"tl_{semaphore_id}")

        phase = "UNKNOWN"
        for pid in possible_ids:
            if pid in self.maturity_phases:
                phase = self.maturity_phases[pid]
                break

        semaphore_data: Dict[str, Any] = {}
        for pid in possible_ids:
            if pid in self.latest_panel_data:
                semaphore_data = (
                    self.latest_panel_data[pid].copy() if isinstance(self.latest_panel_data[pid], dict) else {}
                )
                break

        if not semaphore_data or semaphore_data.get("brand") in (None, "Não informado"):
            try:
                from src.controller.connection_manager import HardwareConnectionManager

                for pid in possible_ids:
                    hw_info = HardwareConnectionManager.get_global_hardware_info(pid)
                    if hw_info and hw_info.get("brand") != "Não informado":
                        if not semaphore_data:
                            semaphore_data = {}
                        semaphore_data["brand"] = hw_info.get("brand")
                        semaphore_data["model"] = hw_info.get("model")
                        break
            except Exception as e:
                logging.debug(f"[DashboardDataCoordinator] Error fetching hardware info: {e}")

        return phase, semaphore_data

    def resolve_street_info(self, street_id: str) -> dict:
        """Resolves street telemetry payload and attaches mapped human-readable edge name."""
        street_data_for_panel = (
            self.latest_street_data.get(street_id, {}).copy() if isinstance(self.latest_street_data, dict) else {}
        )
        if street_id in self.edge_names:
            street_data_for_panel["name"] = self.edge_names[street_id]
        return street_data_for_panel
