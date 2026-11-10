# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from unittest.mock import MagicMock


class _MockNoSuchProcess(RuntimeError):
    pass


class _MockZombieProcess(RuntimeError):
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
