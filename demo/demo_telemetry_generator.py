# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import random
from typing import Dict, List, Tuple


class DemoTelemetryGenerator:
    """Generates synthetic real-time semaphore phases, street traffic dynamics, and metrics."""

    STREET_NAMES = {
        "370320174#0": "Avenida Dom Pedro II",
        "104845175": "Estrada Ouro Fino",
        "370318891#0": "Avenida São João",
        "103342115#1": "Rua 7 de Setembro",
        "370318865#0": "Rua Vasco da Gama",
        "103342093": "Rua Sebastião Cardoso da Silva",
        "696403842#0": "Rodovia Alvaro Godoy",
    }

    @classmethod
    def get_street_name(cls, street_id: str) -> str:
        return cls.STREET_NAMES.get(street_id, f"Via {street_id}")

    @classmethod
    def generate_packet(
        cls,
        step: int,
        timestamp: float,
        traffic_lights: List[str],
        street_ids: List[str],
        semaphore_overrides: Dict[str, str],
        street_overrides: Dict[str, str],
        phase_cycle: List[str],
    ) -> dict:
        """Constructs a complete telemetry update packet for the UI queue."""
        maturity_phases = {}
        panel_data = {}

        for idx, tl_id in enumerate(traffic_lights):
            override = semaphore_overrides.get(tl_id, "NORMAL")
            if override == "ALERT":
                current_phase = "YELLOW"
            elif override == "OFF":
                current_phase = "OFF"
            else:
                phase_idx = (step // 4 + idx) % len(phase_cycle)
                current_phase = phase_cycle[phase_idx]

            maturity_phases[tl_id] = current_phase
            panel_data[tl_id] = {
                "name": f"Cruzamento {tl_id}",
                "brand": "SWARCO ITC-2" if idx % 2 == 0 else "EcoTrafic Adaptive",
                "model": "ITC-2026-X" if idx % 2 == 0 else "NX-Signal Pro",
                "phase": current_phase,
                "mode": "Alerta Intermitente" if override == "ALERT" else ("Desativado" if override == "OFF" else "Adaptativo Autônomo"),
                "cycle_time": 90,
                "plan": "HFT-Dynamic-V4",
            }

        street_data = {}
        congestion_payload = {}

        for s_id in street_ids:
            is_blocked = street_overrides.get(s_id) == "BLOCKED"
            if is_blocked:
                c_val, spd, flw, veh = 98.5, 0.0, 0, 72
            else:
                base_c = 42.0 + (hash(s_id) % 25)
                c_val = round(base_c + random.uniform(-2.5, 2.5), 1)
                spd = round(36.0 + random.uniform(-3.0, 3.0), 1)
                flw = int(1250 + random.uniform(-60, 90))
                veh = int(28 + random.uniform(-4, 6))

            street_data[s_id] = {
                "name": cls.get_street_name(s_id),
                "congestion": c_val,
                "flow": flw,
                "speed": spd,
                "vehicles": veh,
            }
            congestion_payload[s_id] = c_val / 100.0

        return {
            "type": "update_dashboard_data",
            "timestamp": timestamp,
            "maturity_phases": {"agent_maturity": maturity_phases},
            "panel_data": panel_data,
            "street_data": street_data,
            "payload": congestion_payload,
        }
