# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import atexit
import logging
import multiprocessing
import os
import signal
import sys
from multiprocessing import set_start_method

# 1. Environment and sys.path setup prior to any project imports
from src.launcher.env_setup import setup_environment

project_root, bundle_root, IS_FROZEN = setup_environment()

from launcher.process_manager import ProcessManager
from launcher.single_instance import SingleInstanceLock
from launcher.ui_tray_manager import UITrayManager
from utils.paths import get_base_output_dir

# Global single instance lock
single_instance_lock = SingleInstanceLock(port=42123)


def setup_launcher_logging():
    """Configures the logging system for the launcher."""
    log_base_dir = get_base_output_dir()
    launcher_log_dir = os.path.join(log_base_dir, "logs", "launcher")
    os.makedirs(launcher_log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [LAUNCHER] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(launcher_log_dir, "launcher.log"), mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main():
    """Main orchestration function for CARINA."""
    # Process Group isolation on Linux so all child processes share the same PGID
    if sys.platform != "win32":
        try:
            os.setpgrp()
        except Exception:
            pass

    setup_launcher_logging()
    logging.info("--- CARINA SYSTEM STARTING (HFT - SOLID Architecture) ---")

    try:
        from src.controller.map_discoverer import MapTopologyDiscoverer
        from src.utils.episode_step_calculator import EpisodeStepCalculator

        map_file = MapTopologyDiscoverer.get_map_file()
        if map_file and os.path.exists(map_file):
            pacing = EpisodeStepCalculator.calculate(map_file)
            logging.info("=" * 80)
            logging.info(f"[LAUNCHER PACING] Active Map: {os.path.basename(map_file)}")
            logging.info(
                f"[LAUNCHER PACING] 1 Episode = {pacing.episode_steps} steps "
                f"({pacing.duration_seconds:.1f}s / {pacing.duration_seconds / 60:.1f}min @ 250ms/step)"
            )
            logging.info(
                f"[LAUNCHER PACING] Network Topology: {pacing.total_intersections} signals, "
                f"{pacing.real_connections} connections, complexity={pacing.topological_complexity:.2f}"
            )
            logging.info(
                f"[LAUNCHER PACING] Inviolable Safety Floor: Minimum {pacing.child_episodes_1_week} episodes "
                f"(604,800s / 1 full calendar week)"
            )
            logging.info("=" * 80)
    except Exception as e_pacing:
        logging.debug(f"[LAUNCHER PACING] Startup map detection skipped: {e_pacing}")

    process_mgr = ProcessManager()
    ui_mgr = UITrayManager(process_manager=process_mgr, bundle_root=bundle_root)

    # Register emergency cleanup with atexit
    def emergency_cleanup():
        try:
            process_mgr.shutdown_all()
        except Exception:
            pass
        try:
            single_instance_lock.release()
        except Exception:
            pass

    atexit.register(emergency_cleanup)

    # Attach signal handlers for SIGTERM/SIGINT
    def signal_handler(signum, frame):
        logging.info(f"Signal {signum} received. Triggering system shutdown...")
        ui_mgr.shutdown_requested.set()
        process_mgr.shutdown_all()
        single_instance_lock.release()
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, signal_handler)
    except Exception:
        pass

    # Start listener to restore UI if another instance is triggered
    single_instance_lock.start_restore_listener(
        shutdown_requested=ui_mgr.shutdown_requested, restore_requested=ui_mgr.restore_requested
    )

    try:
        # Launch all backend subprocesses
        process_mgr.start_all_backend_services()

        # Run the main UI/Tray loop on the main thread
        ui_mgr.run()

    except KeyboardInterrupt:
        logging.info("Interrupt (Ctrl+C).")
    finally:
        # Execute graceful shutdown and total cleanup
        ui_mgr.shutdown_requested.set()
        process_mgr.shutdown_all()
        single_instance_lock.release()

        # Secondary fallback: terminate any lingering child process tree of launcher
        try:
            import psutil

            current_proc = psutil.Process(os.getpid())
            children = current_proc.children(recursive=True)
            for child in children:
                try:
                    if child.is_running():
                        cmdline = " ".join(child.cmdline()) if hasattr(child, "cmdline") else ""
                        if "resource_tracker" not in cmdline:
                            child.kill()
                except Exception:
                    pass
        except Exception:
            pass

        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)


if __name__ == "__main__":
    # --- 1. Multiprocessing Protection (Windows/PyInstaller) ---
    multiprocessing.freeze_support()
    try:
        if multiprocessing.get_start_method(allow_none=True) != "spawn":
            set_start_method("spawn", force=True)
    except Exception as e:
        print(f"Error setting multiprocessing start method: {e}")

    # --- 2. Single Instance Lock ---
    if not single_instance_lock.acquire():
        sys.exit(0)

    print(f"[LAUNCHER STARTING] Project Root: {project_root}")
    main()
