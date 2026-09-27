# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/mocks/system_mocks.py
# Author: Gabriel Moraes
# Date: September 2026

import sys
from unittest.mock import MagicMock


class _MockNoSuchProcess(Exception):
    pass


class _MockZombieProcess(Exception):
    pass


class _MockProcess:
    def __init__(self, *args, **kwargs):
        pass

    def cpu_percent(self, *a, **k):
        return 0

    def memory_percent(self):
        return 0

    def children(self, *a, **k):
        return []

    def cmdline(self):
        return []

    def is_running(self):
        return False

    def terminate(self):
        pass

    def kill(self):
        pass


def install_system_mocks():
    """Installs mock stubs for heavy or system libraries (psutil, captum, transformers, etc.)."""
    sys.modules["torch_geometric"] = MagicMock()
    sys.modules["torch_geometric.nn"] = MagicMock()
    sys.modules["torch_geometric.data"] = MagicMock()

    mock_captum_attr = MagicMock()
    mock_captum_attr.IntegratedGradients = MagicMock()
    sys.modules["captum"] = MagicMock()
    sys.modules["captum.attr"] = mock_captum_attr

    mock_transformers = MagicMock()
    mock_transformers.AutoModelForCausalLM = MagicMock()
    mock_transformers.AutoTokenizer = MagicMock()
    sys.modules["transformers"] = mock_transformers

    sys.modules["psutil"] = type(
        "Mock",
        (object,),
        {
            "Process": _MockProcess,
            "NoSuchProcess": _MockNoSuchProcess,
            "ZombieProcess": _MockZombieProcess,
            "wait_procs": staticmethod(lambda *args, **kwargs: ([], [])),
        },
    )()

    sys.modules["cv2"] = type("Mock", (object,), {})()
