# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time
from multiprocessing import Queue
from multiprocessing.connection import Connection
from typing import Any, Dict

from controller.failsafe_manager import FailsafeManager
from controller.topology_manager import TopologyManager

try:
    from src.controller.frame_sanitizer import FrameSanitizer
    from src.controller.sds_frame_publisher import SDSFramePublisher
except ImportError:  # pragma: no cover
    from controller.frame_sanitizer import FrameSanitizer
    from controller.sds_frame_publisher import SDSFramePublisher

logger = logging.getLogger(__name__)


class TrafficFrameProcessor:
    """
    Orchestrates incoming Synapse/hardware traffic frames: failsafe recovery,
    DB recording, P0 telemetry sanitization, AI HFT step dispatch, and SDS publishing.
    """

    OCCUPANCY_MIN = FrameSanitizer.OCCUPANCY_MIN
    OCCUPANCY_MAX = FrameSanitizer.OCCUPANCY_MAX
    SPEED_MIN = FrameSanitizer.SPEED_MIN
    SPEED_MAX = FrameSanitizer.SPEED_MAX
    QUEUE_MIN = FrameSanitizer.QUEUE_MIN
    QUEUE_MAX = FrameSanitizer.QUEUE_MAX
    DENSITY_MIN = FrameSanitizer.DENSITY_MIN
    DENSITY_MAX = FrameSanitizer.DENSITY_MAX

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
        return FrameSanitizer.sanitize_metric(
            val, min_val, max_val, default=default, field_name=field_name, edge_id=edge_id
        )

    def _sanitize_edge_state(self, edge_id: str, state: Any) -> Dict[str, float]:
        return FrameSanitizer.sanitize_edge_state(edge_id, state)

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
        hardware_gateway_coordinator: Any = None,
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
        self.hardware_gateway_coordinator = hardware_gateway_coordinator

        self.is_system_ready = False
        self._proc_warning_threshold_ms = 100.0
        self._sds_publisher = SDSFramePublisher(
            sds_data_queue=sds_data_queue,
            topology_manager=topology_manager,
            telemetry_aggregator=telemetry_aggregator,
            get_string_fn=self._get_string,
        )

    @property
    def _last_fast_ui_sync(self) -> float:
        return self._sds_publisher.last_fast_ui_sync

    @_last_fast_ui_sync.setter
    def _last_fast_ui_sync(self, value: float) -> None:
        self._sds_publisher.last_fast_ui_sync = float(value)

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def set_system_ready(self, state: bool):
        self.is_system_ready = state

    def _dispatch_to_ai(self, traffic_data: Dict[str, Any]) -> None:
        if self.failsafe_manager.failsafe_active:
            logger.debug(
                self._get_string(
                    "controller.traffic_frame.ai_blocked_failsafe",
                    default="[TrafficFrameProcessor] AI dispatch blocked — FixedTimeController is active.",
                )
            )
            return

        coord = getattr(self, "hardware_gateway_coordinator", None)
        if coord is not None:
            tls_telemetry, hw_status, evp_state = coord.get_cached_frame_attachments()
            if isinstance(tls_telemetry, dict) and tls_telemetry:
                traffic_data["tls_telemetry"] = tls_telemetry
            if isinstance(hw_status, dict) and hw_status:
                traffic_data["hardware_status"] = hw_status
            if isinstance(evp_state, dict):
                traffic_data["evp_state"] = evp_state

        try:
            self.ai_pipe_conn.send(("custom", "hft_step", (traffic_data,), {}))
        except Exception as exc:
            logger.error(
                self._get_string(
                    "controller.traffic_frame.ai_send_error", default="Error sending frame to AI: {error}", error=exc
                ),
                exc_info=True,
            )

    def process_traffic_frame(self, frame: Any):
        """
        Processes a single Traffic Frame received from Synapse and triggers the AI cycle.
        Returns processing time in milliseconds.
        """
        t_start = time.perf_counter()

        self.failsafe_manager.attempt_recovery()

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

        current_time = FrameSanitizer.sanitize_timestamp(getattr(frame, "timestamp", 0.0))
        seq_id = FrameSanitizer.sanitize_sequence_id(getattr(frame, "sequence_id", 0))
        traffic_data = {
            "timestamp": current_time,
            "sequence_id": seq_id,
            "edges": FrameSanitizer.build_clean_edges(frame, self.override_manager),
        }

        self._dispatch_to_ai(traffic_data)
        self._sds_publisher.publish(
            frame, current_time, coordinator=getattr(self, "hardware_gateway_coordinator", None)
        )

        proc_delta_ms = (time.perf_counter() - t_start) * 1000
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
