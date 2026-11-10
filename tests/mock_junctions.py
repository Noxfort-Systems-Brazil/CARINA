# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys
import time

mock_lights_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "CARINA_MOCK_LIGHTS"))
sys.path.append(mock_lights_dir)

try:
    from core.manager import Junction, TrafficLightManager
    from core.sumo_parser import JunctionData, PhaseData
except ImportError:
    print(f"Erro ao importar módulos do MOCK. Verifique se o diretório {mock_lights_dir} existe.")
    sys.exit(1)


def main():
    num_junctions = 20
    if len(sys.argv) > 1:
        try:
            num_junctions = int(sys.argv[1])
        except ValueError:
            pass

    manager = TrafficLightManager(base_port=8080)

    # Create 'num_junctions' simulated junctions
    for i in range(num_junctions):
        phases = [
            PhaseData(duration=10, state="GGggrrrr"),
            PhaseData(duration=4, state="yyggrrrr"),
            PhaseData(duration=10, state="rrrrGGgg"),
            PhaseData(duration=4, state="rrrryygg"),
        ]
        data = JunctionData(f"mock_junction_{i+1}", phases, num_lights=8)
        port = manager.base_port + i
        junc = Junction(data, port)
        manager.junctions[str(junc.id)] = junc
        junc.start()

    manager.start()

    try:
        print("Starting PEAK traffic generator (Stress Test) to push CARINA CORE...")
        while True:
            # Simulates absolute peak scenario: sends frantic interrupts and state transitions
            # This forces the Symbolic Engine and NTCIP threads to constantly process data.
            for j_id, junc in manager.junctions.items():
                junc.last_ntcip_activity = time.time()
                # Repeatedly toggles state to invalidate caches and force recalculations
                junc._apply_phase("GGrryyGG")
            time.sleep(0.05)  # Bombards core 20 times per second per intersection
    except KeyboardInterrupt:
        manager.stop()


if __name__ == "__main__":
    main()
