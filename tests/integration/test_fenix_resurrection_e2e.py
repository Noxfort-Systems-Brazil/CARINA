# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""End-to-end integration test for Watchdog -> FENIX IPC -> ProcessManager resurrection."""

import queue
import time
from unittest.mock import MagicMock

import pytest

from src.fenix.fenix_supervisor import FenixSupervisor
from src.fenix.multiprocessing_runner import MultiprocessingProcessRunner
from src.fenix.protocols import FenixState
from src.fenix.recovery_policy import WindowedCrashRecoveryPolicy
from src.fenix.state_reconciler import StateReconciler
from src.launcher.process_manager import ProcessManager
from src.watchdog.watchdog_logic import Watchdog


@pytest.mark.integration
def test_watchdog_to_fenix_resurrection_e2e():
    """
    Tests end-to-end:
    1. Watchdog detects DNN error and notifies fenix_queue.
    2. ProcessManager background supervision loop consumes message.
    3. FenixSupervisor executes safe resurrection into FROZEN_SYNC.
    4. StateReconciler detects field stage transitions and executes clean handover to NORMAL.
    """
    pm = ProcessManager()
    pm.setup_queues_and_pipes()

    # 1. Setup mock process and runner
    mock_proc = MagicMock()
    mock_proc.pid = 99001
    mock_proc.is_alive.return_value = True

    mock_runner = MagicMock(spec=MultiprocessingProcessRunner)
    mock_runner.pid = 99001
    mock_runner.is_alive = True
    mock_runner._process = mock_proc

    def _mock_spawn(cmd=None, env=None):
        mock_runner.is_alive = True
        new_proc = MagicMock()
        new_proc.pid = 99002
        new_proc.name = "AI_Process"
        mock_runner._process = new_proc
        mock_runner.pid = 99002
        return True

    mock_runner.spawn.side_effect = _mock_spawn

    policy = WindowedCrashRecoveryPolicy(
        max_consecutive_crashes=3,
        crash_window_seconds=60.0,
        restart_backoff_seconds=0.01,
        exponential=False,
    )

    supervisor = FenixSupervisor(runner=mock_runner, recovery_policy=policy)
    pm.fenix_supervisor = supervisor

    # 2. Start ProcessManager FENIX supervision loop
    pm._start_fenix_supervision()

    try:
        # 3. Simulate Watchdog DNN Error trigger with IPC queue
        fenix_q = pm.queues["fenix"]

        def on_fenix_trigger():
            fenix_q.put(("TRIGGER_RESURRECTION", "DNN_ERROR"))

        wd = Watchdog(timeout_ms=300, grace_period_sec=0.1, on_fenix_trigger=on_fenix_trigger)
        wd.trigger_dnn_error("CUDA illegal memory access")

        # 4. Wait for supervision thread to process resurrection
        max_wait = 2.0
        start = time.perf_counter()
        while supervisor.state != FenixState.FROZEN_SYNC and (time.perf_counter() - start) < max_wait:
            time.sleep(0.05)

        assert supervisor.state == FenixState.FROZEN_SYNC
        assert mock_runner.spawn.called
        assert supervisor.child_pid == 99002
        assert pm.p_ai is not None
        assert pm.p_ai.pid == 99002

        # 5. Simulate Option B clean boundary handover via StateReconciler
        reconciler = StateReconciler(on_handover_complete=supervisor.confirm_handover_complete)
        reconciler.reconcile_with_field({"TL_MAIN": 2})

        assert reconciler.is_inference_allowed("TL_MAIN") is False
        assert supervisor.state == FenixState.FROZEN_SYNC

        # Transition to next stage -> unlocks handover
        unlocked = reconciler.on_stage_transition_detected("TL_MAIN", 3)
        assert unlocked is True
        assert reconciler.is_inference_allowed("TL_MAIN") is True
        assert supervisor.state == FenixState.NORMAL

    finally:
        pm.shutdown_all()
