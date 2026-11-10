# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import time
from unittest.mock import MagicMock

import pytest

from src.watchdog.watchdog_logic import Watchdog


def test_watchdog_silence_activates_fallback_without_fenix():
    """Verifies that Watchdog timer timeout activates fallback (fixed-time) but does NOT trigger FENIX."""
    wd = Watchdog(timeout_ms=300, grace_period_sec=0.01)

    on_fallback = MagicMock()
    on_recover = MagicMock()
    on_fenix = MagicMock()

    wd.set_callbacks(on_activate=on_fallback, on_deactivate=on_recover, on_fenix_trigger=on_fenix)

    # Wait past grace period
    time.sleep(0.02)

    # Health check triggers failsafe due to silence (timer trigger)
    healthy = wd.check_system_health()
    assert healthy is False
    assert wd.is_in_failsafe is True

    # Fallback (fixed-time) MUST be activated
    on_fallback.assert_called_once()
    # FENIX MUST NOT be activated on heartbeat silence / timer trigger
    on_fenix.assert_not_called()


def test_watchdog_dnn_error_triggers_fallback_and_fenix():
    """Verifies that a DNN error explicitly triggers both fallback (fixed-time) and FENIX."""
    wd = Watchdog(timeout_ms=300, grace_period_sec=10.0)

    on_fallback = MagicMock()
    on_recover = MagicMock()
    on_fenix = MagicMock()

    wd.set_callbacks(on_activate=on_fallback, on_deactivate=on_recover, on_fenix_trigger=on_fenix)

    # Trigger DNN error explicitly
    wd.trigger_dnn_error("CUDA OOM / PyTorch model divergence")

    assert wd.is_in_failsafe is True
    # Fallback (fixed-time) MUST be activated
    on_fallback.assert_called_once()
    # FENIX MUST be activated when DNN error occurs
    on_fenix.assert_called_once()


def test_watchdog_init_accepts_on_fenix_trigger():
    """Verifies that Watchdog.__init__ accepts on_fenix_trigger and preserves it when set_callbacks is called without it."""
    on_fenix = MagicMock()
    on_fallback = MagicMock()
    on_recover = MagicMock()

    wd = Watchdog(timeout_ms=300, grace_period_sec=0.01, on_fenix_trigger=on_fenix)

    # Calling set_callbacks without on_fenix_trigger must not override the constructor callback
    wd.set_callbacks(on_activate=on_fallback, on_deactivate=on_recover)

    time.sleep(0.02)
    healthy = wd.check_system_health()
    assert healthy is False
    on_fallback.assert_called_once()
    on_fenix.assert_not_called()

    # Triggering DNN error must still invoke the preserved callback
    wd.trigger_dnn_error("DNN Crash")
    on_fenix.assert_called_once()
