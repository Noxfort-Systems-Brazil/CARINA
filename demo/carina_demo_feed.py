# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import math
import queue
import threading
import time
from typing import Any, Dict, Optional

from demo.demo_analysis_responder import DemoAnalysisResponder
from demo.demo_telemetry_generator import DemoTelemetryGenerator
from demo.demo_xai_worker import DemoXAIWorker


class CarinaDemoFeed:
    """
    Simulates real-time telemetry, traffic dynamics, and backend responses
    for CARINA UI demo and presentation recordings.
    """

    def __init__(
        self,
        ui_telemetry_queue: Any,
        ui_command_queue: Any,
        sas_result_queue: Any,
        mfd_trigger_queue: Optional[Any] = None,
        mfd_result_queue: Optional[Any] = None,
        shutdown_event: Optional[threading.Event] = None,
    ):
        self.ui_telemetry_queue = ui_telemetry_queue
        self.ui_command_queue = ui_command_queue
        self.sas_result_queue = sas_result_queue
        self.mfd_trigger_queue = mfd_trigger_queue
        self.mfd_result_queue = mfd_result_queue
        self.shutdown_event = shutdown_event or threading.Event()

        self._running = False
        self._feed_thread: Optional[threading.Thread] = None
        self._command_thread: Optional[threading.Thread] = None
        self._mfd_thread: Optional[threading.Thread] = None
        self._xai_thread: Optional[threading.Thread] = None
        self._evp_thread: Optional[threading.Thread] = None

        self.traffic_lights = ["1116667894", "1193472473", "1193472566", "1193472678"]
        self.semaphore_overrides: Dict[str, str] = {}
        self.street_overrides: Dict[str, str] = {}
        self.street_ids = [
            "370320174#0",
            "104845175",
            "370318891#0",
            "103342115#1",
            "370318865#0",
            "103342093",
            "696403842#0",
        ]
        self.phase_cycle = ["GREEN", "YELLOW", "RED"]

    def start(self):
        """Starts background feed and command listener threads."""
        self._running = True
        self._feed_thread = threading.Thread(target=self._telemetry_loop, name="DemoTelemetryThread", daemon=True)
        self._command_thread = threading.Thread(target=self._command_loop, name="DemoCommandThread", daemon=True)
        self._mfd_thread = threading.Thread(target=self._mfd_loop, name="DemoMfdThread", daemon=True)
        self._xai_thread = threading.Thread(target=self._xai_loop, name="DemoXaiThread", daemon=True)
        self._evp_thread = threading.Thread(target=self._evp_loop, name="DemoEvpThread", daemon=True)

        self._feed_thread.start()
        self._command_thread.start()
        self._mfd_thread.start()
        self._xai_thread.start()
        self._evp_thread.start()
        logging.info("[CarinaDemoFeed] Telemetry, Command, MFD, XAI and EVP demo feeds started.")

    def stop(self):
        """Stops the simulator cleanly."""
        self._running = False
        self.shutdown_event.set()
        logging.info("[CarinaDemoFeed] Demo feed stopped.")

    def _telemetry_loop(self):
        """Continuously dispatches live traffic and semaphore telemetry."""
        step = 0
        while self._running and not self.shutdown_event.is_set():
            try:
                step += 1
                now = time.time()
                packet = DemoTelemetryGenerator.generate_packet(
                    step=step,
                    timestamp=now,
                    traffic_lights=self.traffic_lights,
                    street_ids=self.street_ids,
                    semaphore_overrides=self.semaphore_overrides,
                    street_overrides=self.street_overrides,
                    phase_cycle=self.phase_cycle,
                )
                if self.ui_telemetry_queue:
                    self.ui_telemetry_queue.put(packet)
            except Exception as e:
                logging.warning(f"[CarinaDemoFeed] Error generating telemetry: {e}")
            time.sleep(1.0)

    def _command_loop(self):
        """Listens for UI commands (e.g. semaphore actions, blockage, AI analysis)."""
        while self._running and not self.shutdown_event.is_set():
            if not self.ui_command_queue:
                time.sleep(0.5)
                continue
            try:
                cmd = self.ui_command_queue.get(block=True, timeout=0.5)
                if not cmd or not isinstance(cmd, dict):
                    continue
                cmd_type = cmd.get("type")
                payload = cmd.get("payload", {})

                if cmd_type == "set_semaphore_override":
                    self.semaphore_overrides[payload.get("semaphore_id")] = payload.get("state", "NORMAL")
                elif cmd_type == "set_street_override":
                    self.street_overrides[payload.get("street_id")] = payload.get("state", "NORMAL")
                elif cmd_type == "trigger_analysis":
                    threading.Thread(target=self._dispatch_analysis_response, daemon=True).start()
            except queue.Empty:
                continue
            except Exception as e:
                logging.debug(f"[CarinaDemoFeed] Command loop error: {e}")

    def _dispatch_analysis_response(self):
        DemoAnalysisResponder.dispatch_analysis_response(self.sas_result_queue)

    def _mfd_loop(self):
        """Listens to mfd_trigger_queue and dispatches rich MFD reports to mfd_result_queue."""
        while self._running and not self.shutdown_event.is_set():
            if not self.mfd_trigger_queue:
                time.sleep(0.5)
                continue
            try:
                item = self.mfd_trigger_queue.get(block=True, timeout=0.5)
                if item:
                    time.sleep(1.2)
                    if self.mfd_result_queue:
                        from demo.mock_report_generator import generate_mfd_plot_base64, generate_mfd_text_report
                        self.mfd_result_queue.put({
                            "status": "complete",
                            "image_base64": generate_mfd_plot_base64(),
                            "text_report": generate_mfd_text_report(),
                        })
            except queue.Empty:
                continue
            except Exception as e:
                logging.debug(f"[CarinaDemoFeed] MFD loop error: {e}")

    def _xai_loop(self):
        DemoXAIWorker.run_loop(lambda: self._running, self.shutdown_event)

    @staticmethod
    def _get_street_name(street_id: str) -> str:
        return DemoTelemetryGenerator.get_street_name(street_id)

    def _evp_loop(self):
        """Dispatches continuous dynamic emergency vehicle telemetry and triggers preemption matching EVP_SIMULATOR."""
        from demo.waypoint_kinematics import WaypointVehicle, SAMU_WAYPOINTS, BOMBEIRO_WAYPOINTS, POLICIA_WAYPOINTS
        from src.evp.evp_notifier import EVPNotifier
        import urllib.request
        import json

        samu = WaypointVehicle(
            "SAMU-01", "SAMU", SAMU_WAYPOINTS,
            speed_kmh=68.5, is_loop=True, siren_active=True,
            target_intersection_id="1116667894", target_intersection_xy=(311.94, 854.79)
        )
        bombeiro = WaypointVehicle(
            "BOMBEIRO-01", "BOMBEIRO", BOMBEIRO_WAYPOINTS,
            speed_kmh=45.0, is_loop=False, siren_active=False
        )
        policia = WaypointVehicle(
            "POLICIA-01", "POLICIA", POLICIA_WAYPOINTS,
            speed_kmh=55.0, is_loop=False, siren_active=False
        )
        vehicles = [samu, bombeiro, policia]

        def _async_post_gateway(payload: dict):
            def _post():
                try:
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        "http://127.0.0.1:2201/amb/v1",
                        data=data,
                        headers={"Content-Type": "application/json", "User-Agent": "CARINA-DemoFeed/1.0"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=0.8):
                        pass
                except Exception:
                    pass
            threading.Thread(target=_post, daemon=True).start()

        last_time = time.time()
        while self._running and not self.shutdown_event.is_set():
            try:
                now = time.time()
                dt = min(0.5, max(0.1, now - last_time))
                last_time = now

                for v in vehicles:
                    v.update(dt)
                    payload = v.to_payload()

                    # Handle preemption override on intersection 1116667894
                    if v.vehicle_id == "SAMU-01":
                        if v.is_evp_triggered:
                            self.semaphore_overrides["1116667894"] = "GREEN"
                        elif "1116667894" in self.semaphore_overrides and self.semaphore_overrides["1116667894"] == "GREEN":
                            self.semaphore_overrides.pop("1116667894", None)

                    # 1. Local Flet Desktop dispatch
                    EVPNotifier.get_instance().notify(payload)

                    # 2. Web Gateway CCO dispatch
                    _async_post_gateway(payload)

            except Exception as e:
                logging.debug(f"[CarinaDemoFeed] EVP loop error: {e}")

            time.sleep(0.35)
