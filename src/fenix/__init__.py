# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
CARINA F.E.N.I.X. (Fail-safe Evolutionary Neural Inference eXchange)
Package for auto-resurrection, crash recovery, and state reconciliation (Option B).
"""

from src.fenix.fenix_supervisor import FenixSupervisor
from src.fenix.multiprocessing_runner import MultiprocessingProcessRunner
from src.fenix.process_runner import SubprocessRunner
from src.fenix.protocols import FenixState, IProcessRunner, IProcessSupervisor, IRecoveryPolicy, IStateReconciler
from src.fenix.recovery_policy import WindowedCrashRecoveryPolicy
from src.fenix.state_reconciler import StateReconciler

__all__ = [
    "FenixState",
    "IRecoveryPolicy",
    "IProcessRunner",
    "IStateReconciler",
    "IProcessSupervisor",
    "WindowedCrashRecoveryPolicy",
    "SubprocessRunner",
    "MultiprocessingProcessRunner",
    "StateReconciler",
    "FenixSupervisor",
]
