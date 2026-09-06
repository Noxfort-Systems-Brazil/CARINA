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

# File: tests/mock_junctions.py
# Author: Gabriel Moraes
# Date: September 2026

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

    # Criar 'num_junctions' junções simuladas
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
        print("Iniciando gerador de tráfego de PICO (Stress Test) para forçar o CARINA CORE...")
        while True:
            # Simula um cenário de pico absoluto: envia interrupções e mudanças de estado frenéticas
            # Isso força o Motor Simbólico e as threads de NTCIP a processarem dados constantemente.
            for j_id, junc in manager.junctions.items():
                junc.last_ntcip_activity = time.time()
                # Alterna o estado repetidamente para invalidar os caches e forçar recálculos
                junc._apply_phase("GGrryyGG")
            time.sleep(0.05)  # Bombardeia o core 20 vezes por segundo por cruzamento
    except KeyboardInterrupt:
        manager.stop()


if __name__ == "__main__":
    main()
