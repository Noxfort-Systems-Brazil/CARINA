# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock
from tests.mocks.dummy_tensor import DummyTensor


class Module:
    """Mock PyTorch nn.Module for unit testing without full PyTorch framework."""

    def __init__(self, *args, **kwargs):
        self.training = True

    def to(self, *args, **kwargs):
        return self

    def eval(self, *args, **kwargs):
        self.training = False
        return self

    def train(self, mode: bool = True, *args, **kwargs):
        self.training = mode
        return self

    def parameters(self, *args, **kwargs):
        return iter([DummyTensor([0.0])])

    def named_parameters(self, *args, **kwargs):
        return iter([("weight", DummyTensor([0.0]))])

    def buffers(self, *args, **kwargs):
        return iter([])

    def named_buffers(self, *args, **kwargs):
        return iter([])

    def register_buffer(self, name: str, tensor, persistent: bool = True) -> None:
        setattr(self, name, tensor)

    def state_dict(self):
        return {}

    def load_state_dict(self, state, strict: bool = True):
        return MagicMock(missing_keys=[], unexpected_keys=[])

    def modules(self):
        return [self]

    def __call__(self, *args, **kwargs):
        if hasattr(self, "forward"):
            return self.forward(*args, **kwargs)
        return MagicMock()
