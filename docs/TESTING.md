---
tags: [testing, pytest, coverage, mocks, safety, validation]
aliases: [Testing Guidelines, Unit Testing, Safety Mocks, Quality Assurance]
---

# 🧪 Testing & Validation Guidelines

CARINA governs safety-critical municipal traffic infrastructure. Absolute reliability, deterministic unit testing, driver mocks, and continuous safety veto validation are mandatory before deploying changes.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🛡️ See [Safety & Watchdog](SAFETY_AND_WATCHDOG.md) | 🚦 See [Hardware Drivers](HARDWARE_DRIVERS.md) | 🛠️ See [Developer Guides](DEVELOPER_GUIDES.md) | 🚑 See [EVP Preemption](EVP_AND_PREEMPTION.md)

---

## 1. Running the Test Suite (`pytest`)

CARINA features an exhaustive test suite with **967 automated Python tests** (verified via `pytest --collect-only`: **935 unit tests** across 192 files, **18 integration tests** across 8 files, and **14 tests** across 4 root test files) plus **46 Go unit tests** across 15 `*_test.go` files, ensuring safety, zero regressions, and deterministic microsecond failover across every subsystem. All tests are located in [`tests/`](../tests) and [`src_go/`](../src_go).

### 1.1 Execute Tests with Memory Guard (`scripts/pytest_limited.sh`)
To prevent multi-process PyTorch/SLM fixtures from exhausting host RAM during full runs, prefer the kernel-capped runner [`scripts/pytest_limited.sh`](../scripts/pytest_limited.sh) paired with [`tests/memory_guard.py`](../tests/memory_guard.py):
```bash
# Enforces systemd cgroup v2 limits (MemoryHigh=1536M, MemoryMax=2048M, MemorySwapMax=512M)
# or falls back to ulimit -d + CARINA_PYTEST_MAX_RAM_MB process-tree RSS guard:
./scripts/pytest_limited.sh tests/ -v
```
- **Deterministic Resource Reclamation:** `tests/memory_guard.py` samples process-tree RSS, performs soft `gc.collect()` / `malloc_trim()`, and cleans up singletons (`GoGatewayClient`, `HardwareConnectionManager`, `DatabaseManager`, Matplotlib figures) via `reclaim_test_resources()`.
- **Offline SLM Test Guard:** Real GGUF LLM loading is disabled during `pytest` by default unless `CARINA_ALLOW_REAL_SLM=1` is explicitly exported.

