# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the logic for the Asynchronous Guardian process.

This version contains the worker's main operation loop, which consumes
simulation states from a queue, executes GuardianAgent inference,
and sends veto signals back to the main process.
"""
import configparser
import logging
import os
import time
from multiprocessing import Queue
from queue import Empty, Full
from typing import Dict, Tuple


def run_guardian_worker(
    settings: configparser.ConfigParser,
    state_queue: Queue,
    signal_queue: Queue,
    scenario_checkpoint_dir: str,
    agent_ids: list,
    pae_state_dict: dict = None,
    pae_config: dict = None,
):
    """
    The entry point and main loop for the Asynchronous Guardian process.
    """

    import torch

    from agents.guardian_agent import GuardianAgent
    from optimizer.dqn_optimizer import DQNOptimizer

    # --- PAE Universal (inference-only copy for subprocess) ---
    from models.pae import PredictiveAutoencoder

    # --- FIX 1: Import the LocaleManagerBackend ---
    from utils.locale_manager_backend import LocaleManagerBackend
    from utils.logging_setup import setup_logging

    # --- TensorCore (TF32/FP16) Hardware Acceleration Optimization (Process Independent) ---
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.backends.cudnn.benchmark = True
    try:
        torch.set_float32_matmul_precision("high")
    except AttributeError:
        pass  # PyTorch versions < 1.12 might not have this, though CARINA requires >= 2.0
    # ------------------------------------------------------------

    # Configure a specific logger for this process
    from utils.paths import get_base_output_dir

    log_dir = os.path.join(get_base_output_dir(), "logs", "guardian_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir)

    # --- FIX 2: Create the LocaleManagerBackend instance ---
    lm = LocaleManagerBackend()

    logging.info(
        lm.get_string(
            "guardian_worker.process_started", default="[GUARDIAN_WORKER] Asynchronous Guardian Process started."
        )
    )

    # --- Reconstruct PAE in inference-only mode (process isolation) ---
    shared_pae_worker = None
    if pae_state_dict and pae_config:
        try:
            shared_pae_worker = PredictiveAutoencoder(**pae_config)
            shared_pae_worker.load_state_dict(pae_state_dict)
            shared_pae_worker.eval()  # Inference-only — no training in subprocess
            logging.info(
                lm.get_string(
                    "guardian_worker.pae_reconstructed",
                    default="[GUARDIAN_WORKER] Universal PAE reconstructed (inference-only)",
                )
            )
        except Exception as e:
            logging.error(
                lm.get_string(
                    "guardian_worker.pae_failed",
                    default="[GUARDIAN_WORKER] Failed to reconstruct PAE: {error}",
                    error=e,
                ),
                exc_info=True,
            )
            shared_pae_worker = None

    # --- Initialization ---
    guardians = {}
    guardian_config = settings["GUARDIAN_AGENT"]
    traffic_rules_config = settings["TRAFFIC_RULES"] if "TRAFFIC_RULES" in settings else guardian_config
    for tl_id in agent_ids:
        guardians[tl_id] = GuardianAgent(
            aiconfig=guardian_config,
            traffic_rules_config=traffic_rules_config,
            locale_manager=lm,
            shared_pae=shared_pae_worker,
        )

    # Global Strategy Optimizer for the Worker (with AMP GradScaler)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    scaler = torch.amp.GradScaler(enabled=(device.type == "cuda"))
    dqn_optimizer = DQNOptimizer(hyperparams=guardian_config, device=device, scaler=scaler)

    logging.info(
        lm.get_string(
            "guardian_worker.guardians_ready",
            default="[GUARDIAN_WORKER] {count} guardians created and ready.",
            count=len(guardians),
        )
    )

    prev_guardian_states: Dict[str, Tuple[torch.Tensor, int]] = {}

    # --- Main Loop ---
    while True:
        try:
            latest_state_package = None

            # 1. Empties the queue to only get the most recent state
            try:
                while True:
                    latest_state_package = state_queue.get_nowait()
            except Empty:
                pass  # Queue is empty, normal.

            # 2. If a status has been received, process it
            if latest_state_package:
                # The package contains the status and rewards
                global_state, rewards, done, mode = latest_state_package

                # THINKING MODE: Generate the Preemptive Veto Map
                veto_map = {}
                is_training_mode = (mode == "training")
                for tl_id, guardian in guardians.items():
                    local_state = global_state.get(tl_id)
                    if not local_state:
                        continue

                    # Background Neural Inference: Predict Spillback Risk
                    risk_score = guardian.evaluate_spillback_risk(local_state, tl_id, is_training=is_training_mode)
                    is_exploratory = guardian.is_exploratory_decision(tl_id)
                    raw_thresh = getattr(guardian, "spillback_risk_threshold", 0.65)
                    veto_thresh = float(raw_thresh) if isinstance(raw_thresh, (int, float)) else 0.65
                    veto_map[tl_id] = {
                        "risk": risk_score,
                        "is_exploratory": is_exploratory,
                        "veto_action": guardian.ACTION_KEEP_STAGE if risk_score >= veto_thresh else None,
                    }

                    # Guardian Learning (if in training mode)
                    if mode == "training" and rewards:
                        curr_seq = guardian._get_temporal_sequence(local_state, tl_id).squeeze(0)
                        if tl_id in prev_guardian_states:
                            prev_seq, prev_act = prev_guardian_states[tl_id]
                            tl_reward = float(rewards.get(tl_id, 0.0))
                            guardian.memory.push(prev_seq, prev_act, curr_seq, tl_reward)

                        chosen_action = (
                            guardian.ACTION_KEEP_STAGE if risk_score >= veto_thresh else guardian.ACTION_CHANGE_STAGE
                        )
                        if done:
                            prev_guardian_states.pop(tl_id, None)
                        else:
                            prev_guardian_states[tl_id] = (curr_seq, chosen_action)

                        raw_steps = getattr(guardian, "steps_done", 0)
                        guardian.steps_done = (int(raw_steps) if isinstance(raw_steps, (int, float)) else 0) + 1

                        if len(guardian.memory) >= getattr(guardian, "batch_size", 128):
                            dqn_optimizer.step(
                                policy_net=guardian.policy_net,
                                target_net=guardian.target_net,
                                optimizer=guardian.optimizer,
                                memory=guardian.memory,
                                forward_policy=guardian.forward_policy,
                                forward_target=guardian.forward_target,
                            )

                            # Polyak soft target update every step (with fallback for legacy mocks)
                            if hasattr(dqn_optimizer, "soft_update_target_net"):
                                dqn_optimizer.soft_update_target_net(guardian.policy_net, guardian.target_net)
                            elif guardian.steps_done % 1000 == 0:
                                dqn_optimizer.update_target_net(guardian.policy_net, guardian.target_net)

                # Broadcast Veto Map to Main Process (Zero-Latency check at inference time)
                if veto_map:
                    try:
                        signal_queue.put_nowait({"type": "veto_map", "map": veto_map})
                    except Full:
                        pass  # If queue is full, drop the map, it will be updated in the next cycle

            # Pause to not consume 100% CPU if there is no work
            time.sleep(0.01)  # Reduced sleep for faster thinking mode

        except (KeyboardInterrupt, SystemExit):
            logging.info(
                lm.get_string("guardian_worker.shutdown", default="[GUARDIAN_WORKER] Shutdown signal received.")
            )
            break
        except Exception as e:
            logging.error(
                lm.get_string(
                    "guardian_worker.fatal_error", default="[GUARDIAN_WORKER] Fatal error in loop: {error}", error=e
                ),
                exc_info=True,
            )
            time.sleep(1)

    logging.info(lm.get_string("guardian_worker.process_finished", default="[GUARDIAN_WORKER] Process finished."))
