# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import sys
import traceback
from datetime import datetime
from multiprocessing import Queue
from multiprocessing.connection import Connection

from utils.hardware_initializer import HardwareInitializer
from utils.locale_manager_backend import LocaleManagerBackend
from utils.logging_setup import setup_logging
from utils.paths import get_base_output_dir
from utils.process_monitor import ProcessMonitor
from utils.settings_manager import SettingsManager


def run_ai_process(
    pipe_conn: Connection, guardian_state_queue: Queue, guardian_signal_queue: Queue, db_data_queue: Queue
):
    """
    Main orchestrator for the AI Process (HFT Mode).
    Coordinates environment logging, hardware setup, resource monitoring,
    and starts the continuous service loop of the Trainer engine.
    """
    # 1. Logging Initialization
    log_base_dir = get_base_output_dir()
    log_dir_ai = os.path.join(log_base_dir, "logs", "main_ai", datetime.now().strftime("%Y%m%d-%H%M%S"))
    log_configured = False
    try:
        os.makedirs(log_dir_ai, exist_ok=True)
        setup_logging(log_dir=log_dir_ai)
        log_configured = True
    except Exception as e:
        print(f"[AI Process ERROR] Failed to setup logging: {e}")

    def print_and_log(message: str, level: str = "info"):
        print(f"[AI Process] {message}")
        if log_configured:
            if level == "info":
                logging.info(message)
            elif level == "warning":
                logging.warning(message)
            elif level == "error":
                logging.error(message)
            elif level == "debug":
                logging.debug(message)

    # 2. Locale Backend Initialization
    try:
        lm = LocaleManagerBackend()
        lang_code = lm.current_lang_data.get("lang_code", lm.get_language())
        print_and_log(
            lm.get_string("main_ai.locale_init", default="LocaleManager initialized. Language: {lang}", lang=lang_code)
        )
    except Exception as e:
        print_and_log(f"Failed to initialize LocaleManagerBackend: {e}", level="error")

        class DummyLM:
            def get_string(self, key, default=None, **kwargs):
                val = default if default is not None else key
                return val.format(**kwargs) if kwargs else val

            def get_language(self):
                return "pt_br"

        lm = DummyLM()

    print_and_log(lm.get_string("main_ai.bootstrapping", default="--- AI Process Bootstrapping (HFT Mode) ---"))
    print_and_log(lm.get_string("main_ai.loading_components", default="Loading AI Engine components..."))

    # 3. Hardware Acceleration & PyTorch Setup
    try:
        HardwareInitializer.setup_environment(logging_func=print_and_log)
        from engine.engine_factory import EngineFactory

        print_and_log(lm.get_string("main_ai.components_loaded", default="AI Engine components loaded successfully."))
    except ImportError as e_import:
        print_and_log(
            lm.get_string("main_ai.critical_import_error", default="CRITICAL IMPORT ERROR: {error}", error=e_import),
            level="error",
        )
        return
    except Exception as e_gen:
        print_and_log(
            lm.get_string(
                "main_ai.critical_load_error",
                default="CRITICAL ERROR during loading phase: {error}\n{traceback}",
                error=e_gen,
                traceback=traceback.format_exc(),
            ),
            level="error",
        )
        return

    # 4. Background Resource Monitoring Daemon
    ProcessMonitor.start_background_monitor(process_name="AI_Process", port=8002)

    # 5. Load GPU Metadata & System Settings
    gpu_info = HardwareInitializer.detect_gpu(locale_manager=lm, logging_func=print_and_log)

    try:
        settings = SettingsManager().load_config()
    except Exception as e_cfg:
        print_and_log(f"Failed to load settings: {e_cfg}", level="error")
        return

    # 5.1 Episode Pacing from Active Map Topology
    try:
        from controller.map_discoverer import MapTopologyDiscoverer
        from utils.episode_step_calculator import EpisodeStepCalculator

        map_file = MapTopologyDiscoverer.get_map_file()
        if map_file and os.path.exists(map_file):
            pacing = EpisodeStepCalculator.calculate(map_file)
            print_and_log(
                f"[AI_Process PACING] Map: {os.path.basename(map_file)} | "
                f"1 episode = {pacing.episode_steps} steps ({pacing.duration_seconds:.1f}s @ 250ms) | "
                f"Safety Floor: {pacing.child_episodes_1_week} episodes (1 week / 168h)",
                level="info",
            )
    except Exception as e_ai_pacing:
        print_and_log(f"Episode pacing detection at AI startup skipped: {e_ai_pacing}", level="debug")

    # 6. Instantiate Trainer and Start Continuous Service Loop
    try:
        print_and_log(lm.get_string("main_ai.initializing_trainer", default="[MAIN_AI] Initializing Trainer..."))
        trainer = EngineFactory.create_trainer(
            settings=settings,
            log_dir=log_dir_ai,
            gpu_info=gpu_info,
            pipe_conn=pipe_conn,
        )

        print_and_log(lm.get_string("main_ai.trainer_ready", default="Trainer ready. Entering event loop..."))
        trainer.start_continuous_service()
        print_and_log(lm.get_string("main_ai.trainer_finished", default="Trainer service finished."), level="info")

    except (KeyboardInterrupt, SystemExit):
        print_and_log(lm.get_string("main_ai.trainer_finished", default="Trainer service interrupted."), level="info")
    except Exception as e_main:
        print_and_log(
            lm.get_string("main_ai.fatal_error", default="FATAL ERROR in AI Process: {error}", error=e_main),
            level="error",
        )
        sys.exit(1)
    finally:
        print_and_log(lm.get_string("main_ai.process_exiting", default="--- AI Process Exiting ---"))
        os._exit(0)
