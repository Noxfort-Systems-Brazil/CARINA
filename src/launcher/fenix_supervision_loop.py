# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Background thread controller for F.E.N.I.X. crash resurrection and handover completion."""

import logging
import queue
import threading
from typing import Any, Callable, Dict, List, Optional


class FenixSupervisionController:
    """Listens on the `fenix` IPC queue and coordinates AI process resurrection and handover."""

    def __init__(
        self,
        get_queues: Callable[[], Dict[str, Any]],
        get_processes: Callable[[], List[Any]],
        get_supervisor: Callable[[], Any],
        on_ai_resurrected: Callable[[Any], None],
        get_stop_event: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._get_queues = get_queues
        self._get_processes = get_processes
        self._get_supervisor = get_supervisor
        self._on_ai_resurrected = on_ai_resurrected
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self._get_stop_event = get_stop_event or (lambda: self.stop_event)

    def _active_stop_event(self) -> Any:
        evt = self._get_stop_event()
        return evt if evt is not None else self.stop_event

    def start(self) -> None:
        if not self._get_supervisor():
            return
        stop_evt = self._active_stop_event()
        if hasattr(stop_evt, "clear"):
            stop_evt.clear()
        self.thread = threading.Thread(
            target=self.run_loop,
            name="FenixSupervisionThread",
            daemon=True,
        )
        self.thread.start()
        logging.info("[ProcessManager] F.E.N.I.X. background supervision thread active.")

    def stop(self) -> None:
        stop_evt = self._active_stop_event()
        if hasattr(stop_evt, "set"):
            stop_evt.set()
        fenix_q = self._get_queues().get("fenix")
        if fenix_q:
            try:
                fenix_q.put_nowait("STOP")
            except Exception:
                pass

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        supervisor = self._get_supervisor()
        if supervisor:
            try:
                supervisor.stop()
            except Exception:
                pass

    def _notify_ui_post_resurrection(self, reason: str, new_proc: Any) -> None:
        ui_q = self._get_queues().get("ui")
        if ui_q is None:
            return
        try:
            ui_q.put_nowait(
                {
                    "type": "fenix_post_resurrection",
                    "payload": {
                        "reason": reason,
                        "new_pid": getattr(new_proc, "pid", None) if new_proc else None,
                    },
                }
            )
        except Exception as e_q:
            logging.warning(f"[ProcessManager] Failed to enqueue fenix_post_resurrection: {e_q}")

    def _handle_resurrection(self, reason: str) -> None:
        logging.critical(
            f"[ProcessManager] 🚨 F.E.N.I.X. resurrection triggered (Reason: {reason}). "
            "Executing AI Engine resurrection..."
        )
        supervisor = self._get_supervisor()
        if not supervisor:
            return

        supervisor.record_child_crash(exit_code=1)
        resurrected = supervisor.resurrect_ai()
        if not resurrected:
            logging.error(
                f"[ProcessManager] ❌ F.E.N.I.X. resurrection halted or failed. Supervisor state: {supervisor.state.value}"
            )
            return

        new_proc = None
        if hasattr(supervisor.runner, "_process"):
            new_proc = supervisor.runner._process
            if new_proc:
                self._on_ai_resurrected(new_proc)
                processes = self._get_processes()
                for idx, proc in enumerate(processes):
                    if proc.name == "AI_Process":
                        processes[idx] = new_proc
                        break
                logging.info(
                    f"[ProcessManager] ✅ F.E.N.I.X. AI Process successfully resurrected! [New PID: {new_proc.pid}]"
                )

        self._notify_ui_post_resurrection(reason, new_proc)

    def run_loop(self) -> None:
        fenix_q = self._get_queues().get("fenix")
        if not fenix_q:
            return

        stop_evt = self._active_stop_event()
        while not stop_evt.is_set():
            try:
                msg = fenix_q.get(timeout=0.5)
            except queue.Empty:
                continue
            except Exception as e:
                logging.debug(f"[ProcessManager] Error reading fenix_q: {e}")
                continue

            if msg == "STOP" or stop_evt.is_set():
                break

            action = msg[0] if isinstance(msg, tuple) else msg
            reason = msg[1] if isinstance(msg, tuple) and len(msg) > 1 else "Unknown"

            if action in ("TRIGGER_RESURRECTION", "CRASH_TRIGGER"):
                self._handle_resurrection(reason)
            elif action == "HANDOVER_COMPLETE":
                supervisor = self._get_supervisor()
                if supervisor and hasattr(supervisor, "confirm_handover_complete"):
                    supervisor.confirm_handover_complete()
                    logging.info("[ProcessManager] ✅ F.E.N.I.X. handover confirmed after stage reconciliation.")
