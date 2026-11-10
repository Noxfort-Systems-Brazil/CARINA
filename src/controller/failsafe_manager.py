# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time
from multiprocessing.connection import Connection
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class FailsafeManager:
    """
    Responsible for managing the global operation mode of CARINA:
        - AUTOMATIC: AI Neural Network controls traffic signals
        - SEMI_AUTOMATIC: Assisted operation mode
        - WATCHDOG: Fixed-time hardware fallback (Synapse connection lost)
        - MANUAL: Operator override

    Coordinates the transition between AI-controlled and failsafe modes
    with strict real-time safety guarantees.
    """

    def __init__(
        self,
        ai_pipe_conn: Connection,
        monitor_client: Optional[Any] = None,
        locale_manager: Optional[Any] = None,
        on_failsafe_triggered: Optional[Callable[[], None]] = None,
        on_failsafe_recovered: Optional[Callable[[], None]] = None,
    ):
        self.current_operation_mode = "AUTOMATIC"
        self.failsafe_active = False

        self.ai_pipe_conn = ai_pipe_conn
        self.monitor_client = monitor_client
        self.locale_manager = monitor_client.locale_manager if monitor_client else locale_manager
        self.on_failsafe_triggered = on_failsafe_triggered
        self.on_failsafe_recovered = on_failsafe_recovered

        # --- Frame Timing Monitor ---
        # Tracks the last time a TrafficFrame was received.
        # Used by CentralController to detect Synapse silence in-process.
        self._last_frame_time: Optional[float] = None
        self._failsafe_timeout: float = 0.30  # 300ms default, overridden by settings

        # --- Failsafe Statistics ---
        self._failsafe_activation_time: Optional[float] = None
        self._total_failsafe_events: int = 0

    def set_failsafe_timeout(self, timeout_seconds: float):
        """Set the Synapse silence timeout (from settings.ini WATCHDOG section)."""
        self._failsafe_timeout = timeout_seconds

    def record_frame_received(self):
        """
        Record that a TrafficFrame was received from Synapse.
        Called by TrafficFrameProcessor on every frame.
        """
        self._last_frame_time = time.perf_counter()

    def check_synapse_health(self) -> bool:
        """
        Check if Synapse has been silent beyond the timeout threshold.
        Called periodically from CentralController main loop.

        Returns:
            True if healthy (frames arriving), False if timeout exceeded.
        """
        if self._last_frame_time is None:
            # No frames ever received — in grace period (startup)
            return True

        elapsed = time.perf_counter() - self._last_frame_time
        return elapsed <= self._failsafe_timeout

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def trigger_failsafe(self):
        """
        Forces the system into Fail-Safe (Watchdog) mode.
        Activates the FixedTimeController and reports the incident.
        """
        if not self.failsafe_active:
            self._total_failsafe_events += 1
            self._failsafe_activation_time = time.perf_counter()

            logger.critical(
                self._get_string(
                    "failsafe_manager.entering_watchdog",
                    default="[FailsafeManager] 🚨 ENTERING WATCHDOG MODE (Fixed-Time Fallback). AI Neural Network PAUSED. Event #{event}.",
                    event=self._total_failsafe_events,
                )
            )

            self.failsafe_active = True
            self.current_operation_mode = "WATCHDOG"

            # Dispatch command to hardware controller to activate emergency release and revert to local plans
            self._notify_hardware_failsafe()
            if self.on_failsafe_triggered:
                try:
                    self.on_failsafe_triggered()
                except Exception as cb_err:
                    logger.error(f"[FailsafeManager] Error in on_failsafe_triggered callback: {cb_err}", exc_info=True)

            logger.critical(
                self._get_string(
                    "failsafe_manager.commanding_all_red",
                    default="[FailsafeManager] ⚠️ COMMANDING LOCAL CONTROLLER: Execute ALL_RED transition followed by local fixed-time plans.",
                )
            )

            # Report Critical Incident to External Monitor (MQTT)
            if self.monitor_client:
                try:
                    self.monitor_client.report_incident(
                        category="SOFTWARE",
                        level="CRITICAL",
                        message=self._get_string(
                            "monitor.watchdog_trigger",
                            default="Watchdog timeout triggered (>{timeout}ms silence). Switching to Fixed-Time fallback. Event #{event}.",
                            timeout=f"{self._failsafe_timeout * 1000:.0f}",
                            event=self._total_failsafe_events,
                        ),
                    )
                except Exception as e:
                    logger.error(
                        self._get_string(
                            "failsafe_manager.mqtt_incident_error",
                            default="Error reporting failsafe incident via MQTT: {error}",
                            error=e,
                        )
                    , exc_info=True)

    def attempt_recovery(self) -> bool:
        """
        Attempts to recover the system from Watchdog mode.
        Called when a new TrafficFrame arrives during failsafe.

        Returns True if recovery occurred in this call.
        """
        if self.failsafe_active:
            elapsed = time.perf_counter() - self._failsafe_activation_time if self._failsafe_activation_time else 0

            logger.info(
                self._get_string(
                    "failsafe_manager.signal_restored",
                    default="[FailsafeManager] ✅ SYNAPSE SIGNAL RESTORED after {elapsed:.1f}s. Resuming AI Neural Network control.",
                    elapsed=elapsed,
                )
            )

            # Dispatch command to hardware controller to resume remote control
            self._notify_hardware_recovery()
            if self.on_failsafe_recovered:
                try:
                    self.on_failsafe_recovered()
                except Exception as cb_err:
                    logger.error(f"[FailsafeManager] Error in on_failsafe_recovered callback: {cb_err}", exc_info=True)

            logger.info(
                self._get_string(
                    "failsafe_manager.commanding_resume",
                    default="[FailsafeManager] ✅ COMMANDING LOCAL CONTROLLER: Resume remote AI control.",
                )
            )

            self.failsafe_active = False
            self.current_operation_mode = "AUTOMATIC"

            # Report Recovery to External Monitor (MQTT)
            if self.monitor_client:
                try:
                    self.monitor_client.report_incident(
                        category="SOFTWARE",
                        level="INFO",
                        message=self._get_string(
                            "monitor.synapse_restored",
                            default="Synapse signal restored after {elapsed}s. Watchdog mode disabled, resuming AI Neural Network.",
                            elapsed=f"{elapsed:.1f}",
                        ),
                    )
                except Exception as e:
                    logger.error(
                        self._get_string(
                            "failsafe_manager.mqtt_recovery_error",
                            default="Error reporting recovery incident via MQTT: {error}",
                            error=e,
                        )
                    , exc_info=True)

            # Wake up AI process
            try:
                self.ai_pipe_conn.send(("system", "wakeup", (), {}))
            except (OSError, EOFError, BrokenPipeError, RuntimeError, ValueError, AttributeError) as e:
                logger.error(
                    self._get_string(
                        "failsafe_manager.wakeup_error", default="Error sending wakeup signal to AI: {error}", error=e
                    )
                )

            return True
        return False

    def tick(self) -> Dict[str, str]:
        """
        Advance the failsafe state.
        Since local fixed-time control was removed, this just returns empty.
        Hardware handles its own ticking during failsafe.
        """
        return {}

    def get_status(self) -> Dict:
        """Returns complete failsafe status for dashboard/telemetry."""
        return {
            "operation_mode": self.current_operation_mode,
            "failsafe_active": self.failsafe_active,
            "total_failsafe_events": self._total_failsafe_events,
            "fixed_time": {},  # Kept for dashboard compatibility
        }

    def _notify_hardware_failsafe(self):
        """Dispatches emergency release commands to Go Hardware Gateway and active drivers."""
        try:
            from drivers.go_gateway_client import GoGatewayClient

            go_client = GoGatewayClient.get_instance()
            if go_client.is_running():
                go_client.send_command("emergency_release")
        except Exception as e:
            logger.warning(f"[FailsafeManager] Go Gateway emergency release notification error: {e}", exc_info=True)

        try:
            from controller.connection_manager import HardwareConnectionManager

            hw_mgr = HardwareConnectionManager.get_instance(locale_manager=self.locale_manager)
            if hw_mgr and getattr(hw_mgr, "active_connections", None):
                for pid, driver in hw_mgr.active_connections.items():
                    try:
                        if hasattr(driver, "release_control"):
                            driver.release_control()
                    except Exception as driver_err:
                        logger.error(
                            f"[FailsafeManager] Failed to release hardware control for intersection {pid}: {driver_err}"
                        , exc_info=True)
        except Exception as e:
            logger.warning(f"[FailsafeManager] Hardware connection manager release error: {e}", exc_info=True)

    def _notify_hardware_recovery(self):
        """Verifies hardware connectivity upon recovering from Watchdog failsafe."""
        try:
            from drivers.go_gateway_client import GoGatewayClient

            go_client = GoGatewayClient.get_instance()
            if go_client.is_running():
                go_client.ping(timeout=1.0)
        except Exception as e:
            logger.warning(f"[FailsafeManager] Go Gateway resume notification error: {e}", exc_info=True)
