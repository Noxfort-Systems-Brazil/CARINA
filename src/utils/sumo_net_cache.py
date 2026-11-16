# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Thread-safe LRU cache for parsed SUMO `.net.xml` topologies within a process."""

import os
import threading
from collections import OrderedDict
from typing import Any, Optional, Tuple

_CACHE_LOCK = threading.Lock()
_NET_CACHE: "OrderedDict[Tuple[str, int, int, bool, bool], Any]" = OrderedDict()
_MAX_CACHE_ENTRIES = 8


def read_sumo_net_cached(
    net_file_path: str,
    reader_fn: Optional[Any] = None,
    with_programs: bool = True,
    with_internal: Optional[bool] = False,
) -> Any:
    """
    Loads a SUMO `.net.xml` file via `sumolib.net.readNet`, reusing cached parsed
    network objects when the file exists on disk, mtime/size match, and the reader is not mocked.
    """
    if reader_fn is None:
        import sumolib  # type: ignore

        reader_fn = sumolib.net.readNet

    kwargs: dict[str, Any] = {}
    if with_internal is not None:
        kwargs["withInternal"] = with_internal
    if with_programs:
        kwargs["withPrograms"] = True

    # Bypass cache when tests mock sumolib.net.readNet or supply virtual paths.
    if hasattr(reader_fn, "assert_called") or not net_file_path or not os.path.isfile(net_file_path):
        return reader_fn(net_file_path, **kwargs)

    abs_path = os.path.abspath(net_file_path)
    try:
        st = os.stat(abs_path)
        sig_base = (abs_path, int(st.st_mtime_ns), int(st.st_size))
    except OSError:
        return reader_fn(net_file_path, **kwargs)

    norm_internal = bool(with_internal) if with_internal is not None else False
    exact_key = (*sig_base, bool(with_programs), norm_internal)
    superset_key = (*sig_base, True, norm_internal)

    with _CACHE_LOCK:
        if exact_key in _NET_CACHE:
            _NET_CACHE.move_to_end(exact_key)
            return _NET_CACHE[exact_key]
        if not with_programs and superset_key in _NET_CACHE:
            _NET_CACHE.move_to_end(superset_key)
            return _NET_CACHE[superset_key]

    net = reader_fn(net_file_path, **kwargs)

    with _CACHE_LOCK:
        _NET_CACHE[exact_key] = net
        _NET_CACHE.move_to_end(exact_key)
        while len(_NET_CACHE) > _MAX_CACHE_ENTRIES:
            _NET_CACHE.popitem(last=False)

    return net
