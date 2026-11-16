# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Registry and startup builder for CARINA backend worker processes and F.E.N.I.X. runner."""

import logging
import os
import time
from typing import Any, Callable, Dict, List, Tuple

from utils.locale_manager_backend import LocaleManagerBackend
from utils.paths import get_base_output_dir


def start_backend_worker_processes(
    *,
    process_cls: Any,
    controller_target: Callable[..., Any],
    settings: Any,
    controller_conn: Any,
    ai_conn: Any,
    queues: Dict[str, Any],
) -> Tuple[List[Any], Any, Any, Any]:
    """Instantiates, configures F.E.N.I.X. supervision for, and starts all backend worker processes."""
    from database.database_worker import run_database_worker
    from fenix.fenix_supervisor import FenixSupervisor
    from fenix.multiprocessing_runner import MultiprocessingProcessRunner
    from main import run_ai_process
    from mfd.mfd_worker import run_mfd_worker
    from sas.analysis_worker import run_analysis_worker
    from sds.dashboard_worker import run_sds_worker
    from watchdog.watchdog_process import run_watchdog
    from xai.xai_worker import run_xai_worker

    processes: List[Any] = []

    p_cc = process_cls(
        target=controller_target,
        args=(
            settings,
            controller_conn,
            queues["wd"],
            queues["sds"],
            queues["sas"],
            queues["ui"],
            queues["mfd_trigger"],
            queues.get("fenix"),
        ),
        name="CentralController",
    )
    processes.append(p_cc)

    ai_args = (ai_conn, queues["g_state"], queues["g_signal"], queues["db"])
    runner = MultiprocessingProcessRunner(target=run_ai_process, args=ai_args, name="AI_Process")
    fenix_supervisor = FenixSupervisor(runner=runner)

    p_ai = process_cls(target=run_ai_process, args=ai_args, name="AI_Process")
    runner.set_process(p_ai)
    processes.append(p_ai)

    lm = LocaleManagerBackend()
    hft_results_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session")
    os.makedirs(hft_results_dir, exist_ok=True)

    worker_specs = (
        ("Watchdog", run_watchdog, (queues["wd"], lm, queues["fenix"])),
        ("DashboardService", run_sds_worker, (queues["sds"], settings, queues["ui"], queues["ui_telemetry"])),
        ("AnalysisService", run_analysis_worker, (queues["sas"], settings, queues["db"], queues["sas_results"])),
        ("DatabaseWorker", run_database_worker, (queues["db"],)),
    )
    for name, target, args in worker_specs:
        processes.append(process_cls(target=target, args=args, name=name))

    logging.info("Starting XAI Worker...")
    processes.append(process_cls(target=run_xai_worker, args=(settings, hft_results_dir), name="XAI_Worker"))

    logging.info("Starting MFD Worker...")
    processes.append(
        process_cls(
            target=run_mfd_worker,
            args=(settings, hft_results_dir, queues["mfd_results"], queues["mfd_trigger"]),
            name="MFD_Worker",
        )
    )

    for proc in processes:
        proc.start()
        logging.info(f" -> Process [{proc.name}] successfully started! PID: {proc.pid}")
        time.sleep(0.3)

    return processes, p_cc, p_ai, fenix_supervisor
