# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Description:
The "Actuator" of the environment: expert in applying actions safely.
Delegates hardware communication directly to the ConnectionManager.
"""

import configparser
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend
    from engine.state_extractor import StateExtractor
    from controller.connection_manager import HardwareConnectionManager

from utils.safety_rules import SafetyRules


class ActionSupervisor:
    """
    The "Actuator" of the environment: expert in applying actions safely.
    Delegates hardware communication directly to the ConnectionManager.
    """

    def __init__(
        self,
        connection_manager: "HardwareConnectionManager",
        settings: configparser.ConfigParser,
        state_extractor: "StateExtractor",
        locale_manager: "LocaleManagerBackend",
    ):

        self.connection_manager = connection_manager
        self.state_extractor = state_extractor
        self.locale_manager = locale_manager
        self.lm = self.locale_manager

        self._last_stage_change_time = {}
        self.vetoed_actions = {}
        self._last_sent_action = {}
        self.override_states = {}

        # Load minimum safety time rules
        self.green_time = SafetyRules.get_green()

        logging.info(
            self.lm.get_string(
                "action_supervisor.init.actuator_created",
                fallback="ActionSupervisor initialized with ConnectionManager.",
            )
        )

    def update_vetos(self, vetos: dict):
        """Updates the list of actions vetoed by the Safety Layer (Guardian)."""
        if vetos:
            for tl_id, veto_signal in vetos.items():
                if isinstance(veto_signal, dict):
                    self.vetoed_actions[tl_id] = veto_signal.get("veto_action")
                elif isinstance(veto_signal, (int, float)):
                    self.vetoed_actions[tl_id] = 0 if veto_signal > 0.8 else None

    @staticmethod
    def _possible_ids(tl_id: str) -> List[str]:
        s_id = str(tl_id)
        if s_id.startswith("tl_"):
            return [s_id, s_id[3:]]
        return [s_id, f"tl_{s_id}"]

    def _resolve_active_driver(self, tl_id: str) -> Optional[Any]:
        active = getattr(self.connection_manager, "active_connections", None)
        if not isinstance(active, dict):
            return None
        for pid in self._possible_ids(tl_id):
            if pid in active:
                return active[pid]
        return None

    def _get_override_state(self, tl_id: str) -> Optional[str]:
        for pid in self._possible_ids(tl_id):
            if pid in self.override_states:
                return self.override_states[pid]
        return None

    def _get_stage_metadata(self, tl_id: str) -> Tuple[List[int], Dict[int, str]]:
        green_stages: List[int] = []
        stage_codes: Dict[int, str] = {}
        green_map = getattr(self.state_extractor, "tl_green_stages", None)
        if isinstance(green_map, dict):
            for pid in self._possible_ids(tl_id):
                val = green_map.get(pid)
                if isinstance(val, (list, tuple)) and len(val) > 0:
                    green_stages = [int(x) for x in val]
                    break
        codes_map = getattr(self.state_extractor, "tl_stage_codes", None)
        if isinstance(codes_map, dict):
            for pid in self._possible_ids(tl_id):
                val = codes_map.get(pid)
                if isinstance(val, dict) and len(val) > 0:
                    stage_codes = dict(val)
                    break
        return green_stages, stage_codes

    def apply_actions(
        self,
        actions: Dict[str, int],
        current_sim_time: float = 0.0,
        current_stages: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Executes AI-recommended actions on respective hardware drivers.
        """
        for tl_id, action in list(actions.items()):
            # 1. Check Guardian Veto
            if tl_id in self.vetoed_actions and self.vetoed_actions[tl_id] == action:
                logging.info(
                    self.lm.get_string(
                        "action_supervisor.veto_blocked",
                        default="[{tl_id}] Action blocked by Guardian veto.",
                        tl_id=tl_id,
                    )
                )
                del self.vetoed_actions[tl_id]
                actions[tl_id] = 1  # Force to HOLD
                action = 1

            # 2. Dispatch non-vetoed NEXT_STAGE (0) commands to physical hardware
            if action == 0:
                if self._get_override_state(tl_id) in ("ALERT", "OFF"):
                    continue
                driver = self._resolve_active_driver(tl_id)
                if driver and getattr(driver, "is_connected", True):
                    green_stages, stage_codes = self._get_stage_metadata(tl_id)
                    stage_idx = int((current_stages or {}).get(tl_id, 0) or 0)
                    if (
                        green_stages
                        and hasattr(driver, "apply_logical_action")
                        and callable(driver.apply_logical_action)
                    ):
                        driver.apply_logical_action(0, stage_idx, green_stages, stage_codes)
                    elif hasattr(driver, "apply_decision") and callable(driver.apply_decision):
                        driver.apply_decision("ADVANCE")

    def send_stage_hold(
        self,
        tl_id: str,
        stage_idx: int,
        stage_codes: Optional[Dict[int, str]] = None,
    ) -> None:
        """
        Sends the hold command for the specified stage (with 0-based stage_idx and stage_codes)
        to the hardware driver.
        """
        override_state = self._get_override_state(tl_id)
        if override_state in ("ALERT", "OFF"):
            logging.debug(
                self.lm.get_string(
                    "action_supervisor.override_active",
                    default="[{tl_id}] Skipping send_stage_hold because of active override: {state}",
                    tl_id=tl_id,
                    state=override_state,
                )
            )
            return

        driver = self._resolve_active_driver(tl_id)
        if driver:
            if stage_codes is None:
                _, stage_codes = self._get_stage_metadata(tl_id)

            action_payload: Dict[str, Any] = {
                "action_type": "hold",
                "stage": int(stage_idx) + 1,
                "stage_idx": int(stage_idx),
            }
            if stage_codes:
                action_payload["stage_codes"] = dict(stage_codes)

            if hasattr(driver, "apply_action") and callable(driver.apply_action):
                driver.apply_action(action_payload)
            elif hasattr(driver, "apply_decision") and callable(driver.apply_decision):
                driver.apply_decision("HOLD")

    def send_decision(self, tl_id: str, decision: str) -> None:
        """Sends pure high-level AI decision ('HOLD' or 'ADVANCE') to the driver."""
        if self._get_override_state(tl_id) in ("ALERT", "OFF"):
            return
        driver = self._resolve_active_driver(tl_id)
        if driver:
            if hasattr(driver, "apply_decision"):
                driver.apply_decision(decision)
            elif decision.upper() == "HOLD":
                driver.apply_action({"action_type": "hold"})

    def record_stage_change(self, tl_id: str, sim_time: float) -> None:
        """Records the simulation timestamp of a confirmed stage transition for tl_id."""
        self._last_stage_change_time[tl_id] = sim_time

    def get_last_stage_change_time(self, tl_id: str, default: float = 0.0) -> float:
        """Returns the simulation timestamp of the last confirmed stage transition for tl_id."""
        return float(self._last_stage_change_time.get(tl_id, default))

    def cleanup_intersection(self, tl_id: str) -> None:
        """Removes all cached states and override flags for a disconnected intersection."""
        for pid in self._possible_ids(tl_id):
            self._last_stage_change_time.pop(pid, None)
            self.vetoed_actions.pop(pid, None)
            self._last_sent_action.pop(pid, None)
            self.override_states.pop(pid, None)

    def reset(self):
        """Clears metrics for a clean restart."""
        self._last_stage_change_time.clear()
        self.vetoed_actions.clear()
        self._last_sent_action.clear()
        self.override_states.clear()

    def apply_hardware_override(self, tl_id: str, state: str):
        """
        Interprets and sends manual UI override commands (e.g. FLASH, DARK) directly to the hardware connection.
        """
        if tl_id == "ALL" and state == "SHUTDOWN":
            for driver in self.connection_manager.active_connections.values():
                logging.critical(
                    self.lm.get_string(
                        "action_supervisor.shutdown_global",
                        default="[ActionSupervisor] Global SHUTDOWN: Stopping heartbeat for traffic light {ip}",
                        ip=driver.ip_address,
                    )
                )
                driver.shutdown()
            return

        driver = self._resolve_active_driver(tl_id)
        if driver is not None:
            if state == "ALERT":
                self.override_states[tl_id] = "ALERT"
                driver.apply_action({"action_type": "flash"})
                driver.log_carina_override("ALERT")
                logging.info(
                    self.lm.get_string(
                        "action_supervisor.flash_sent",
                        default="[{tl_id}] FLASH (Alert) command sent to hardware via ActionSupervisor.",
                        tl_id=tl_id,
                    )
                )
            elif state == "OFF":
                self.override_states[tl_id] = "OFF"
                driver.apply_action({"action_type": "dark"})
                driver.log_carina_override("OFF")
                logging.info(
                    self.lm.get_string(
                        "action_supervisor.dark_sent",
                        default="[{tl_id}] DARK (Off) command sent to hardware via ActionSupervisor.",
                        tl_id=tl_id,
                    )
                )
            elif state == "NORMAL":
                prev_state = None
                for pid in self._possible_ids(tl_id):
                    if pid in self.override_states:
                        prev_state = self.override_states.pop(pid, None)
                if prev_state == "ALERT":
                    driver.apply_action({"action_type": "release_flash"})
                elif prev_state == "OFF":
                    driver.apply_action({"action_type": "release_dark"})
                logging.info(
                    self.lm.get_string(
                        "action_supervisor.normal_returned",
                        default="[{tl_id}] Traffic light returned to normal operation by operator.",
                        tl_id=tl_id,
                    )
                )
