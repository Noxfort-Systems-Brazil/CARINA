# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import os
import queue
import time
from multiprocessing import Queue
from typing import Optional

from watchdog.watchdog_logic import Watchdog

try:
    from utils.logging_setup import setup_logging
    from utils.paths import get_base_output_dir, resource_path
except ImportError:
    # Fallback if utils not found in path
    def get_base_output_dir():
        return "."

    def resource_path(p):
        return p

    def setup_logging(log_dir):
        pass


logger = logging.getLogger(__name__)


def run_watchdog(com_queue: Queue, locale_manager, fenix_queue: Optional[Queue] = None):
    """
    Process entry point for the Watchdog system.

    Args:
        com_queue (Queue): Queue to receive 'HEARTBEAT' signals and potentially send status updates.
        locale_manager: Instance of locale manager (passed from main, though we might rely on logs mostly).
        fenix_queue (Optional[Queue]): Queue to notify FENIX supervisor process manager for resurrection.
    """

    def get_str(key: str, default: str = None, **kwargs) -> str:
        if locale_manager and hasattr(locale_manager, "get_string"):
            return locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    # 1. Setup Logging for this process
    log_base_dir = get_base_output_dir()
    log_dir = os.path.join(log_base_dir, "logs", "watchdog")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    logger.info(get_str("watchdog.process_started", default="--- Watchdog Process Started ---"))

    # 2. Load Settings to get Timeout
    settings = configparser.ConfigParser()
    settings_path = resource_path(os.path.join("config", "settings.ini"))
    timeout_ms = 300  # Default: 300ms as per CARINA real-time safety requirement

    try:
        if os.path.exists(settings_path):
            settings.read(settings_path, encoding="utf-8")
            # Read from [WATCHDOG] heartbeat_timeout_seconds (which is in seconds in ini, convert to ms)
            timeout_sec = settings.getfloat("WATCHDOG", "heartbeat_timeout_seconds", fallback=0.30)
            timeout_ms = int(timeout_sec * 1000)
            logger.info(
                get_str(
                    "watchdog.timeout_loaded", default="Loaded timeout from settings: {timeout}ms", timeout=timeout_ms
                )
            )
        else:
            logger.warning(
                get_str(
                    "watchdog.settings_not_found",
                    default="Settings file not found at {path}. Using default timeout: {timeout}ms",
                    path=settings_path,
                    timeout=timeout_ms,
                )
            )
    except Exception as e:
        logger.error(
            get_str(
                "watchdog.settings_error", default="Error reading settings: {error}. Using default timeout.", error=e
            )
        , exc_info=True)

    def on_fenix_trigger():
        logger.warning(
            get_str(
                "watchdog.fenix_trigger",
                default="[Watchdog] 🚨 F.E.N.I.X. TRIGGERED: DNN error confirmed. Activating crash supervisor.",
            )
        )
        if fenix_queue is not None:
            try:
                fenix_queue.put_nowait(("TRIGGER_RESURRECTION", "DNN_ERROR"))
                logger.info("[Watchdog] Dispatched TRIGGER_RESURRECTION to FENIX IPC queue.")
            except Exception as q_err:
                logger.error(f"[Watchdog] Error notifying fenix_queue: {q_err}", exc_info=True)

        try:
            from fenix.fenix_supervisor import FenixSupervisor

            supervisor = FenixSupervisor()
            supervisor.record_child_crash(exit_code=1)
        except Exception as err:
            logger.debug(f"[Watchdog] Error notifying FENIX supervisor: {err}")

    # 3. Initialize Logic
    wd = Watchdog(timeout_ms=timeout_ms, locale_manager=locale_manager, on_fenix_trigger=on_fenix_trigger)

    # Define Actions (Defense-in-depth: log critical events for audit trail)
    # NOTE: We no longer put FAILSAFE/RECOVERY on com_queue because that is the SAME
    # queue this process reads HEARTBEAT from. Self-messaging causes noise.
    # The CentralController has its own in-process detection via FailsafeManager.
    def on_failsafe_active():
        logger.critical(
            get_str("watchdog.failsafe_triggered", default="[Watchdog] ⚠️ FAILSAFE TRIGGERED — Synapse connection lost.")
        )

    def on_failsafe_recover():
        logger.info(
            get_str(
                "watchdog.heartbeat_restored",
                default="[Watchdog] ✅ RECOVERY — Synapse heartbeat restored. AI Neural Network may resume control.",
            )
        )

    wd.set_callbacks(on_failsafe_active, on_failsafe_recover, on_fenix_trigger=on_fenix_trigger)

    # 4. Main Loop
    logger.info(get_str("watchdog.loop_active", default="Watchdog monitoring loop active. Waiting for Heartbeats..."))

    def _apply_config_update(payload):
        if isinstance(payload, (int, float)):
            wd.update_timeout(int(payload))
        elif isinstance(payload, dict):
            if "timeout_ms" in payload:
                wd.update_timeout(int(payload["timeout_ms"]))
            elif "heartbeat_timeout_seconds" in payload:
                wd.update_timeout(int(float(payload["heartbeat_timeout_seconds"]) * 1000))

    try:
        while True:
            # Phase 1: Drain ALL pending messages from queue immediately.
            # Uses get_nowait() directly instead of unreliable empty() check.
            # Python docs: "Queue.empty() is not reliable for multiprocessing".
            try:
                while True:
                    msg = com_queue.get_nowait()

                    if msg == "HEARTBEAT":
                        wd.register_heartbeat()
                    elif msg == "DNN_ERROR" or (isinstance(msg, tuple) and msg[0] == "DNN_ERROR"):
                        err_info = msg[1] if isinstance(msg, tuple) and len(msg) > 1 else None
                        wd.trigger_dnn_error(error=err_info)
                    elif msg in ("STOP", None):
                        logger.info(
                            get_str("watchdog.stop_signal", default="Stop signal received. Shutting down Watchdog.")
                        )
                        return
                    elif isinstance(msg, tuple) and msg[0] == "CONFIG_UPDATE":
                        if len(msg) > 1:
                            _apply_config_update(msg[1])
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(get_str("watchdog.loop_error", default="Error in Watchdog loop: {error}", error=e), exc_info=True)

            # Phase 2: Check health AFTER draining all pending heartbeats
            wd.check_system_health()

            # Phase 3: Block-wait for next message (replaces sleep).
            # get(timeout=0.01) is both a 10ms sleep AND a message listener,
            # so the watchdog responds to heartbeats faster than sleep+poll.
            try:
                msg = com_queue.get(timeout=0.01)
                if msg == "HEARTBEAT":
                    wd.register_heartbeat()
                elif msg == "DNN_ERROR" or (isinstance(msg, tuple) and msg[0] == "DNN_ERROR"):
                    err_info = msg[1] if isinstance(msg, tuple) and len(msg) > 1 else None
                    wd.trigger_dnn_error(error=err_info)
                elif msg in ("STOP", None):
                    logger.info(
                        get_str("watchdog.stop_signal", default="Stop signal received. Shutting down Watchdog.")
                    )
                    return
                elif isinstance(msg, tuple) and msg[0] == "CONFIG_UPDATE":
                    if len(msg) > 1:
                        _apply_config_update(msg[1])
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(get_str("watchdog.wait_error", default="Error in Watchdog wait phase: {error}", error=e), exc_info=True)
    except (KeyboardInterrupt, SystemExit):
        logger.info(get_str("watchdog.stop_signal", default="Stop signal received. Shutting down Watchdog."))
    finally:
        os._exit(0)