### 1.2 Execute All Tests Directly & Coverage Reports
```bash
pytest tests/ -v
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
The HTML coverage report is generated at `htmlcov/index.html`.

### 1.3 Execute Go Hardware Gateway Unit Tests (`go test`)
To run native Go unit tests (46 test functions covering NTCIP, UTMC, SNMPv3/codec, binary traps, discovery, failsafe, EVP, and Web Gateway auth/TLS):
```bash
cd src_go && go test -v -race ./...
```

---

## 2. Real Test Directory Structure

```text
tests/
├── conftest.py                     # Shared pytest fixtures, temporary DBs & mock envs
├── memory_guard.py                 # Process-tree RSS monitor, soft GC trims & singleton reclamation
├── mock_junctions.py               # Synthetic topology graph & node definitions
├── benchmark.py                    # Performance benchmarks (throughput & latency)
├── test_*.py                       # 4 root suites (14 tests: sanity, invariants, pacing, weekly coverage)
│
├── unit/                           # Isolated Unit Tests (192 files / 935 collected tests)
│   ├── test_closed_loop_hardware_control.py # NTCIP/UTMC bitmask decoding & closed-loop stage sync
│   ├── test_field_readiness_configs.py # Per-intersection config_path, token forwarding & phase timing
│   ├── test_grpc_security.py       # Synapse gRPC TLS/mTLS & BearerTokenServerInterceptor tests
│   ├── test_sds_cco_broadcast_security.py # CCOBroadcastClient TLS + SHA-256 leaf cert pinning
│   ├── test_guardian_calibration_and_training.py # QR-D3QN CHILD training, F2 calibration, Noisy-OR & freeze
│   ├── test_db_connection_and_locking.py # PostgresConnectionPool, SQLite WAL pragmas & db_transaction
│   ├── test_nvidia_memory_and_hotpath_optimizations.py # BatchedPAE, torch.vmap, NumPy GAE, host ReplayMemory
│   ├── test_phase2_db_ipc_optimizations.py # make_interval SQL, ThreadSafePipeConnection & EVP retention
│   ├── test_phase3_slm_xai_render_optimizations.py # slm_process_lock, pynvml VRAM, mpl_utils, XAI cache
│   ├── test_phase4_gateway_evp_ui_optimizations.py # MapAnimator window pause, AuditLog pagination, CCO perf
│   ├── test_pytest_memory_guard.py # Process-tree RSS sampling, soft trims & resource reclamation
│   ├── test_solid_full_audit_refactoring.py # Segregated interfaces & SOLID coordinator decompositions
│   ├── test_solid_gateway_and_step_refactoring.py # Gateway coordinator & step pipeline DIP tests
│   ├── test_evp_*.py               # 12 EVP modules (service, kinematics, preemption, fleet, UI markers)
│   ├── test_local_agent.py         # PPO Tactical Agent action selection & update loop
│   ├── test_guardian_agent.py      # D3QN safety sentinel & risk threshold validation
│   ├── test_strategist_agent.py    # ST-GATv2 Lite Graph Attention arterial coordinator
│   ├── test_pae_model.py           # Action-Conditioned iTransformer PAE & uncertainty tests
│   ├── test_remote_gateway_and_cco.py # Tailscale Web Gateway & CCO stream tests
│   ├── test_settings_modular.py    # Modular SettingsService, Schema, Providers & INI
│   ├── test_monitor_client.py      # Polymorphic MonitorClient, HTTP & MQTT transports
│   ├── test_go_gateway_bridge.py   # Go Hardware Gateway subprocess & pipe IPC bridge
│   ├── test_fenix_*.py             # FENIX supervisor, runner, recovery policy & state reconciler
│   ├── security/                   # Crypto, PBKDF2, password policy & SOLID security suites
│   └── ...                         # Full coverage across core, mfd, sas, xai, rendering & ui
│
└── integration/                    # End-to-End System Integration Tests (8 Modules / 18 Tests)
    ├── test_system_integration.py    # Full gRPC telemetry-to-actuation cycle
    ├── test_gateway_ipc_pipeline.py  # Go Gateway anonymous pipe NDJSON IPC pipeline
    ├── test_gateway_ownership_and_fenix_roundtrip.py # CARINA_GATEWAY_ROLE owner/remote & FENIX roundtrip
    ├── test_go_gateway_snmp_hil_loopback.py # Real compiled Go binary <-> SNMP mock agent HIL loopback
    ├── test_hft_performance_sla.py   # Sub-millisecond HFT loop latency & SLA validation
    ├── test_postgres_migrations.py   # PostgreSQL Alembic schema migrations & rollback
    ├── test_traffic_light_drivers.py # High-level NTCIP/UTMC driver integration checks
    └── test_watchdog_resilience.py   # Watchdog heartbeat timeout failover & resurrection
```

---

## 3. Writing Safety Veto Tests (`SafetyAuditor`)

Every new action or phase transition must be validated against [`src/core/safety_auditor.py`](../src/core/safety_auditor.py):

```python
import pytest
from core.safety_auditor import SafetyAuditor

def test_symbolic_min_green_veto():
    """Verify that the auditor vetoes premature phase switches before minimum green expires."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    # Simulate current state: Phase 1 has been active for only 3.0 seconds
    current_state = {"active_phase": 1, "phase_duration_seconds": 3.0}
    proposed_action = 2  # Attempting to switch to Phase 2 prematurely

    # Audit action
    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Forced to maintain active phase
    assert "Minimum Green" in reason


def test_evp_preemption_overrides_rl_action():
    """Verify Rule SR-00: active preemption forces corridor green while respecting yellow clearance."""
    auditor = SafetyAuditor(min_green_time_seconds=7.0)

    current_state = {
        "active_phase": 2,
        "phase_duration_seconds": 15.0,
        "evp_active": True,
        "evp_target_stage": 1,
        "yellow_clearance_completed": True
    }
    proposed_action = 3  # RL agent wanted Phase 3

    authorized_action, is_vetoed, reason = auditor.audit(current_state, proposed_action)

    assert is_vetoed is True
    assert authorized_action == 1  # Forced to EVP target Stage 1
    assert "SR-00" in reason or "Preemption" in reason
```

---

## 4. Hardware Driver Mocking

When testing controllers without physical hardware present, utilize mock fixtures provided in [`tests/conftest.py`](../tests/conftest.py) to simulate UDP SNMP responses:

```python
def test_ntcip_driver_status_query(mock_snmp_client):
    driver = NTCIPDriver(ip_address="127.0.0.1", port=161)
    status = driver.query_phase_status()
    assert "greens" in status
    assert "reds" in status
```

---

<div align="center">
  <img src="assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
