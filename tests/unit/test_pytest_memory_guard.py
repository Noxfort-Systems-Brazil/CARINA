# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for pytest RAM limiting, process-tree RSS guard, and test path/SLM isolation."""

import os
import resource
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.utils.paths import get_base_output_dir, get_user_config_dir
from tests.memory_guard import (
    DEFAULT_MAX_RAM_MB,
    ProcessTreeRamGuard,
    apply_rlimit_data,
    collect_process_tree_rss_mb,
    parse_max_ram_mb,
    reclaim_test_resources,
)


def test_parse_max_ram_mb_precedence_and_validation(monkeypatch):
    monkeypatch.delenv("CARINA_PYTEST_MAX_RAM_MB", raising=False)
    assert parse_max_ram_mb(None) == DEFAULT_MAX_RAM_MB
    assert parse_max_ram_mb(1024) == 1024
    assert parse_max_ram_mb(0) == 0
    assert parse_max_ram_mb(-50) == 0

    monkeypatch.setenv("CARINA_PYTEST_MAX_RAM_MB", "1536")
    assert parse_max_ram_mb(None) == 1536
    assert parse_max_ram_mb(512) == 512  # CLI overrides env

    monkeypatch.setenv("CARINA_PYTEST_MAX_RAM_MB", "not_an_int")
    assert parse_max_ram_mb(None) == DEFAULT_MAX_RAM_MB


def test_apply_rlimit_data_clamps_to_existing_hard_limit():
    if not hasattr(resource, "RLIMIT_DATA"):
        pytest.skip("RLIMIT_DATA not available on this OS")

    with (
        patch("resource.getrlimit", return_value=(resource.RLIM_INFINITY, 1500 * 1024 * 1024)),
        patch("resource.setrlimit") as mock_set,
    ):
        applied = apply_rlimit_data(2048)

    assert applied == 1500
    mock_set.assert_called_once_with(
        resource.RLIMIT_DATA,
        (1500 * 1024 * 1024, 1500 * 1024 * 1024),
    )
    assert apply_rlimit_data(0) is None


def test_collect_process_tree_rss_mb_sums_descendants(tmp_path):
    proc_root = tmp_path / "proc"
    proc_root.mkdir()

    def _mkproc(pid: int, ppid: int, rss_kb: int, name: str) -> None:
        pdir = proc_root / str(pid)
        pdir.mkdir()
        (pdir / "status").write_text(
            f"Name:\t{name}\nPPid:\t{ppid}\nVmRSS:\t{rss_kb} kB\n",
            encoding="utf-8",
        )

    _mkproc(100, 1, 200 * 1024, "pytest")
    _mkproc(101, 100, 300 * 1024, "python3")
    _mkproc(102, 101, 50 * 1024, "carina-go")
    _mkproc(999, 1, 4096 * 1024, "unrelated")

    total_rss, per_pid = collect_process_tree_rss_mb(100, proc_dir=str(proc_root))
    assert pytest.approx(total_rss, rel=1e-3) == 550.0
    assert set(per_pid.keys()) == {100, 101, 102}
    assert per_pid[102] == (50.0, "carina-go")


def test_process_tree_ram_guard_soft_trim_and_hard_abort():
    readings = [
        (450.0, {1: (450.0, "pytest")}),  # 90% of 500 -> triggers soft trim
        (520.0, {1: (520.0, "pytest")}),  # breach #1 (after immediate gc recheck still 520 > 500)
        (520.0, {1: (520.0, "pytest")}),
        (520.0, {1: (520.0, "pytest")}),  # breach #2 -> abort_fn invoked
        (520.0, {1: (520.0, "pytest")}),
    ]
    idx = {"i": 0}

    def _fake_reader(_pid: int):
        pos = min(idx["i"], len(readings) - 1)
        idx["i"] += 1
        return readings[pos]

    aborted = []

    def _fake_abort(nodeid: str, total_rss: float, per_pid):
        aborted.append((nodeid, total_rss, dict(per_pid)))

    guard = ProcessTreeRamGuard(
        max_ram_mb=500,
        root_pid=1,
        abort_fn=_fake_abort,
        rss_reader=_fake_reader,
    )
    guard.current_nodeid = "tests/unit/test_fake.py::test_leak"

    rss1 = guard.check_once()
    assert rss1 == 450.0
    assert guard.soft_trim_count == 1
    assert aborted == []

    # First breach (>100%, <105%) records breach #1 without aborting yet
    guard.check_once()
    assert aborted == []

    # Second consecutive breach triggers abort
    guard.check_once()
    assert len(aborted) == 1
    assert aborted[0][0] == "tests/unit/test_fake.py::test_leak"
    assert aborted[0][1] == 520.0
    assert guard.peak_rss_mb == 520.0


def test_output_and_config_dirs_isolated_from_user_home(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    cfg_dir = tmp_path / "cfg"
    monkeypatch.setenv("CARINA_OUTPUT_DIR", str(out_dir))
    monkeypatch.setenv("CARINA_CONFIG_DIR", str(cfg_dir))

    assert get_base_output_dir() == str(out_dir)
    assert get_user_config_dir() == str(cfg_dir)
    assert out_dir.is_dir()
    assert cfg_dir.is_dir()


def test_slm_guard_blocks_real_llama_cpp_in_test_mode():
    llama_mod = sys.modules.get("llama_cpp")
    assert llama_mod is not None
    with pytest.raises(RuntimeError, match="CARINA_ALLOW_REAL_SLM"):
        llama_mod.Llama(model_path="Model_Vault/Qwen3.5-2B-UD-Q6_K_XL.gguf")


def test_reclaim_test_resources_stops_live_go_gateway_singleton():
    from src.drivers.go_gateway_client import GoGatewayClient

    fake_client = MagicMock()
    # Strip mock assertion attrs so reclaim_test_resources treats it like a real instance
    fake_real = type(
        "_FakeRealGoClient",
        (),
        {
            "is_running": lambda self: True,
            "stop": MagicMock(),
        },
    )()
    prev = GoGatewayClient._instance
    try:
        GoGatewayClient._instance = fake_real
        reclaim_test_resources(force_gc=False)
        fake_real.stop.assert_called_once()
        assert GoGatewayClient._instance is None
    finally:
        GoGatewayClient._instance = prev
        del fake_client
