# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Backward-compatibility adapter for AgentPopulationLoader.
Re-exports AgentPopulationLoader and TopologyManager from manager.agent_population_loader.
"""

from manager.agent_population_loader import AgentPopulationLoader, TopologyManager

__all__ = ["AgentPopulationLoader", "TopologyManager"]
