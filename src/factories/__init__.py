# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
CARINA Composition Root & Factory Layer (Clean Architecture & SOLID: SRP + DIP).
Centralizes IoC containers and object graph factories.
"""

from src.factories.engine_factory import EngineFactory
from src.factories.service_container import CentralControllerContainer, ServiceContainer
from src.manager.agent_factory import AgentFactory
from src.security.factory import SecurityFactory
from src.transports.factory import create_monitor_transport

__all__ = [
    "CentralControllerContainer",
    "ServiceContainer",
    "EngineFactory",
    "AgentFactory",
    "SecurityFactory",
    "create_monitor_transport",
]
