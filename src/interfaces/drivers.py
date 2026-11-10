# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Hardware Traffic Driver Ports Re-export (Clean Architecture: src/interfaces/drivers.py).
"""

from src.drivers.base_driver import BaseTrafficDriver
from src.drivers.hardware_event_listener import BaseActiveEventListener

__all__ = [
    "BaseTrafficDriver",
    "BaseActiveEventListener",
]
