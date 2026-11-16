# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Hardware Traffic Driver Ports Re-export (Clean Architecture: src/interfaces/drivers.py).
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from src.drivers.base_driver import BaseTrafficDriver
from src.drivers.hardware_event_listener import BaseActiveEventListener


@runtime_checkable
class ITrafficDriverFactory(Protocol):
    """Factory port for constructing physical traffic controller driver instances (DIP)."""

    def create_driver(
        self,
        intersection_id: str,
        ip_address: str,
        port: int,
        green_stages: Optional[List[int]] = None,
        locale_manager: Any = None,
        **extra_kwargs: Any,
    ) -> Any: ...


__all__ = [
    "BaseTrafficDriver",
    "BaseActiveEventListener",
    "ITrafficDriverFactory",
]
