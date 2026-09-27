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

# File: tests/mocks/torch_mock.py
# Author: Gabriel Moraes
# Date: September 2026

import importlib.machinery
import sys
from unittest.mock import MagicMock

mock_nn = MagicMock()


class Module:
    pass


mock_nn.Module = Module


class DummyTensor:
    def __init__(self, data, shape=None):
        self._data = data
        if shape is not None:
            self.shape = shape
        else:
            try:
                if isinstance(data, list):
                    if len(data) > 0 and isinstance(data[0], list):
                        self.shape = (len(data), len(data[0]))
                    else:
                        self.shape = (len(data),)
                elif hasattr(data, "shape"):
                    self.shape = data.shape
                else:
                    self.shape = ()
            except Exception:
                self.shape = ()

    def to(self, *args, **kwargs):
        return self

    def cpu(self):
        return self

    def numpy(self):
        import numpy as np

        return np.zeros((10, 10))

    def size(self, dim=None):
        if dim is not None:
            return self.shape[dim] if len(self.shape) > dim else 1
        return self.shape

    def unsqueeze(self, dim=0, *args, **kwargs):
        if hasattr(self, "shape") and isinstance(self.shape, tuple):
            new_shape = list(self.shape)
            idx = dim if dim >= 0 else len(new_shape) + 1 + dim
            new_shape.insert(idx, 1)
            return DummyTensor(self._data, shape=tuple(new_shape))
        return self

    def item(self):
        return self._data

    def max(self, *args, **kwargs):
        return DummyTensor(None, shape=()), DummyTensor(0, shape=())

    def __getitem__(self, idx):
        if isinstance(idx, tuple):
            return DummyTensor(0)
        try:
            sub = self._data[idx]
            return DummyTensor(sub)
        except Exception:
            return DummyTensor(0)


class DummyTorch:
    class cuda:
        @staticmethod
        def is_available():
            return False

        @staticmethod
        def get_device_name(idx):
            return "Mock CPU"

    nn = mock_nn
    optim = MagicMock()
    distributions = MagicMock()
    amp = MagicMock()

    float32 = "float32"
    long = "long"
    int64 = "int64"
    bool = "bool"
    float = "float"
    double = "double"
    int = "int"

    @staticmethod
    def zeros(shape, *args, **kwargs):
        return DummyTensor(None, shape=shape)

    @staticmethod
    def tensor(data, *args, **kwargs):
        return DummyTensor(data)

    @staticmethod
    def FloatTensor(data, *args, **kwargs):
        return DummyTensor(data)

    @staticmethod
    def LongTensor(data, *args, **kwargs):
        return DummyTensor(data)

    @staticmethod
    def from_numpy(data, *args, **kwargs):
        return DummyTensor(data)

    @staticmethod
    def cat(*args, **kwargs):
        return DummyTensor(None)

    @staticmethod
    def rand(shape, *args, **kwargs):
        return DummyTensor(None, shape=shape)

    @staticmethod
    def save(*args, **kwargs):
        return MagicMock()

    @staticmethod
    def load(*args, **kwargs):
        return MagicMock()

    @staticmethod
    def sparse_coo_tensor(*args, **kwargs):
        shape = kwargs.get("size", (2, 2)) if "size" in kwargs else (args[2] if len(args) > 2 else (2, 2))
        return DummyTensor(None, shape=shape)

    class sparse:
        @staticmethod
        def mm(*args, **kwargs):
            return DummyTensor(None, shape=(2, 2))

    class DeviceMock:
        def __init__(self, type_str):
            self.type = type_str

        def __str__(self):
            return self.type

    class Tensor:
        pass

    @staticmethod
    def device(name):
        return DummyTorch.DeviceMock(name)

    @staticmethod
    def no_grad():
        class NoGradContext:
            def __enter__(self):
                pass

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        return NoGradContext()


def install_dummy_torch():
    """Installs DummyTorch stubs into sys.modules."""
    dummy_torch_instance = DummyTorch()
    dummy_torch_instance.__spec__ = importlib.machinery.ModuleSpec("torch", None)
    dummy_torch_instance.__version__ = "2.2.0"

    sys.modules["torch"] = dummy_torch_instance
    sys.modules["torch.nn"] = DummyTorch.nn
    sys.modules["torch.nn.functional"] = MagicMock()
    sys.modules["torch.nn.utils"] = MagicMock()
    sys.modules["torch.optim"] = DummyTorch.optim
    sys.modules["torch.distributions"] = DummyTorch.distributions
    sys.modules["torch.amp"] = DummyTorch.amp
