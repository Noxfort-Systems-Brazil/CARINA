# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class RewardCalculator:
    """
    The environment 'Judge': calculates multi-objective traffic engineering rewards
    combining waiting time, discharge flow, Max-Pressure queue balance, non-linear
    spillback saturation penalties, phase-switch hysteresis, and road safety events
    (emergency braking and gridlock teleports).
    """

    SPILLBACK_OCCUPANCY_THRESHOLD: float = 0.80

    def __init__(self, settings: configparser.ConfigParser, locale_manager: "LocaleManagerBackend") -> None:
        self.locale_manager = locale_manager
        lm = self.locale_manager
        self.last_step_total_flow = 0
        self.last_reward_breakdown: Dict[str, Dict[str, float]] = {}

        default_weights = {
            "waiting_time": -1.0,
            "flow": 1.0,
            "queue_pressure": -0.5,
            "spillback": -25.0,
            "phase_switch": -2.0,
            "emergency_brake": -50.0,
            "teleport": -300.0,
        }

        try:
            section = settings["REWARD_WEIGHTS"]
            self.reward_weights = {
                "waiting_time": float(section.getfloat("weight_waiting_time")),
                "flow": float(section.getfloat("weight_flow")),
                "queue_pressure": self._safe_section_float(section, "weight_queue_pressure", -0.5),
                "spillback": self._safe_section_float(section, "weight_spillback", -25.0),
                "phase_switch": self._safe_section_float(section, "weight_phase_switch", -2.0),
                "emergency_brake": self._safe_section_float(section, "weight_emergency_brake", -50.0),
                "teleport": self._safe_section_float(section, "weight_teleport", -300.0),
            }
        except (configparser.Error, KeyError, TypeError, ValueError):
            if lm:
                logging.error(lm.get_string("reward_calculator.init.config_error"))
            self.reward_weights = dict(default_weights)

        if lm:
            logging.info(lm.get_string("reward_calculator.init.judge_created"))
            logging.info(lm.get_string("reward_calculator.init.weights_loaded", weights=self.reward_weights))

    @staticmethod
    def _safe_section_float(section: Any, key: str, default: float) -> float:
        try:
            if hasattr(section, "__contains__") and key not in section:
                return default
            val = section.getfloat(key, fallback=default)
            return float(val) if isinstance(val, (int, float)) else default
        except (configparser.Error, KeyError, TypeError, ValueError):
            return default

    def set_reward_weights(
        self,
        waiting_time: float,
        flow: float,
        queue_pressure: float | None = None,
        spillback: float | None = None,
        phase_switch: float | None = None,
        emergency_brake: float | None = None,
        teleport: float | None = None,
    ) -> None:
        """Dynamically updates reward weights."""
        self.reward_weights["waiting_time"] = float(waiting_time)
        self.reward_weights["flow"] = float(flow)
        if queue_pressure is not None:
            self.reward_weights["queue_pressure"] = float(queue_pressure)
        if spillback is not None:
            self.reward_weights["spillback"] = float(spillback)
        if phase_switch is not None:
            self.reward_weights["phase_switch"] = float(phase_switch)
        if emergency_brake is not None:
            self.reward_weights["emergency_brake"] = float(emergency_brake)
        if teleport is not None:
            self.reward_weights["teleport"] = float(teleport)
        logging.info(
            f"[RewardCalculator] Reward weights updated: waiting_time={self.reward_weights['waiting_time']:.2f}, "
            f"flow={self.reward_weights['flow']:.2f}"
        )

    @classmethod
    def compute_spillback_severity(cls, occupancy: float) -> float:
        """
        Computes non-linear quadratic spillback severity in [0.0, 1.0]
        when occupancy exceeds SPILLBACK_OCCUPANCY_THRESHOLD (0.80).
        """
        occ = min(max(float(occupancy), 0.0), 1.0)
        if occ <= cls.SPILLBACK_OCCUPANCY_THRESHOLD:
            return 0.0
        excess = (occ - cls.SPILLBACK_OCCUPANCY_THRESHOLD) / (1.0 - cls.SPILLBACK_OCCUPANCY_THRESHOLD)
        return float(excess * excess)

    def calculate_rewards_from_batch(
        self, traffic_light_ids: List[str], current_batch: Dict[str, Any], last_batch: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculates the multi-objective reward for each traffic light using pre-collected data packets.
        """
        rewards: Dict[str, float] = {}
        if not current_batch:
            return rewards

        total_flow_this_step = 0
        self.last_reward_breakdown.clear()

        lane_waiting_map = current_batch.get("lane_waiting_time", {})
        lane_veh_curr = current_batch.get("lane_vehicle_ids", {})
        lane_veh_prev = last_batch.get("lane_vehicle_ids", {}) if last_batch else {}
        lane_queues = current_batch.get("lane_queue_length", {})
        downstream_queues = current_batch.get("downstream_queue_length", {})
        lane_occupancies = current_batch.get("lane_occupancy", {})
        lane_brakes = current_batch.get("lane_emergency_brakes", {})
        tls_teleports = current_batch.get("tls_teleports", {})
        curr_phases = current_batch.get("tls_phases", {})
        prev_phases = last_batch.get("tls_phases", {}) if last_batch else {}

        for tl_id in traffic_light_ids:
            controlled_lanes = current_batch.get("tls_controlled_lanes", {}).get(tl_id, [])
            waiting_time = sum(float(lane_waiting_map.get(lane_id, 0.0)) for lane_id in controlled_lanes)

            flow_bonus = 0
            if last_batch:
                for lane_id in controlled_lanes:
                    vehicles_before = set(lane_veh_prev.get(lane_id, []))
                    vehicles_after = set(lane_veh_curr.get(lane_id, []))
                    flow_bonus += len(vehicles_before - vehicles_after)

            total_flow_this_step += flow_bonus

            # Max-Pressure: |sum(incoming_queues) - sum(downstream_queues)|
            inc_queue = sum(float(lane_queues.get(lane_id, 0.0)) for lane_id in controlled_lanes)
            down_queue = sum(float(downstream_queues.get(lane_id, 0.0)) for lane_id in controlled_lanes)
            pressure = max(0.0, inc_queue - down_queue)

            # Non-linear Spillback saturation penalty
            spillback_severity = sum(
                self.compute_spillback_severity(lane_occupancies.get(lane_id, 0.0)) for lane_id in controlled_lanes
            )

            # Phase-switch hysteresis
            switched = (
                1.0
                if (tl_id in curr_phases and tl_id in prev_phases and curr_phases[tl_id] != prev_phases[tl_id])
                else 0.0
            )

            # Safety penalties: emergency braking & gridlock teleports
            emergency_brakes = sum(float(lane_brakes.get(lane_id, 0.0)) for lane_id in controlled_lanes)
            teleports = float(tls_teleports.get(tl_id, 0.0))

            c_wait = waiting_time * self.reward_weights["waiting_time"]
            c_flow = flow_bonus * self.reward_weights["flow"]
            c_press = pressure * self.reward_weights.get("queue_pressure", 0.0)
            c_spill = spillback_severity * self.reward_weights.get("spillback", 0.0)
            c_switch = switched * self.reward_weights.get("phase_switch", 0.0)
            c_brake = emergency_brakes * self.reward_weights.get("emergency_brake", 0.0)
            c_tele = teleports * self.reward_weights.get("teleport", 0.0)

            total_reward = c_wait + c_flow + c_press + c_spill + c_switch + c_brake + c_tele
            rewards[tl_id] = float(total_reward)
            self.last_reward_breakdown[tl_id] = {
                "waiting_time": c_wait,
                "flow": c_flow,
                "queue_pressure": c_press,
                "spillback": c_spill,
                "phase_switch": c_switch,
                "emergency_brake": c_brake,
                "teleport": c_tele,
                "total": float(total_reward),
            }

        self.last_step_total_flow = total_flow_this_step
        return rewards

    def get_last_reward_breakdown(self, tl_id: str) -> Dict[str, float]:
        """Returns the component-by-component reward breakdown for a traffic light."""
        return dict(self.last_reward_breakdown.get(tl_id, {}))
