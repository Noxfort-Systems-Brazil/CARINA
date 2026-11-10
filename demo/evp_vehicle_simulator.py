# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
CLI Telemetry Simulator for Emergency Vehicles in CARINA_CORE.
Sends unidirectional HTTP packets (Fire-and-Forget) simulating GPS antennas
for SAMU, Fire Department, and Police vehicles snapped strictly to road waypoints.
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, List, Tuple

# Path setup to import waypoint kinematics
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from demo.waypoint_kinematics import (
    WaypointVehicle,
    SAMU_WAYPOINTS,
    BOMBEIRO_WAYPOINTS,
    POLICIA_WAYPOINTS,
)


def send_telemetry(host: str, port: int, payload: Dict) -> Tuple[bool, int, str]:
    """Sends unidirectional POST request to the telemetry endpoint."""
    url = f"http://{host}:{port}/amb/v1"
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "CARINA-EVP-GPS-Antenna/1.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return True, resp.status, ""
    except urllib.error.HTTPError as e:
        return False, e.code, str(e)
    except urllib.error.URLError as e:
        return False, 0, str(e.reason)
    except Exception as e:
        return False, 0, str(e)


def run_fleet_patrol(host: str, port: int, duration: float = 60.0):
    """Simulates all 3 emergency services operating simultaneously in real time snapped to road lines."""
    print(f"\n=======================================================")
    print(f"🚒 SIMULADOR DE FROTA MULTI-CORPORAÇÃO (SAMU + BOMB + PM)")
    print(f"Transmitindo a 2.5 Hz para http://{host}:{port}/amb/v1")
    print(f"Malha: Rolândia/PR (vias mapeadas em map_topology.json)")
    print(f"=======================================================\n")

    samu = WaypointVehicle(
        "SAMU-01", "SAMU", SAMU_WAYPOINTS,
        speed_kmh=68.5, is_loop=True, siren_active=True,
        target_intersection_id="1116667894", target_intersection_xy=(311.94, 854.79)
    )
    bombeiro = WaypointVehicle(
        "BOMBEIRO-01", "BOMBEIRO", BOMBEIRO_WAYPOINTS,
        speed_kmh=45.0, is_loop=False, siren_active=False
    )
    policia = WaypointVehicle(
        "POLICIA-01", "POLICIA", POLICIA_WAYPOINTS,
        speed_kmh=55.0, is_loop=False, siren_active=False
    )
    fleet = [samu, bombeiro, policia]

    start_time = time.time()
    last_t = start_time

    while time.time() - start_time < duration:
        now = time.time()
        dt = min(0.5, max(0.1, now - last_t))
        last_t = now

        for v in fleet:
            v.update(dt)
            payload = v.to_payload()
            payload["timestamp"] = int(time.time() * 1000)

            ok, code, err = send_telemetry(host, port, payload)
            ind = "✅" if ok else "❌"
            siren_str = "🚨 SIRENE ON" if v.siren_active else "⚪ PATRULHA"
            evp_str = " [PREEMPÇÃO ATIVA]" if v.is_evp_triggered else ""
            print(f"{ind} [{v.vehicle_id:11}] {v.corporation:8} ({payload['latitude']:.5f}, {payload['longitude']:.5f}) x={payload['x']:6.1f} y={payload['y']:6.1f} {siren_str}{evp_str}")

        time.sleep(0.4)


def main():
    parser = argparse.ArgumentParser(description="Simulador de Telemetria de Veículo de Emergência (EVP)")
    parser.add_argument("--host", default="localhost", help="Host do CARINA_CORE (padrão: localhost)")
    parser.add_argument("--port", type=int, default=2201, help="Porta HTTP do receptor EVP (padrão: 2201)")
    parser.add_argument(
        "--mode",
        choices=["emergency", "patrol", "siren_off"],
        default="patrol",
        help="Modo: 'emergency' (corrida com preempção), 'patrol' (frota contínua), 'siren_off' (teste de desarme)",
    )
    parser.add_argument(
        "--vehicle",
        choices=["SAMU-01", "BOMBEIRO-01", "POLICIA-01"],
        default="SAMU-01",
        help="ID da viatura a simular",
    )
    parser.add_argument("--duration", type=float, default=120.0, help="Duração da simulação em segundos")

    args = parser.parse_args()
    run_fleet_patrol(args.host, args.port, duration=args.duration)


if __name__ == "__main__":
    main()
