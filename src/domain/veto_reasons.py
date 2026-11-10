# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Domain Model for Step Decision Codes and Veto Classifications (DDD Domain Layer).
Enums and constant dictionaries defining traffic safety constraints and intervention codes.
"""

from enum import IntEnum
from typing import Dict


class DecisionCode(IntEnum):
    """Canonical decision / veto codes evaluated at each simulation step."""

    APPROVED = 0
    PASS = 0
    MIN_GREEN = 1
    MIN_YELLOW = 2
    MIN_ALL_RED = 3
    MIN_RED = 4
    SPILLBACK_D3QN = 5
    EVP_PREEMPTION = 6
    EXPLORATORY_VETO = 7


# Backward compatible dictionary of decision codes
DECISION_CODES: Dict[str, int] = {
    "APPROVED": 0,
    "PASS": 0,
    "MIN_GREEN": 1,
    "MIN_YELLOW": 2,
    "MIN_ALL_RED": 3,
    "MIN_RED": 4,
    "SPILLBACK_D3QN": 5,
    "EVP_PREEMPTION": 6,
    "EXPLORATORY_VETO": 7,
}

# Reverse Mappings for ABNT Report Formatting and UI diagnostics
VETO_REASON_TEXT: Dict[int, str] = {
    0: "Nenhum (Decisão Aprovada)",
    1: "Proteção de Tempo Mínimo de Verde (Min Green = 10s)",
    2: "Proteção de Tempo Mínimo de Amarelo (Yellow Clearance)",
    3: "Proteção de Tempo Mínimo de Vermelho Integral (All-Red)",
    4: "Proteção de Tempo Mínimo de Vermelho Geral (Min Red)",
    5: "Veto Crítico de Spillback (Redes Neurais D3QN)",
    6: "Preempção de Veículo de Emergência (EVP - Corredor Verde Ativo)",
    7: "Intervenção Exploratória de Treino (Exploração Aleatória)",
}


def get_veto_reason_description(code: int) -> str:
    """Returns the standardized textual description of a decision/veto code."""
    return VETO_REASON_TEXT.get(code, VETO_REASON_TEXT[0])
