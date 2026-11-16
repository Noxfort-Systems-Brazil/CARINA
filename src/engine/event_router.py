# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time
from multiprocessing.connection import Connection
from typing import Any

from engine.step_processor import StepProcessor
from manager.agent_manager import AgentManager


class EventRouter:
    """
    Orchestrates the infinite WebSocket/Pipe event loop, consuming data until
    a valid message arrives and routing it to the internal Simulation step (StepProcessor)
    or Map update step (Trainer root).
    """

    def __init__(
        self, pipe_conn: Connection, trainer_instance: Any, agent_manager: AgentManager, step_processor: StepProcessor
    ):
        self.pipe_conn = pipe_conn
        self.trainer = trainer_instance
        self.agent_manager = agent_manager
        self.step_processor = step_processor

    def start_continuous_service(self):
        """
        Main Event Loop: Hibernate -> Drain -> Decide.
        """
        logging.info("Trainer entering Active Standby mode (Event-Driven)...")
        last_warn_time = 0

        while self.trainer.is_running:
            try:
                # 1. HIBERNATE: Block until data arrives
                if self.pipe_conn.poll(timeout=None):

                    # 2. DRAIN BUFFER (Conflation)
                    commands = []
                    try:
                        commands.append(self.pipe_conn.recv())
                    except EOFError:
                        self.trainer.is_running = False
                        break

                    while self.pipe_conn.poll():
                        try:
                            commands.append(self.pipe_conn.recv())
                        except EOFError:
                            self.trainer.is_running = False
                            break

                    if not self.trainer.is_running:
                        break

                    hft_command = None
                    dropped_frames = 0

                    for cmd in commands:
                        if not isinstance(cmd, (list, tuple)) or len(cmd) < 3:
                            continue

                        module, func, args = cmd[0], cmd[1], cmd[2]
                        kwargs = cmd[3] if len(cmd) > 3 and isinstance(cmd[3], dict) else {}

                        if module == "custom" and func == "hft_step":
                            if hft_command is not None:
                                dropped_frames += 1
                            hft_command = cmd
                        else:
                            # 3. ROUTE ADMIN COMMANDS IMMEDIATELY
                            self._execute_command(module, func, args, kwargs=kwargs)

                    if dropped_frames > 0:
                        logging.debug(f"[SYNC] Drained {dropped_frames} stale frames.")

                    # 4. ROUTE THE LATEST HFT FRAME
                    if hft_command:
                        hft_kwargs = hft_command[3] if len(hft_command) > 3 and isinstance(hft_command[3], dict) else {}
                        self._execute_command(hft_command[0], hft_command[1], hft_command[2], kwargs=hft_kwargs)

            except (EOFError, KeyboardInterrupt, SystemExit):
                self.trainer.is_running = False
                break
            except Exception as e:
                logging.error(f"Event Loop Error: {e}", exc_info=True)

    def _execute_command(self, module: str, func: str, args: tuple, kwargs: dict = None):
        """Routes unpacked commands to the correct modules."""
        kwargs = kwargs if isinstance(kwargs, dict) else {}
        if module == "custom" and func == "hft_step":
            if not self.trainer.agents:
                if not hasattr(self, "_last_warn_time"):
                    self._last_warn_time = 0
                if time.time() - self._last_warn_time > 5:
                    logging.warning("[HFT] Data received but AGENTS not loaded.")
                    self._last_warn_time = time.time()
            else:
                if not getattr(self, "_ai_started_logged", False):
                    logging.info("--- AI Engine Started Operating (HFT Mode) ---")
                    print("[AI Process] --- AI Engine Started Operating (HFT Mode) ---")
                    self._ai_started_logged = True
                self.step_processor.process_hft_step(args[0], self.trainer.agents)

        elif module == "custom" and func == "load_map":
            self.trainer._load_map(args[0])

        elif module == "system" and func == "save_checkpoint":
            self.agent_manager.save_system_state(
                self.trainer.current_map_path, self.trainer.agents, self.trainer.strategist
            )

        elif module == "hardware" and func == "toggle_connection":
            action = args[2] if len(args) > 2 else "toggle"
            conn_mgr = getattr(self.trainer, "connection_manager", None)
            if not conn_mgr and hasattr(self.step_processor, "action_supervisor"):
                conn_mgr = getattr(self.step_processor.action_supervisor, "connection_manager", None)
            supervisor = getattr(self.trainer, "action_supervisor", None) or getattr(
                self.step_processor, "action_supervisor", None
            )

            try:
                from drivers.go_gateway_client import GoGatewayClient
            except ImportError:
                from src.drivers.go_gateway_client import GoGatewayClient

            if GoGatewayClient.is_remote_gateway_role() and conn_mgr is not None:
                try:
                    from src.drivers.remote_hardware_driver import RemoteHardwareDriverProxy
                    from src.drivers.remote_proxy_synchronizer import sync_remote_driver_proxies
                except ImportError:
                    from drivers.remote_hardware_driver import RemoteHardwareDriverProxy
                    from drivers.remote_proxy_synchronizer import sync_remote_driver_proxies

                hw_status = kwargs.get("hardware_status")
                if isinstance(hw_status, dict):
                    if hasattr(conn_mgr, "update_remote_hardware_status"):
                        conn_mgr.update_remote_hardware_status(hw_status)
                    disconnected = sync_remote_driver_proxies(
                        conn_mgr=conn_mgr,
                        hardware_status=hw_status,
                        pipe_conn=self.pipe_conn,
                        state_extractor=getattr(self.step_processor, "state_extractor", None),
                        prune_missing=True,
                    )
                    if supervisor:
                        for d_id in disconnected:
                            supervisor.cleanup_intersection(d_id)
                elif args:
                    tl_id = str(args[0])
                    ip_addr = str(args[1] or "") if len(args) > 1 else ""
                    active_conns = getattr(conn_mgr, "active_connections", None)
                    if isinstance(active_conns, dict):
                        should_connect = action == "connect" or (action == "toggle" and tl_id not in active_conns)
                        if should_connect:
                            active_conns[tl_id] = RemoteHardwareDriverProxy(
                                intersection_id=tl_id,
                                ip_address=ip_addr,
                                is_connected=True,
                                pipe_conn=self.pipe_conn,
                            )
                        else:
                            removed = active_conns.pop(tl_id, None)
                            if removed and hasattr(removed, "shutdown"):
                                removed.shutdown()
                            if supervisor:
                                supervisor.cleanup_intersection(tl_id)
            elif conn_mgr:
                is_conn = conn_mgr.toggle_connection(args[0], args[1], action=action)
                if not is_conn and supervisor:
                    supervisor.cleanup_intersection(args[0])
            else:
                logging.error("[EventRouter] Cannot toggle connection: HardwareConnectionManager not available.")

        elif module == "hardware" and func == "failsafe_state":
            hw_act = getattr(self.step_processor, "hardware_actuator", None)
            if hw_act is not None and hasattr(hw_act, "reset"):
                hw_act.reset()

        elif module == "hardware" and func == "apply_override":
            supervisor = getattr(self.trainer, "action_supervisor", None) or getattr(
                self.step_processor, "action_supervisor", None
            )
            if supervisor:
                supervisor.apply_hardware_override(args[0], args[1])
            else:
                logging.error("[EventRouter] Cannot apply override: ActionSupervisor not available.")

        elif module == "fenix" and func == "reconcile_stages":
            reconciler = getattr(self.trainer, "state_reconciler", None) or getattr(
                self.step_processor, "state_reconciler", None
            )
            if reconciler:
                stages = args[0] if args and isinstance(args[0], dict) else {}
                reconciler.reconcile_with_field(stages)

        elif module == "system" and func == "shutdown":
            self.trainer.is_running = False
