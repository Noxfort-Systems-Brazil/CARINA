# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Lazy worker attribute resolution (PEP 562) and isolated CentralController process entrypoint."""

import logging
import os
from typing import Any, Optional

from utils.locale_manager_backend import LocaleManagerBackend
from utils.logging_setup import setup_logging
from utils.paths import get_base_output_dir
from utils.process_monitor import ProcessMonitor

_LAZY_WORKER_IMPORTS = {
    "CentralController": ("central_controller", "CentralController"),
    "run_ai_process": ("main", "run_ai_process"),
    "run_database_worker": ("database.database_worker", "run_database_worker"),
    "run_watchdog": ("watchdog.watchdog_process", "run_watchdog"),
    "run_sds_worker": ("sds.dashboard_worker", "run_sds_worker"),
    "run_analysis_worker": ("sas.analysis_worker", "run_analysis_worker"),
    "run_xai_worker": ("xai.xai_worker", "run_xai_worker"),
    "run_mfd_worker": ("mfd.mfd_worker", "run_mfd_worker"),
}


def resolve_legacy_worker_attribute(module_name: str, attr_name: str) -> Any:
    """Resolves legacy module-level worker attributes lazily on first access."""
    target = _LAZY_WORKER_IMPORTS.get(attr_name)
    if target is None:
        raise AttributeError(f"module {module_name!r} has no attribute {attr_name!r}")
    mod_path, symbol_name = target
    mod = __import__(mod_path, fromlist=[symbol_name])
    return getattr(mod, symbol_name)


def execute_controller_process(
    settings: Any,
    pipe_conn: Any,
    wd_q: Any,
    sds_q: Any,
    sas_q: Any,
    ui_q: Any,
    mfd_trigger_q: Optional[Any] = None,
    fenix_q: Optional[Any] = None,
    *,
    caller_module: Optional[Any] = None,
) -> None:
    """Isolated entrypoint executing `CentralController` in its own backend process."""
    try:
        from launcher.env_setup import setup_environment

        setup_environment()
        os.environ["CARINA_GATEWAY_ROLE"] = "owner"

        cc_cls = (
            getattr(caller_module, "CentralController")
            if caller_module is not None
            else resolve_legacy_worker_attribute(__name__, "CentralController")
        )
        log_setup_fn = getattr(caller_module, "setup_logging", setup_logging) if caller_module else setup_logging
        base_dir_fn = (
            getattr(caller_module, "get_base_output_dir", get_base_output_dir) if caller_module else get_base_output_dir
        )
        monitor_cls = getattr(caller_module, "ProcessMonitor", ProcessMonitor) if caller_module else ProcessMonitor

        log_base_dir = base_dir_fn()
        log_dir = os.path.join(log_base_dir, "logs", "central_controller")
        os.makedirs(log_dir, exist_ok=True)
        log_setup_fn(log_dir=log_dir)

        logging.info("[CentralController Process] Starting...")
        try:
            from utils.hardware_initializer import HardwareInitializer

            HardwareInitializer.setup_environment()
        except Exception:
            pass

        locale_manager = LocaleManagerBackend()
        monitor_cls.start_background_monitor(process_name="CentralController", port=8001)

        controller = cc_cls(
            settings,
            pipe_conn,
            wd_q,
            sds_q,
            sas_q,
            ui_q,
            locale_manager,
            mfd_trigger_queue=mfd_trigger_q,
        )
        if fenix_q is not None:
            controller.fenix_queue = fenix_q
        controller.run()  # Blocks here on the gRPC server
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logging.error(f"[CentralController Process] Exception: {e}", exc_info=True)
    finally:
        os._exit(0)
