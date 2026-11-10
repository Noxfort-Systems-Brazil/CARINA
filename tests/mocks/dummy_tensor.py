# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

class DummyTensor:
    """Mock tensor object implementing core PyTorch tensor operations for tests."""

    def __init__(self, data, shape=None, dtype=None):
        self._data = data
        self.dtype = dtype or "float32"
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

    def index_put_(self, *args, **kwargs):
        return self

    def t(self):
        if hasattr(self, "shape") and len(self.shape) == 2:
            return DummyTensor(self._data, shape=(self.shape[1], self.shape[0]), dtype=self.dtype)
        return self

    def contiguous(self):
        return self

    def numpy(self):
        import numpy as np

        if hasattr(self, "shape") and isinstance(self.shape, tuple) and len(self.shape) > 0:
            return np.zeros(self.shape)
        return np.zeros((8,))

    def size(self, dim=None):
        if hasattr(self, "shape") and isinstance(self.shape, (tuple, list)):
            if dim is not None:
                try:
                    return self.shape[dim]
                except (IndexError, TypeError):
                    return 1
            return tuple(self.shape)
        if dim is not None:
            return 1
        return ()

    def unsqueeze(self, dim=0, *args, **kwargs):
        if hasattr(self, "shape") and isinstance(self.shape, tuple):
            new_shape = list(self.shape)
            idx = dim if dim >= 0 else len(new_shape) + 1 + dim
            new_shape.insert(idx, 1)
            return DummyTensor(self._data, shape=tuple(new_shape))
        return self

    def expand(self, *sizes):
        if len(sizes) == 1 and isinstance(sizes[0], (tuple, list)):
            sizes = sizes[0]
        new_shape = list(self.shape) if hasattr(self, "shape") and isinstance(self.shape, tuple) else []
        expanded = []
        for i, s in enumerate(sizes):
            if s == -1:
                expanded.append(new_shape[i] if i < len(new_shape) else 1)
            else:
                expanded.append(s)
        return DummyTensor(self._data, shape=tuple(expanded))

    def squeeze(self, dim=None, *args, **kwargs):
        if hasattr(self, "shape") and isinstance(self.shape, tuple):
            if dim is None:
                new_shape = [s for s in self.shape if s != 1]
            else:
                idx = dim if dim >= 0 else len(self.shape) + dim
                new_shape = [s for i, s in enumerate(self.shape) if i != idx or s != 1]
            return DummyTensor(self._data, shape=tuple(new_shape))
        return self

    def view(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            return DummyTensor(self._data, shape=tuple(args[0]))
        elif len(args) > 0:
            return DummyTensor(self._data, shape=tuple(args))
        return self

    def dim(self):
        return len(self.shape) if hasattr(self, "shape") and isinstance(self.shape, tuple) else 1

    def transpose(self, dim0, dim1):
        if hasattr(self, "shape") and isinstance(self.shape, tuple):
            new_shape = list(self.shape)
            if len(new_shape) > max(dim0, dim1):
                new_shape[dim0], new_shape[dim1] = new_shape[dim1], new_shape[dim0]
            return DummyTensor(self._data, shape=tuple(new_shape))
        return self

    def item(self):
        val = self._data
        while isinstance(val, (list, tuple)) and len(val) == 1:
            val = val[0]
        if hasattr(val, "item"):
            try:
                return val.item()
            except (ValueError, RuntimeError):
                return val
        return val



    def __len__(self):
        if hasattr(self, "shape") and isinstance(self.shape, (tuple, list)) and len(self.shape) > 0:
            return self.shape[0]
        if isinstance(self._data, (list, tuple, dict)):
            return len(self._data)
        return 0

    def max(self, *args, **kwargs):
        val = 1.0 if self._data is None else self._data
        return DummyTensor(val, shape=()), DummyTensor(0, shape=())

    def __getitem__(self, idx):
        sub_data = None
        if self._data is not None:
            try:
                k = idx.item() if hasattr(idx, "item") else idx
                sub_data = self._data[k]
            except Exception:
                try:
                    sub_data = self._data[idx]
                except Exception:
                    sub_data = None

        is_scalar_tensor = isinstance(idx, DummyTensor) and len(getattr(idx, "shape", ())) == 0
        if not is_scalar_tensor and (
            isinstance(idx, (list, tuple, DummyTensor))
            or (hasattr(idx, "__iter__") and not isinstance(idx, (str, bytes)))
        ):
            num = len(idx) if hasattr(idx, "__len__") else getattr(idx, "shape", [1])[0]
            if hasattr(self, "shape") and isinstance(self.shape, tuple) and len(self.shape) > 1:
                return DummyTensor(sub_data, shape=(num, *self.shape[1:]), dtype=self.dtype)
            return DummyTensor(sub_data, shape=(num,), dtype=self.dtype)

        if isinstance(idx, slice):
            if hasattr(self, "shape") and isinstance(self.shape, tuple):
                return DummyTensor(sub_data, shape=self.shape, dtype=self.dtype)

        if hasattr(self, "shape") and isinstance(self.shape, tuple) and len(self.shape) > 1:
            return DummyTensor(sub_data, shape=self.shape[1:], dtype=self.dtype)
        if sub_data is not None:
            return DummyTensor(sub_data, shape=(), dtype=self.dtype)
        return DummyTensor(0, shape=(), dtype=self.dtype)

    @property
    def device(self):
        return "cpu"

    @property
    def is_cuda(self):
        return False

    def detach(self):
        return self

    def clone(self):
        return self

    def repeat(self, *args, **kwargs):
        return self

    def reshape(self, *args, **kwargs):
        s = args[0] if len(args) == 1 and isinstance(args[0], (tuple, list)) else args
        return DummyTensor(self._data, shape=tuple(s), dtype=self.dtype)

    def __mul__(self, other):
        return self

    def __rmul__(self, other):
        return self

    def __add__(self, other):
        return self

    def __radd__(self, other):
        return self

    def __sub__(self, other):
        return self

    def __rsub__(self, other):
        return self

    def __neg__(self):
        return self

    def __gt__(self, other):
        return True

    def __ge__(self, other):
        return True

    def __lt__(self, other):
        return False

    def __le__(self, other):
        return False

    def __setitem__(self, idx, value):
        if self._data is None:
            self._data = {}
        if isinstance(self._data, dict):
            idx_keys = (
                idx._data
                if isinstance(idx, DummyTensor) and isinstance(idx._data, list)
                else (idx if isinstance(idx, (list, tuple)) else None)
            )
            val_items = (
                value._data
                if isinstance(value, DummyTensor) and isinstance(value._data, list)
                else (value if isinstance(value, (list, tuple)) else None)
            )
            if idx_keys is not None and val_items is not None:
                for k, v in zip(idx_keys, val_items):
                    k_key = k.item() if hasattr(k, "item") else k
                    if isinstance(k_key, list):
                        k_key = tuple(k_key)
                    v_val = v._data if hasattr(v, "_data") else v
                    self._data[k_key] = v_val
            else:
                idx_key = idx._data if hasattr(idx, "_data") else idx
                if isinstance(idx_key, list):
                    idx_key = tuple(idx_key)
                val = value._data if hasattr(value, "_data") else value
                self._data[idx_key] = val


    def zero_(self):
        return self

    def fill_(self, value):
        self._data = value
        return self

    def normal_(self, *args, **kwargs):
        return self

    def uniform_(self, *args, **kwargs):
        return self

    def requires_grad_(self, requires_grad: bool = True):
        self.requires_grad = requires_grad
        return self

    def backward(self, *args, **kwargs):
        pass

    def masked_fill(self, mask, value):
        return DummyTensor(self._data, shape=self.shape, dtype=self.dtype)

    def masked_fill_(self, mask, value):
        return self

    def log(self):
        return DummyTensor(self._data, shape=self.shape, dtype=self.dtype)

    def exp(self):
        return DummyTensor(self._data, shape=self.shape, dtype=self.dtype)

    def sqrt(self):
        return DummyTensor(self._data, shape=self.shape, dtype=self.dtype)

    def clamp(self, *args, **kwargs):
        return DummyTensor(self._data, shape=self.shape, dtype=self.dtype)

    def clamp_(self, *args, **kwargs):
        return self

    def permute(self, *dims):
        if len(dims) == 1 and isinstance(dims[0], (tuple, list)):
            dims = tuple(dims[0])
        if hasattr(self, "shape") and isinstance(self.shape, tuple) and len(dims) == len(self.shape):
            new_shape = tuple(self.shape[d] for d in dims)
            return DummyTensor(self._data, shape=new_shape, dtype=self.dtype)
        return self

    def flatten(self, start_dim: int = 0, end_dim: int = -1):
        if hasattr(self, "shape") and isinstance(self.shape, tuple) and len(self.shape) > 0:
            ndim = len(self.shape)
            s = start_dim if start_dim >= 0 else ndim + start_dim
            e = end_dim if end_dim >= 0 else ndim + end_dim
            s = max(0, min(s, ndim - 1))
            e = max(s, min(e, ndim - 1))
            flat_dim = 1
            for d in self.shape[s : e + 1]:
                flat_dim *= d if isinstance(d, int) else 1
            new_shape = (*self.shape[:s], flat_dim, *self.shape[e + 1 :])
            return DummyTensor(self._data, shape=new_shape, dtype=self.dtype)
        return self

    def gather(self, dim: int, index):
        out_shape = getattr(index, "shape", self.shape)
        return DummyTensor(self._data, shape=out_shape, dtype=self.dtype)

    def sort(self, dim: int = -1, descending: bool = False):
        return (
            DummyTensor(self._data, shape=self.shape, dtype=self.dtype),
            DummyTensor(0, shape=self.shape, dtype="int64"),
        )

    def topk(self, k: int, dim: int = -1, largest: bool = True, sorted: bool = True):
        if hasattr(self, "shape") and isinstance(self.shape, tuple) and len(self.shape) > 0:
            new_shape = list(self.shape)
            idx = dim if dim >= 0 else len(new_shape) + dim
            if 0 <= idx < len(new_shape):
                new_shape[idx] = k
            out_shape = tuple(new_shape)
        else:
            out_shape = (k,)
        return (
            DummyTensor(self._data, shape=out_shape, dtype=self.dtype),
            DummyTensor(0, shape=out_shape, dtype="int64"),
        )

    def chunk(self, chunks: int, dim: int = 0):
        if hasattr(self, "shape") and isinstance(self.shape, tuple) and len(self.shape) > 0:
            new_shape = list(self.shape)
            idx = dim if dim >= 0 else len(new_shape) + dim
            if 0 <= idx < len(new_shape) and isinstance(new_shape[idx], int):
                new_shape[idx] = max(1, new_shape[idx] // max(1, chunks))
            return tuple(DummyTensor(self._data, shape=tuple(new_shape), dtype=self.dtype) for _ in range(chunks))
        return tuple(DummyTensor(self._data, shape=self.shape, dtype=self.dtype) for _ in range(chunks))

    def unbind(self, dim: int = 0):
        n = 1
        out_shape = ()
        if hasattr(self, "shape") and isinstance(self.shape, tuple) and len(self.shape) > 0:
            idx = dim if dim >= 0 else len(self.shape) + dim
            if 0 <= idx < len(self.shape):
                n = self.shape[idx] if isinstance(self.shape[idx], int) else 1
                out_shape = tuple(s for i, s in enumerate(self.shape) if i != idx)
        return tuple(DummyTensor(self._data, shape=out_shape, dtype=self.dtype) for _ in range(max(1, n)))

    def any(self, *args, **kwargs):
        return True

    def all(self, *args, **kwargs):
        return True

    def __invert__(self):
        return self

    def pow(self, exp):
        return self

    def __pow__(self, exp):
        return self

    def sum(self, dim=None, keepdim: bool = False, *args, **kwargs):
        if dim is not None and hasattr(self, "shape") and isinstance(self.shape, tuple) and len(self.shape) > 0:
            idx = dim if dim >= 0 else len(self.shape) + dim
            if 0 <= idx < len(self.shape):
                if keepdim:
                    new_shape = tuple(1 if i == idx else s for i, s in enumerate(self.shape))
                else:
                    new_shape = tuple(s for i, s in enumerate(self.shape) if i != idx)
                return DummyTensor(1.0, shape=new_shape, dtype=self.dtype)
        return DummyTensor(1.0, shape=(), dtype=self.dtype)

    def mean(self, dim=None, keepdim: bool = False, *args, **kwargs):
        if dim is not None and hasattr(self, "shape") and isinstance(self.shape, tuple) and len(self.shape) > 0:
            if isinstance(dim, (tuple, list)):
                dims = {d if d >= 0 else len(self.shape) + d for d in dim}
                if keepdim:
                    new_shape = tuple(1 if i in dims else s for i, s in enumerate(self.shape))
                else:
                    new_shape = tuple(s for i, s in enumerate(self.shape) if i not in dims)
                return DummyTensor(0.5, shape=new_shape, dtype=self.dtype)
            idx = dim if dim >= 0 else len(self.shape) + dim
            if 0 <= idx < len(self.shape):
                if keepdim:
                    new_shape = tuple(1 if i == idx else s for i, s in enumerate(self.shape))
                else:
                    new_shape = tuple(s for i, s in enumerate(self.shape) if i != idx)
                return DummyTensor(0.5, shape=new_shape, dtype=self.dtype)
        return DummyTensor(0.5, shape=(), dtype=self.dtype)

    def var(self, dim=None, keepdim: bool = False, *args, **kwargs):
        return self.mean(dim=dim, keepdim=keepdim)

    def std(self, dim=None, keepdim: bool = False, *args, **kwargs):
        if dim is not None:
            return self.mean(dim=dim, keepdim=keepdim)
        return DummyTensor(1.0, shape=(), dtype=self.dtype)

    def abs(self):
        return self

    def __abs__(self):
        return self

    def float(self):
        return self

    def long(self):
        return self

    def bool(self):
        return DummyTensor(self._data, shape=self.shape, dtype="bool")

    def int(self):
        return DummyTensor(self._data, shape=self.shape, dtype="int64")

    def __truediv__(self, other):
        return self

    def __rtruediv__(self, other):
        return self

    def __matmul__(self, other):
        if (
            hasattr(self, "shape")
            and hasattr(other, "shape")
            and isinstance(self.shape, tuple)
            and isinstance(other.shape, tuple)
            and len(self.shape) >= 2
            and len(other.shape) >= 2
        ):
            return DummyTensor(self._data, shape=(*self.shape[:-1], other.shape[-1]), dtype=self.dtype)
        return self
