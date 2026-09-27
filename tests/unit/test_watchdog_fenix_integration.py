# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_watchdog_fenix_integration.py
# Author: Gabriel Moraes
# Date: September 25, 2026

import time
from unittest.mock import MagicMock

import pytest

from src.watchdog.watchdog_logic import Watchdog


def test_watchdog_triggers_fenix_on_silence():
    """Verifies that Watchdog invokes on_fenix_trigger callback when timeout occurs."""
    wd = Watchdog(timeout_ms=300, grace_period_sec=0.01)

    on_fallback = MagicMock()
    on_recover = MagicMock()
    on_fenix = MagicMock()

    wd.set_callbacks(on_activate=on_fallback, on_deactivate=on_recover, on_fenix_trigger=on_fenix)

    # Wait past grace period
    time.sleep(0.02)

    # Health check triggers failsafe
    healthy = wd.check_system_health()
    assert healthy is False
    assert wd.is_in_failsafe is True

    on_fallback.assert_called_once()
    on_fenix.assert_called_once()
