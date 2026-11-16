# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Fast-path and slow-path SDS visualization frame publisher."""

import logging
from multiprocessing import Queue
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class SDSFramePublisher:
    """Publishes fast-path (0.5s) and slow-path rich updates to the SDS dashboard queue."""

    def __init__(
        self,
        sds_data_queue: Queue,
        topology_manager: Any,
        telemetry_aggregator: Any,
        get_string_fn: Callable[..., str],
    ) -> None:
        self.sds_data_queue = sds_data_queue
        self.topology_manager = topology_manager
        self.telemetry_aggregator = telemetry_aggregator
        self._get_string = get_string_fn
        self.last_fast_ui_sync: float = 0.0

    @staticmethod
    def _attach_hardware_status(payload: Dict[str, Any], coordinator: Optional[Any]) -> None:
        if coordinator is None:
            return
        hw_snapshot = coordinator.get_cached_hardware_status()
        if isinstance(hw_snapshot, dict) and hw_snapshot:
            payload["hardware_status"] = hw_snapshot

    def publish(self, frame: Any, current_time: float, coordinator: Optional[Any] = None) -> None:
        """Runs telemetry aggregation and emits fast-path and/or slow-path SDS updates."""
        self.telemetry_aggregator.process_frame(frame)

        # Fast path (0.5s): traffic light phases, maturity, hardware status
        if current_time - self.last_fast_ui_sync >= 0.5:
            self.last_fast_ui_sync = current_time
            fast_payload: Dict[str, Any] = {
                "timestamp": current_time,
                "maturity": getattr(self.topology_manager, "agent_maturity_cache", {}),
                "tls_phases": getattr(self.topology_manager, "tls_phases_cache", {}),
                "edges": {},
            }
            self._attach_hardware_status(fast_payload, coordinator)
            try:
                self.sds_data_queue.put(("hft_rich_update", fast_payload), block=False)
            except Exception as exc:
                logger.debug("[controller] Ignored recoverable error: %s", exc)

        # Slow path: full heatmap and aggregated traffic metrics
        if self.telemetry_aggregator.should_update(current_time):
            if not self.topology_manager.agent_maturity_cache:
                self.topology_manager.try_restore_state()

            rich_payload = self.telemetry_aggregator.compute_rich_payload(
                current_time, self.topology_manager.agent_maturity_cache
            )
            rich_payload["tls_phases"] = getattr(self.topology_manager, "tls_phases_cache", {})
            self._attach_hardware_status(rich_payload, coordinator)

            try:
                self.sds_data_queue.put(("hft_rich_update", rich_payload), block=False)
            except Exception as exc:
                logger.error(
                    self._get_string(
                        "controller.traffic_frame.rich_update_error",
                        default="Error putting rich update on SDS queue: {error}",
                        error=exc,
                    ),
                    exc_info=True,
                )
