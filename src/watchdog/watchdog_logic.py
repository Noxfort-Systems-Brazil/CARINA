# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class Watchdog:
    """
    Monitors the 'heartbeat' of the input data stream.
    If the time since the last heartbeat exceeds the threshold, it triggers a safety fallback.
    """

    def __init__(
        self,
        timeout_ms: int = 300,
        grace_period_sec: float = 10.0,
        locale_manager=None,
        on_fenix_trigger: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize the Watchdog.

        Args:
            timeout_ms (int): The maximum allowed silence from Synapse in milliseconds before
                               triggering fail-safe mode.
            grace_period_sec (float): The initial grace period in seconds during startup.
            locale_manager: Optional LocaleManagerBackend instance.
            on_fenix_trigger: Optional callback invoked when watchdog failsafe is triggered.
        """
        if timeout_ms <= 300:
            timeout_ms = 300

        self._timeout_seconds = timeout_ms / 1000.0
        self._grace_period_seconds = grace_period_sec
        self._startup_time = time.perf_counter()
        self._last_heartbeat_time = None
        self._is_fail_safe_active = False
        self.locale_manager = locale_manager

        # Callbacks for state transitions
        self._on_fallback_activate: Optional[Callable[[], None]] = None
        self._on_fallback_deactivate: Optional[Callable[[], None]] = None
        self._on_fenix_trigger: Optional[Callable[[], None]] = on_fenix_trigger

        # --- Flapping Detection ---
        self._consecutive_triggers = 0
        self._total_triggers = 0
        self._total_recoveries = 0
        self._FLAPPING_THRESHOLD = 5  # Triggers within short succession = systemic issue

        logger.info(
            self._get_string(
                "watchdog.init",
                default="Watchdog Logic initialized with {timeout}ms timeout threshold and {grace}s grace period.",
                timeout=timeout_ms,
                grace=grace_period_sec,
            )
        )

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def set_callbacks(
        self,
        on_activate: Callable[[], None],
        on_deactivate: Callable[[], None],
        on_fenix_trigger: Optional[Callable[[], None]] = None,
    ):
        """
        Register callback functions to be triggered when state changes.
        """
        self._on_fallback_activate = on_activate
        self._on_fallback_deactivate = on_deactivate
        if on_fenix_trigger is not None:
            self._on_fenix_trigger = on_fenix_trigger

    def update_timeout(self, timeout_ms: int) -> None:
        """
        Updates the heartbeat silence timeout threshold dynamically.
        Enforces the minimum 300ms real-time safety floor.
        """
        safe_timeout_ms = max(300, int(timeout_ms))
        self._timeout_seconds = safe_timeout_ms / 1000.0
        logger.info(
            self._get_string(
                "watchdog.timeout_updated",
                default="Watchdog timeout dynamically updated to {timeout}ms.",
                timeout=safe_timeout_ms,
            )
        )

    def register_heartbeat(self):
        """
        Called whenever a valid data packet is received from Synapse.
        Resets the timer and recovers from Fail-Safe if currently active.
        """
        self._last_heartbeat_time = time.perf_counter()

        if self._is_fail_safe_active:
            self._recover_system()

    def check_system_health(self) -> bool:
        """
        Evaluates the current state against the timer.
        Returns True if system is healthy, False if in Fail-Safe mode.
        """
        current_time = time.perf_counter()

        # If we are within the initial startup grace period, we are healthy
        if current_time - self._startup_time <= self._grace_period_seconds:
            return True

        if self._last_heartbeat_time is None:
            # Grace period expired and no heartbeat received yet
            if not self._is_fail_safe_active:
                self._trigger_failsafe(current_time - self._startup_time)
            return False

        elapsed_time = current_time - self._last_heartbeat_time

        if elapsed_time > self._timeout_seconds:
            if not self._is_fail_safe_active:
                self._trigger_failsafe(elapsed_time)
            return False

        return True

    def trigger_dnn_error(self, error: Optional[object] = None):
        """
        Explicitly triggers Fail-Safe due to a confirmed Deep Neural Network (DNN) error.
        Activates Fixed-Time mode and invokes F.E.N.I.X. crash recovery supervisor.
        """
        logger.critical(
            f"[Watchdog] 🚨 DNN Error detected: {error}. Activating FIXED-TIME mode and F.E.N.I.X. supervisor."
        )
        self._trigger_failsafe(elapsed_time=0.0, is_dnn_error=True)

    def _trigger_failsafe(self, elapsed_time: float, is_dnn_error: bool = False):
        self._is_fail_safe_active = True
        self._consecutive_triggers += 1
        self._total_triggers += 1

        if is_dnn_error:
            logger.critical(
                "[Watchdog] FAILSAFE TRIGGERED: DNN error encountered. Switching to FIXED-TIME mode and requesting FENIX recovery."
            )
        else:
            logger.critical(
                self._get_string(
                    "watchdog.triggered",
                    default="WATCHDOG TRIGGERED: Synapse silence detected ({elapsed:.1f}ms > {threshold:.0f}ms). Switching to FIXED-TIME mode. [triggers: {consecutive} consecutive, {total} total]",
                    elapsed=elapsed_time * 1000,
                    threshold=self._timeout_seconds * 1000,
                    consecutive=self._consecutive_triggers,
                    total=self._total_triggers,
                )
            )

        # Flapping detection: if we keep triggering and recovering rapidly, something is wrong
        if self._consecutive_triggers >= self._FLAPPING_THRESHOLD:
            logger.critical(
                self._get_string(
                    "watchdog.flapping",
                    default="WATCHDOG FLAPPING DETECTED: {consecutive} consecutive triggers. This indicates a SYSTEMIC latency issue. Check HFT diagnostics log.",
                    consecutive=self._consecutive_triggers,
                )
            )

        # Fixed-Time / Fallback is ALWAYS activated (both on time trigger and on DNN error)
        if self._on_fallback_activate:
            try:
                self._on_fallback_activate()
            except Exception as e:
                logger.error(
                    self._get_string(
                        "watchdog.activation_error",
                        default="Error executing Watchdog activation callback: {error}",
                        error=e,
                    )
                , exc_info=True)

        # FENIX mode is triggered ONLY if this is a DNN error (timer trigger does NOT activate Fenix)
        if is_dnn_error and self._on_fenix_trigger:
            try:
                self._on_fenix_trigger()
            except Exception as e:
                logger.error(f"[Watchdog] Error executing Fenix resurrection trigger: {e}", exc_info=True)
        elif not is_dnn_error:
            logger.debug("[Watchdog] Timeout was due to heartbeat silence (Synapse). FENIX trigger skipped.")

    def _recover_system(self):
        self._is_fail_safe_active = False
        self._total_recoveries += 1

        logger.info(
            self._get_string(
                "watchdog.recovery",
                default="WATCHDOG RECOVERY: Signal restored. Resuming Neural Network control. [was {consecutive} consecutive trigger(s)]",
                consecutive=self._consecutive_triggers,
            )
        )

        # Reset consecutive counter on recovery
        self._consecutive_triggers = 0

        if self._on_fallback_deactivate:
            try:
                self._on_fallback_deactivate()
            except Exception as e:
                logger.error(
                    self._get_string(
                        "watchdog.deactivation_error",
                        default="Error executing Watchdog deactivation callback: {error}",
                        error=e,
                    )
                , exc_info=True)

    @property
    def is_in_failsafe(self) -> bool:
        return self._is_fail_safe_active
