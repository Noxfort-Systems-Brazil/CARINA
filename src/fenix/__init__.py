# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/fenix/__init__.py
# Author: Gabriel Moraes
# Date: September 25, 2026

"""
CARINA F.E.N.I.X. (Fail-safe Evolutionary Neural Inference eXchange)
Package for auto-resurrection, crash recovery, and state reconciliation (Option B).
"""

from src.fenix.fenix_supervisor import FenixSupervisor
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
    "StateReconciler",
    "FenixSupervisor",
]
