# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import math
import logging
import time
from multiprocessing import Queue
from multiprocessing.connection import Connection
from typing import Any, Dict

from controller.failsafe_manager import FailsafeManager
from controller.topology_manager import TopologyManager

logger = logging.getLogger(__name__)


class TrafficFrameProcessor:
    """
    Responsible for unpacking hardware/synapse frames and routing them
    correctly to the AI and the UI visual aggregator.

    NOTE: Heartbeat is now sent immediately in the gRPC hot-path (hft_server.py),
    NOT here. This processor runs on the cold-path worker thread.
    """

    # Numerical Sanitization & Clamping Boundaries (P0 Safety Invariants)
    OCCUPANCY_MIN: float = 0.0
    OCCUPANCY_MAX: float = 1.0

    SPEED_MIN: float = 0.0
    SPEED_MAX: float = 100.0  # m/s (~360 km/h)

    QUEUE_MIN: float = 0.0
    QUEUE_MAX: float = 1000.0  # vehicle units / meters

    DENSITY_MIN: float = 0.0
    DENSITY_MAX: float = 1.0

    @classmethod
    def _sanitize_metric(
        cls,
        val: Any,
        min_val: float,
        max_val: float,
        default: float = 0.0,
        field_name: str = "",
        edge_id: str = "",
    ) -> float:
        """
        Validates numeric input using math.isnan() and math.isinf(),
        sanitizing to default on anomalies, and clamps to [min_val, max_val].
        """
        try:
            f_val = float(val) if val is not None else default
        except (ValueError, TypeError):
            logger.warning(
                "[TrafficFrameProcessor] Invalid numeric type for %s on edge %s: %s. Sanitizing to %.2f.",
                field_name,
                edge_id,
                val,
                default,
            )
            return default

        if math.isnan(f_val) or math.isinf(f_val):
            logger.warning(
                "[TrafficFrameProcessor] Numerical anomaly (NaN/Inf) detected for %s on edge %s: %s. Sanitizing to %.2f.",
                field_name,
                edge_id,
                f_val,
                default,
            )
            return default

        return max(min_val, min(max_val, f_val))

    def _sanitize_edge_state(self, edge_id: str, state: Any) -> Dict[str, float]:
        """
        Extracts, validates (math.isnan / math.isinf), and clamps all metrics
        for an edge state before dispatch to PPO and Guardian.
        """
        raw_occ = getattr(state, "occupancy", None) if not isinstance(state, dict) else state.get("occupancy")
        raw_speed = getattr(state, "mean_speed", None) if not isinstance(state, dict) else state.get("mean_speed")
        raw_queue = getattr(state, "queue_length", None) if not isinstance(state, dict) else state.get("queue_length")

        clean_occ = self._sanitize_metric(
            raw_occ, self.OCCUPANCY_MIN, self.OCCUPANCY_MAX, default=0.0, field_name="occupancy", edge_id=edge_id
        )
        clean_speed = self._sanitize_metric(
            raw_speed, self.SPEED_MIN, self.SPEED_MAX, default=0.0, field_name="mean_speed", edge_id=edge_id
        )
        clean_queue = self._sanitize_metric(
            raw_queue, self.QUEUE_MIN, self.QUEUE_MAX, default=0.0, field_name="queue_length", edge_id=edge_id
        )

        edge_data = {
            "occupancy": clean_occ,
            "mean_speed": clean_speed,
            "queue_length": clean_queue,
        }

        raw_density = getattr(state, "density", None) if not isinstance(state, dict) else state.get("density")
        if raw_density is not None:
            edge_data["density"] = self._sanitize_metric(
                raw_density, self.DENSITY_MIN, self.DENSITY_MAX, default=0.0, field_name="density", edge_id=edge_id
            )

        return edge_data

    def __init__(
        self,
        ai_pipe_conn: Connection,
        watchdog_queue: Queue,
        sds_data_queue: Queue,
        failsafe_manager: FailsafeManager,
        topology_manager: TopologyManager,
        telemetry_aggregator: Any,
        override_manager: Any,
        traffic_data_recorder: Any = None,
        locale_manager: Any = None,
    ):
        self.ai_pipe_conn = ai_pipe_conn
        self.watchdog_queue = watchdog_queue
        self.sds_data_queue = sds_data_queue

        self.failsafe_manager = failsafe_manager
        self.topology_manager = topology_manager
        self.telemetry_aggregator = telemetry_aggregator
        self.override_manager = override_manager
        self.traffic_data_recorder = traffic_data_recorder
        self.locale_manager = locale_manager

        # --- Two-Stage Readiness Latch ---
        self.is_system_ready = False

        # --- Processing time tracking ---
        self._proc_warning_threshold_ms = 100.0

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def set_system_ready(self, state: bool):
        self.is_system_ready = state

    def process_traffic_frame(self, frame: Any):
        """
        Processes a single Traffic Frame received from Synapse.
        This is the TRIGGER for the AI Decision Cycle.

        NOTE: Heartbeat is already sent in the gRPC hot-path. This method
        only handles failsafe recovery, AI dispatch, and visualization.

        Returns:
            float: Processing time in milliseconds (for diagnostics).
        """
        t_start = time.perf_counter()

        # 0. RECORD FRAME ARRIVAL
        # REMOVED: Frame arrival is now recorded in hft_server.py (HOT path)
        # to prevent false timeouts due to processing latency.

        # 1. FAILSAFE RECOVERY
        # If we were in failsafe mode and a frame just arrived, Synapse is back.
        # FixedTimeController will deactivate and put all intersections in ALL_RED
        # for a safe handoff back to the Neural Network.
        self.failsafe_manager.attempt_recovery()

        # 1.5 RECORD FRAME TO DATABASE (for historical optimization analysis)
        if self.traffic_data_recorder:
            try:
                self.traffic_data_recorder.record_frame(frame)
            except Exception as rec_err:
                logger.debug(
                    self._get_string(
                        "controller.traffic_frame.recording_error",
                        default="[TrafficFrameProcessor] Data recording error: {error}",
                        error=rec_err,
                    )
                )

        # 2. NORMAL PROCESSING (AI Step)
        raw_ts = getattr(frame, "timestamp", 0.0)
        try:
            current_time = float(raw_ts)
            if math.isnan(current_time) or math.isinf(current_time) or current_time < 0.0:
                logger.warning(
                    "[TrafficFrameProcessor] Anomaly detected: invalid timestamp %s. Sanitizing to 0.0.",
                    raw_ts,
                )
                current_time = 0.0
        except (ValueError, TypeError):
            current_time = 0.0

        raw_seq = getattr(frame, "sequence_id", 0)
        try:
            seq_id = int(raw_seq)
            if seq_id < 0:
                seq_id = 0
        except (ValueError, TypeError):
            seq_id = 0

        traffic_data = {"timestamp": current_time, "sequence_id": seq_id, "edges": {}}

        frame_edges = getattr(frame, "edges", {}) or {}
        if isinstance(frame_edges, dict):
            edge_items = frame_edges.items()
        elif hasattr(frame_edges, "items"):
            edge_items = frame_edges.items()
        else:
            edge_items = []

        # Prepare data for AI (still manual as it is control logic, not visualization)
        for edge_id, state in edge_items:
            # Check if this street is manually blocked by the operator
            # Consider potential sibling/reverse mappings or direct ID
            is_blocked = False
            if self.override_manager and self.override_manager.active_street_overrides:
                if (
                    edge_id in self.override_manager.active_street_overrides
                    and self.override_manager.active_street_overrides[edge_id] == "BLOCKED"
                ):
                    is_blocked = True
                else:
                    # Also check for base or reverse edge IDs to ensure accurate blocking
                    base_sibling = edge_id[1:] if edge_id.startswith("-") else edge_id
                    reverse_sibling = "-" + base_sibling if not edge_id.startswith("-") else base_sibling
                    if (
                        base_sibling in self.override_manager.active_street_overrides
                        and self.override_manager.active_street_overrides[base_sibling] == "BLOCKED"
                    ) or (
                        reverse_sibling in self.override_manager.active_street_overrides
                        and self.override_manager.active_street_overrides[reverse_sibling] == "BLOCKED"
                    ):
                        is_blocked = True

            if is_blocked:
                # If blocked, inform the AI that there is no traffic/flow here
                blocked_data = {"occupancy": 0.0, "mean_speed": 0.0, "queue_length": 0.0}
                if hasattr(state, "density") or (isinstance(state, dict) and "density" in state):
                    blocked_data["density"] = 0.0
                traffic_data["edges"][edge_id] = blocked_data
            else:
                traffic_data["edges"][edge_id] = self._sanitize_edge_state(edge_id, state)

        # AGREEMENT: This is the ONLY place triggering the HFT Step.
        # SAFETY: Do NOT send AI commands while FixedTimeController is active.
        # The fixed-time plan must have exclusive control during failsafe to
        # prevent conflicting signal commands.
        # NOTE (Fix): Removed strict 'is_system_ready' drop so headless mock clients
        # can still trigger AI decisions without needing a UI 'carina_ready' connection.
        if not self.failsafe_manager.failsafe_active:
            try:
                self.ai_pipe_conn.send(("custom", "hft_step", (traffic_data,), {}))
            except Exception as e:
                logger.error(
                    self._get_string(
                        "controller.traffic_frame.ai_send_error", default="Error sending frame to AI: {error}", error=e
                    )
                , exc_info=True)
        else:
            if self.failsafe_manager.failsafe_active:
                logger.debug(
                    self._get_string(
                        "controller.traffic_frame.ai_blocked_failsafe",
                        default="[TrafficFrameProcessor] AI dispatch blocked — FixedTimeController is active.",
                    )
                )
            # Drop AI frame dispatch, but allow visualization to continue.

        # 3. VISUALIZATION AGGREGATION & SYNC
        self.telemetry_aggregator.process_frame(frame)

        # 3.1 FAST PATH (Lightweight Sync for Semaphores/Maturity) -> 0.5s
        if getattr(self, "_last_fast_ui_sync", 0.0) == 0.0:
            self._last_fast_ui_sync = 0.0

        if current_time - self._last_fast_ui_sync >= 0.5:
            self._last_fast_ui_sync = current_time
            fast_payload = {
                "timestamp": current_time,
                "maturity": getattr(self.topology_manager, "agent_maturity_cache", {}),
                "tls_phases": getattr(self.topology_manager, "tls_phases_cache", {}),
                "edges": {},  # Empty edges skips congestion update, preventing flickering
            }
            try:
                self.sds_data_queue.put(("hft_rich_update", fast_payload), block=False)
            except Exception as _exc:
                logger.debug("[controller] Ignored recoverable error: %s", _exc)

        # 3.2 SLOW PATH (Heavy Heatmap Rendering) -> Controller.interval (e.g. 5.0s)
        if self.telemetry_aggregator.should_update(current_time):
            if not self.topology_manager.agent_maturity_cache:
                self.topology_manager.try_restore_state()

            rich_payload = self.telemetry_aggregator.compute_rich_payload(
                current_time, self.topology_manager.agent_maturity_cache
            )

            rich_payload["tls_phases"] = getattr(self.topology_manager, "tls_phases_cache", {})

            try:
                self.sds_data_queue.put(("hft_rich_update", rich_payload), block=False)
            except Exception as e:
                logger.error(
                    self._get_string(
                        "controller.traffic_frame.rich_update_error",
                        default="Error putting rich update on SDS queue: {error}",
                        error=e,
                    )
                , exc_info=True)

        # 4. MEASURE AND DIAGNOSE PROCESSING TIME
        t_end = time.perf_counter()
        proc_delta_ms = (t_end - t_start) * 1000

        if proc_delta_ms > self._proc_warning_threshold_ms:
            logger.warning(
                self._get_string(
                    "controller.traffic_frame.slow_processing",
                    default="[TrafficFrameProcessor] ⏱️ Slow processing: {delta:.1f}ms (>{thresh:.0f}ms). Seq: {seq}",
                    delta=proc_delta_ms,
                    thresh=self._proc_warning_threshold_ms,
                    seq=frame.sequence_id,
                )
            )

        return proc_delta_ms
