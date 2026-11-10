# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import importlib.machinery
import sys
from unittest.mock import MagicMock

from tests.mocks.dummy_module import Module
from tests.mocks.dummy_tensor import DummyTensor

mock_nn = MagicMock()
mock_nn.Module = Module
mock_nn.utils.weight_norm = lambda module, *args, **kwargs: module
mock_nn.utils.parametrizations.weight_norm = lambda module, *args, **kwargs: module


class DummyGradScaler:
    def __init__(self, enabled=True, *args, **kwargs):
        self._enabled = bool(enabled)

    def is_enabled(self):
        return self._enabled

    def scale(self, loss):
        return loss

    def unscale_(self, optimizer):
        pass

    def step(self, optimizer):
        pass

    def update(self):
        pass


class DummyTorch:
    """Mock PyTorch root namespace providing tensors, math functions and mock submodules."""

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
    amp.GradScaler = DummyGradScaler
    backends = MagicMock()
    utils = MagicMock()
    func = None

    float32 = "float32"
    float16 = "float16"
    bfloat16 = "bfloat16"
    long = "long"
    int64 = "int64"
    bool = "bool"
    float = "float"
    double = "double"
    dtype = object

    @staticmethod
    def manual_seed(seed):
        pass

    @staticmethod
    def compile(model, *args, **kwargs):
        return model

    @staticmethod
    def zeros(*shape, **kwargs):
        if len(shape) == 1 and isinstance(shape[0], (tuple, list)):
            s = tuple(shape[0])
        else:
            s = shape
        dt = kwargs.get("dtype", "float32")
        return DummyTensor(None, shape=s, dtype=dt)

    @staticmethod
    def ones(*shape, **kwargs):
        if len(shape) == 1 and isinstance(shape[0], (tuple, list)):
            s = tuple(shape[0])
        else:
            s = shape
        dt = kwargs.get("dtype", "float32")
        return DummyTensor(1.0, shape=s, dtype=dt)

    @staticmethod
    def full(size, fill_value, *args, **kwargs):
        s = tuple(size) if isinstance(size, (tuple, list)) else (size,)
        dt = kwargs.get("dtype", "float32")
        return DummyTensor(fill_value, shape=s, dtype=dt)

    @staticmethod
    def full_like(tensor, fill_value, *args, **kwargs):
        s = getattr(tensor, "shape", ())
        dt = kwargs.get("dtype", getattr(tensor, "dtype", "float32"))
        return DummyTensor(fill_value, shape=s, dtype=dt)

    @staticmethod
    def arange(*args, **kwargs):
        if len(args) == 1:
            start, end, step = 0, int(args[0]), 1
        elif len(args) == 2:
            start, end, step = int(args[0]), int(args[1]), 1
        elif len(args) >= 3:
            start, end, step = int(args[0]), int(args[1]), int(args[2])
        else:
            start, end, step = 0, 1, 1
        vals = list(range(start, end, step))
        dt = kwargs.get("dtype", "int64")
        return DummyTensor(vals, shape=(len(vals),), dtype=dt)

    @staticmethod
    def linspace(start, end, steps, *args, **kwargs):
        n = int(steps)
        dt = kwargs.get("dtype", "float32")
        return DummyTensor([float(start)] * n, shape=(n,), dtype=dt)

    @staticmethod
    def randperm(n, *args, **kwargs):
        cnt = int(n)
        dt = kwargs.get("dtype", "int64")
        return DummyTensor(list(range(cnt)), shape=(cnt,), dtype=dt)

    @staticmethod
    def ones_like(tensor, *args, **kwargs):
        s = getattr(tensor, "shape", ())
        return DummyTensor(1.0, shape=s, dtype=getattr(tensor, "dtype", "float32"))

    @staticmethod
    def zeros_like(tensor, *args, **kwargs):
        s = getattr(tensor, "shape", ())
        return DummyTensor(0.0, shape=s, dtype=getattr(tensor, "dtype", "float32"))

    @staticmethod
    def tensor(data, *args, **kwargs):
        dt = kwargs.get("dtype", "float32")
        return DummyTensor(data, dtype=dt)

    @staticmethod
    def as_tensor(data, *args, **kwargs):
        dt = kwargs.get("dtype", "float32")
        return DummyTensor(data, dtype=dt)

    @staticmethod
    def multinomial(input, num_samples, replacement=False, *args, **kwargs):
        return DummyTensor(list(range(num_samples)), shape=(num_samples,))

    @staticmethod
    def randint(low, high, size, *args, **kwargs):
        s = size if isinstance(size, (tuple, list)) else (size,)
        return DummyTensor(low, shape=s)

    @staticmethod
    def abs(input, *args, **kwargs):
        return input

    @staticmethod
    def squeeze(input, dim=None, *args, **kwargs):
        if hasattr(input, "squeeze"):
            return input.squeeze(dim) if dim is not None else input.squeeze()
        return input

    @staticmethod
    def exp(input, *args, **kwargs):
        return input

    @staticmethod
    def log(input, *args, **kwargs):
        return input

    @staticmethod
    def logsumexp(input, dim=-1, keepdim=False, *args, **kwargs):
        if hasattr(input, "mean"):
            return input.mean(dim=dim, keepdim=keepdim)
        return input

    @staticmethod
    def softmax(input, dim=-1, *args, **kwargs):
        return input

    @staticmethod
    def sqrt(input, *args, **kwargs):
        return input

    @staticmethod
    def clamp(input, *args, **kwargs):
        return input

    @staticmethod
    def where(condition, x, y, *args, **kwargs):
        return x

    @staticmethod
    def min(a, b=None, *args, **kwargs):
        return a

    @staticmethod
    def max(a, b=None, *args, **kwargs):
        if b is None and hasattr(a, "max"):
            return a.max(*args, **kwargs)
        return a

    @staticmethod
    def minimum(a, b, *args, **kwargs):
        return a

    @staticmethod
    def maximum(a, b, *args, **kwargs):
        return a

    @staticmethod
    def sort(input, dim=-1, descending=False, *args, **kwargs):
        if hasattr(input, "sort"):
            return input.sort(dim=dim, descending=descending)
        return input, DummyTensor(0, shape=getattr(input, "shape", ()), dtype="int64")

    @staticmethod
    def topk(input, k, dim=-1, *args, **kwargs):
        if hasattr(input, "topk"):
            return input.topk(k, dim=dim)
        return input, input

    @staticmethod
    def isnan(input, *args, **kwargs):
        return DummyTensor(False, shape=getattr(input, "shape", ()), dtype="bool")

    @staticmethod
    def isinf(input, *args, **kwargs):
        return DummyTensor(False, shape=getattr(input, "shape", ()), dtype="bool")

    @staticmethod
    def isfinite(input, *args, **kwargs):
        return DummyTensor(True, shape=getattr(input, "shape", ()), dtype="bool")

    @staticmethod
    def sum(input, *args, **kwargs):
        if hasattr(input, "sum"):
            return input.sum(*args, **kwargs)
        return DummyTensor(1.0, shape=(), dtype="float32")

    @staticmethod
    def mean(input, *args, **kwargs):
        if hasattr(input, "mean") and isinstance(input, DummyTensor):
            return input.mean(*args, **kwargs)
        return DummyTensor(0.5, shape=(), dtype="float32")

    @staticmethod
    def bmm(input, mat2, *args, **kwargs):
        if hasattr(input, "__matmul__"):
            return input @ mat2
        return input

    @staticmethod
    def matmul(input, other, *args, **kwargs):
        if hasattr(input, "__matmul__"):
            return input @ other
        return input

    @staticmethod
    def allclose(a, b, *args, **kwargs):
        return True

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
    def cat(tensors, dim=0, *args, **kwargs):
        if len(tensors) > 0 and hasattr(tensors[0], "shape") and isinstance(tensors[0].shape, tuple):
            s = list(tensors[0].shape)
            actual_dim = dim if dim >= 0 else len(s) + dim
            if 0 <= actual_dim < len(s):
                total_dim = sum(
                    t.shape[actual_dim] for t in tensors if hasattr(t, "shape") and len(t.shape) > actual_dim
                )
                s[actual_dim] = total_dim
            return DummyTensor(None, shape=tuple(s))
        return DummyTensor(None)

    @staticmethod
    def stack(tensors, dim=0, *args, **kwargs):
        if len(tensors) > 0 and hasattr(tensors[0], "shape") and isinstance(tensors[0].shape, tuple):
            s = list(tensors[0].shape)
            s.insert(dim, len(tensors))
            return DummyTensor(None, shape=tuple(s))
        return DummyTensor(None)

    @staticmethod
    def rand(*size, **kwargs):
        s = size[0] if (len(size) == 1 and isinstance(size[0], (tuple, list))) else size
        return DummyTensor(None, shape=tuple(s))

    @staticmethod
    def randn(*size, **kwargs):
        s = size[0] if (len(size) == 1 and isinstance(size[0], (tuple, list))) else size
        return DummyTensor(None, shape=tuple(s))

    @staticmethod
    def save(obj, f, *args, **kwargs):
        if isinstance(f, str):
            try:
                import pickle
                with open(f, "wb") as fp:
                    pickle.dump(obj, fp)
            except Exception:
                pass
        return MagicMock()

    @staticmethod
    def load(f, *args, **kwargs):
        if isinstance(f, str):
            try:
                import os, pickle
                if os.path.exists(f):
                    with open(f, "rb") as fp:
                        return pickle.load(fp)
            except Exception:
                pass
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

    @staticmethod
    def inference_mode(mode: bool = True):
        return DummyTorch.no_grad()


def install_dummy_torch():
    """Installs DummyTorch stubs into sys.modules."""
    dummy_torch_instance = DummyTorch()
    dummy_torch_instance.__spec__ = importlib.machinery.ModuleSpec("torch", None, is_package=True)
    dummy_torch_instance.__path__ = []
    dummy_torch_instance.__version__ = "2.2.0"

    sys.modules["torch"] = dummy_torch_instance
    sys.modules["torch.nn"] = DummyTorch.nn
    sys.modules["torch.nn.functional"] = DummyTorch.nn.functional
    sys.modules["torch.nn.utils"] = DummyTorch.nn.utils
    sys.modules["torch.nn.utils.parametrizations"] = DummyTorch.nn.utils.parametrizations
    sys.modules["torch.optim"] = DummyTorch.optim
    sys.modules["torch.distributions"] = DummyTorch.distributions
    sys.modules["torch.utils"] = DummyTorch.utils
    sys.modules["torch.utils.tensorboard"] = MagicMock()
    sys.modules["torch.amp"] = DummyTorch.amp
