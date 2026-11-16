# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Memory limiting, process-tree RSS watchdog, and test resource reclamation utilities.

Enforces hard RAM limits (`RLIMIT_DATA` + descendant process-tree RSS monitoring),
caps glibc/BLAS/OMP arenas and threads, disables unintended CUDA context initialization
in test runs, and reaps leaked child processes/singletons between tests.
"""

from __future__ import annotations

import ctypes
import gc
import logging
import os
import resource
import signal
import sys
import threading
import time
from typing import Callable, Dict, Iterable, Optional, Tuple

DEFAULT_MAX_RAM_MB = 2048
SOFT_TRIM_RATIO = 0.80
HARD_SPIKE_RATIO = 1.05
M_ARENA_MAX = -8

# Capture stdlib primitives at import time so unit tests patching `builtins.open`,
# `os.listdir`, or `time.sleep` cannot disrupt the background watchdog thread.
_REAL_OPEN = open
_REAL_LISTDIR = os.listdir
_REAL_KILL = os.kill
_REAL_EXIT = os._exit
_REAL_MONOTONIC = time.monotonic
_REAL_STDERR = sys.stderr

_LIBC_CACHE: Optional[ctypes.CDLL] = None
_LIBC_LOADED = False


def _get_libc() -> Optional[ctypes.CDLL]:
    """Loads libc once for mallopt / malloc_trim calls on glibc platforms."""
    global _LIBC_CACHE, _LIBC_LOADED
    if _LIBC_LOADED:
        return _LIBC_CACHE
    _LIBC_LOADED = True
    try:
        _LIBC_CACHE = ctypes.CDLL("libc.so.6")
    except OSError:
        _LIBC_CACHE = None
    return _LIBC_CACHE


def malloc_trim() -> int:
    """Returns freed glibc heap pages back to the OS kernel when supported."""
    libc = _get_libc()
    if libc is not None and hasattr(libc, "malloc_trim"):
        try:
            return int(libc.malloc_trim(0))
        except Exception:
            return 0
    return 0


def configure_low_memory_env() -> None:
    """
    Applies low-memory allocator, thread, backend, and device defaults
    before heavy native libraries (PyTorch, NumPy, SciPy, Matplotlib) load.
    """
    env_defaults = {
        "MALLOC_ARENA_MAX": "2",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "TORCH_NUM_THREADS": "1",
        "RAYON_NUM_THREADS": "1",
        "MPLBACKEND": "Agg",
        "PYTORCH_NO_CUDA_MEMORY_CACHING": "1",
    }
    for key, val in env_defaults.items():
        os.environ.setdefault(key, val)

    if os.environ.get("CARINA_PYTEST_ALLOW_CUDA") != "1":
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

    libc = _get_libc()
    if libc is not None and hasattr(libc, "mallopt"):
        try:
            libc.mallopt(M_ARENA_MAX, 2)
        except Exception:
            pass


def parse_max_ram_mb(cli_value: Optional[int] = None) -> int:
    """Resolves configured max RAM limit in MiB (0 disables hard limit)."""
    if cli_value is not None:
        return max(0, int(cli_value))

    raw = os.environ.get("CARINA_PYTEST_MAX_RAM_MB")
    if raw is None or not str(raw).strip():
        return DEFAULT_MAX_RAM_MB

    try:
        return max(0, int(str(raw).strip()))
    except ValueError:
        logging.warning("[CARINA RAM Guard] Invalid CARINA_PYTEST_MAX_RAM_MB=%r; using %d MB.", raw, DEFAULT_MAX_RAM_MB)
        return DEFAULT_MAX_RAM_MB


def apply_rlimit_data(max_ram_mb: int) -> Optional[int]:
    """
    Enforces per-process RLIMIT_DATA (heap + private anonymous mmap) inherited by child processes.
    Respects tighter limits already imposed by the parent shell or container.
    """
    if max_ram_mb <= 0 or not hasattr(resource, "RLIMIT_DATA"):
        return None

    limit_bytes = int(max_ram_mb) * 1024 * 1024
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_DATA)
        target_hard = limit_bytes if hard == resource.RLIM_INFINITY else min(hard, limit_bytes)
        target_soft = target_hard if soft == resource.RLIM_INFINITY else min(soft, target_hard)
        resource.setrlimit(resource.RLIMIT_DATA, (target_soft, target_hard))
        return int(target_soft // (1024 * 1024))
    except (ValueError, OSError) as exc:
        logging.warning("[CARINA RAM Guard] Could not apply RLIMIT_DATA=%d MB: %s", max_ram_mb, exc)
        return None


def collect_process_tree_rss_mb(
    root_pid: int,
    proc_dir: str = "/proc",
) -> Tuple[float, Dict[int, Tuple[float, str]]]:
    """
    Sums VmRSS (MiB) across `root_pid` and all reachable descendant processes from `/proc`.
    Returns `(total_rss_mb, {pid: (rss_mb, comm_name)})`.
    """
    proc_info: Dict[int, Tuple[int, float, str]] = {}
    try:
        entries = _REAL_LISTDIR(proc_dir)
    except OSError:
        return 0.0, {}

    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        status_path = os.path.join(proc_dir, entry, "status")
        try:
            with _REAL_OPEN(status_path, "r", encoding="utf-8", errors="ignore") as f:
                ppid = 0
                rss_kb = 0
                name = ""
                for line in f:
                    if line.startswith("Name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("PPid:"):
                        ppid = int(line.split()[1])
                    elif line.startswith("VmRSS:"):
                        rss_kb = int(line.split()[1])
                proc_info[pid] = (ppid, rss_kb / 1024.0, name)
        except (OSError, ValueError, IndexError):
            continue

    tree_pids = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, (ppid, _rss, _name) in proc_info.items():
            if ppid in tree_pids and pid not in tree_pids:
                tree_pids.add(pid)
                changed = True

    per_pid: Dict[int, Tuple[float, str]] = {}
    total_rss = 0.0
    for pid in tree_pids:
        if pid in proc_info:
            _ppid, rss_mb, name = proc_info[pid]
            per_pid[pid] = (rss_mb, name)
            total_rss += rss_mb

    return total_rss, per_pid


def terminate_descendant_processes(root_pid: int, pids: Iterable[int]) -> None:
    """Force-terminates descendant processes in the test tree before aborting pytest."""
    for pid in pids:
        if pid == root_pid:
            continue
        try:
            _REAL_KILL(pid, signal.SIGKILL)
        except OSError:
            pass


class ProcessTreeRamGuard:
    """
    Background daemon watchdog enforcing an aggregate RSS ceiling across the pytest
    process and all spawned child processes.
    """

    def __init__(
        self,
        max_ram_mb: int,
        root_pid: Optional[int] = None,
        poll_interval: float = 0.25,
        soft_trim_ratio: float = SOFT_TRIM_RATIO,
        abort_fn: Optional[Callable[[str, float, Dict[int, Tuple[float, str]]], None]] = None,
        rss_reader: Optional[Callable[[int], Tuple[float, Dict[int, Tuple[float, str]]]]] = None,
    ) -> None:
        self.max_ram_mb = max(0, int(max_ram_mb))
        self.root_pid = root_pid if root_pid is not None else os.getpid()
        self.poll_interval = max(0.05, float(poll_interval))
        self.soft_trim_ratio = soft_trim_ratio
        self._abort_fn = abort_fn
        self._rss_reader = rss_reader or collect_process_tree_rss_mb

        self.rlimit_data_mb: Optional[int] = None
        self.peak_rss_mb: float = 0.0
        self.current_nodeid: str = "<session>"
        self.soft_trim_count: int = 0
        self.aborted: bool = False

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_trim_ts: float = 0.0
        self._consecutive_breaches: int = 0

    def start(self) -> None:
        """Samples baseline RSS and starts the daemon RSS watchdog thread if enabled."""
        self.check_once()
        if self.max_ram_mb <= 0 or self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="carina-pytest-ram-guard",
        )
        try:
            self._thread.start()
        except RuntimeError:
            self._thread = None

    def stop(self) -> None:
        """Samples final RSS and stops the watchdog thread cleanly."""
        try:
            self.check_once()
        except Exception:
            pass
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self.poll_interval):
            try:
                self.check_once()
            except Exception:
                pass

    def _trigger_abort(self, total_rss_mb: float, per_pid: Dict[int, Tuple[float, str]]) -> None:
        self.aborted = True
        if self._abort_fn is not None:
            self._abort_fn(self.current_nodeid, total_rss_mb, per_pid)
            return

        terminate_descendant_processes(self.root_pid, per_pid.keys())
        proc_details = ", ".join(
            f"pid={pid}({name}): {rss:.1f}MB"
            for pid, (rss, name) in sorted(per_pid.items(), key=lambda item: item[1][0], reverse=True)
        )
        msg = (
            f"\n[CARINA RAM Guard] ABORTING pytest: process-tree RSS {total_rss_mb:.1f} MB "
            f"exceeded limit {self.max_ram_mb} MB during {self.current_nodeid} [{proc_details}]\n"
        )
        try:
            os.write(2, msg.encode("utf-8", errors="replace"))
        except Exception:
            try:
                _REAL_STDERR.write(msg)
                _REAL_STDERR.flush()
            except Exception:
                pass
        _REAL_EXIT(137)

    def check_once(self) -> float:
        """Samples process-tree RSS once and enforces soft trim and hard ceiling."""
        total_rss, per_pid = self._rss_reader(self.root_pid)
        if total_rss > self.peak_rss_mb:
            self.peak_rss_mb = total_rss

        if self.max_ram_mb <= 0:
            return total_rss

        now = _REAL_MONOTONIC()
        if total_rss >= self.max_ram_mb * self.soft_trim_ratio and (now - self._last_trim_ts) >= 2.0:
            self._last_trim_ts = now
            self.soft_trim_count += 1
            gc.collect()
            malloc_trim()

        if total_rss > self.max_ram_mb:
            gc.collect()
            malloc_trim()
            total_rss, per_pid = self._rss_reader(self.root_pid)
            if total_rss > self.peak_rss_mb:
                self.peak_rss_mb = total_rss

            if total_rss > self.max_ram_mb:
                self._consecutive_breaches += 1
                if self._consecutive_breaches >= 2 or total_rss > self.max_ram_mb * HARD_SPIKE_RATIO:
                    self._trigger_abort(total_rss, per_pid)
            else:
                self._consecutive_breaches = 0
        else:
            self._consecutive_breaches = 0

        return total_rss

    def format_summary(self) -> str:
        """Formats end-of-session memory usage summary line."""
        limit_str = f"{self.max_ram_mb} MB" if self.max_ram_mb > 0 else "unlimited"
        rlimit_str = f"{self.rlimit_data_mb} MB" if self.rlimit_data_mb is not None else "unset"
        return (
            f"[CARINA RAM Guard] Peak tree RSS: {self.peak_rss_mb:.1f} MB | "
            f"Limit: {limit_str} | RLIMIT_DATA: {rlimit_str} | Soft trims: {self.soft_trim_count}"
        )


def _is_mock_object(obj: object) -> bool:
    """Detects unittest.mock objects without importing unittest.mock unnecessarily."""
    return hasattr(obj, "assert_called") or type(obj).__module__.startswith("unittest.mock")


def reclaim_test_resources(force_gc: bool = False) -> None:
    """
    Cleans up leaked singletons, child binaries (e.g. carina-go), listener threads,
    and open matplotlib figures after test execution.
    """
    for mod_name in ("src.drivers.go_gateway_client", "drivers.go_gateway_client"):
        mod = sys.modules.get(mod_name)
        cls = getattr(mod, "GoGatewayClient", None) if mod is not None else None
        inst = getattr(cls, "_instance", None) if cls is not None else None
        if inst is not None and not _is_mock_object(inst):
            try:
                if hasattr(inst, "is_running") and inst.is_running():
                    inst.stop()
            except Exception:
                pass
            try:
                cls._instance = None
            except Exception:
                pass

    for mod_name in ("src.controller.connection_manager", "controller.connection_manager"):
        mod = sys.modules.get(mod_name)
        cls = getattr(mod, "HardwareConnectionManager", None) if mod is not None else None
        inst = getattr(cls, "_active_instance", None) if cls is not None else None
        if inst is not None and not _is_mock_object(inst):
            listener = getattr(inst, "event_listener", None)
            if listener is not None and not _is_mock_object(listener):
                try:
                    listener.stop()
                except Exception:
                    pass
            try:
                cls._active_instance = None
            except Exception:
                pass

    for mod_name in ("src.database.database_manager", "database.database_manager"):
        mod = sys.modules.get(mod_name)
        cls = getattr(mod, "DatabaseManager", None) if mod is not None else None
        inst = getattr(cls, "_instance", None) if cls is not None else None
        if inst is not None and not _is_mock_object(inst):
            try:
                if hasattr(inst, "close"):
                    inst.close()
            except Exception:
                pass
            try:
                cls._instance = None
            except Exception:
                pass

    plt = sys.modules.get("matplotlib.pyplot")
    if plt is not None and hasattr(plt, "close") and not _is_mock_object(plt):
        try:
            plt.close("all")
        except Exception:
            pass

    if force_gc:
        gc.collect()
        malloc_trim()
