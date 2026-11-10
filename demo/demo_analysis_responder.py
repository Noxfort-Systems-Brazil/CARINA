# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time
from typing import Any


class DemoAnalysisResponder:
    """Dispatches realistic simulated AI planning reports and intersection recommendations."""

    @staticmethod
    def dispatch_analysis_response(sas_result_queue: Any, delay_seconds: float = 2.5) -> None:
        """Pushes a high-fidelity AI optimization report to sas_result_queue after a brief delay."""
        if delay_seconds > 0:
            time.sleep(delay_seconds)

        now = time.time()
        report = {
            "timestamp": now,
            "status": "success",
            "significant_change": True,
            "scenario_dir": "/tmp",
            "report_content": (
                "NOXFORT CARINA - LAUDO TÉCNICO DE OTIMIZAÇÃO URBANA\n"
                "Data de Processamento: 2026-10-07\n\n"
                "1. Resumo Executivo:\n"
                "O modelo neural ST-GATv2 Lite e o motor MFD recalcularam os parâmetros de split e ciclo\n"
                "para a malha urbana monitorada, otimizando o fluxo em 4 interseções críticas.\n\n"
                "2. Métricas de Impacto Projetadas:\n"
                "- Redução média de atraso por veículo: -26.4%\n"
                "- Aumento da capacidade de vazão contínua: +18.2%\n"
                "- Redução estimada de emissões veiculares: -14.7%\n\n"
                "3. Plano Semafórico Otimizado:\n"
                "- Cruzamento 1116667894: Ciclo 90s (Verde 55s / Vermelho 35s)\n"
                "- Cruzamento 1193472473: Ciclo 90s (Verde 45s / Vermelho 45s)\n"
                "- Cruzamento 1193472566: Ciclo 90s (Verde 50s / Vermelho 40s)\n"
                "- Cruzamento 1193472678: Ciclo 90s (Verde 48s / Vermelho 42s)\n"
            ),
            "analysis_results": {
                "1116667894": {
                    "action": "OTIMIZADO",
                    "green_split": 55,
                    "cycle_time": 90,
                    "reduction_delay": "-26.4%",
                    "capacity_gain": "+18.2%",
                },
                "1193472473": {
                    "action": "OTIMIZADO",
                    "green_split": 45,
                    "cycle_time": 90,
                    "reduction_delay": "-22.1%",
                    "capacity_gain": "+15.0%",
                },
                "1193472566": {
                    "action": "OTIMIZADO",
                    "green_split": 50,
                    "cycle_time": 90,
                    "reduction_delay": "-19.8%",
                    "capacity_gain": "+12.4%",
                },
                "1193472678": {
                    "action": "OTIMIZADO",
                    "green_split": 48,
                    "cycle_time": 90,
                    "reduction_delay": "-24.5%",
                    "capacity_gain": "+17.1%",
                },
            },
        }

        if sas_result_queue:
            sas_result_queue.put(report)
            logging.info("[DemoAnalysisResponder] AI Analysis response pushed successfully to sas_result_queue!")
