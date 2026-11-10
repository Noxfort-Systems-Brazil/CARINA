---
tags: [testing, pytest, coverage, mocks, safety, validation]
aliases: [Testing Guidelines, Unit Testing, Safety Mocks, Quality Assurance]
---

# 🧪 Testing & Validation Guidelines

CARINA governs safety-critical municipal traffic infrastructure. Absolute reliability, deterministic unit testing, driver mocks, and continuous safety veto validation are mandatory before deploying changes.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🛡️ See [Safety & Watchdog](SAFETY_AND_WATCHDOG.md) | 🚦 See [Hardware Drivers](HARDWARE_DRIVERS.md) | 🛠️ See [Developer Guides](DEVELOPER_GUIDES.md) | 🚑 See [EVP Preemption](EVP_AND_PREEMPTION.md)

---

## 1. Running the Test Suite (`pytest`)

CARINA features an exhaustive test suite with **861 automated tests** (verified via `pytest --collect-only`) ensuring safety, zero regressions, and deterministic microsecond failover across every subsystem. All tests are located in [`tests/`](../tests).

### 1.1 Execute All Tests
```bash
pytest tests/ -v
```

### 1.2 Generate Coverage Reports
To measure branch and statement coverage across `src/`:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
The HTML coverage report is generated at `htmlcov/index.html`.

### 1.3 Execute Go Hardware Gateway Unit Tests (`go test`)
To run native Go unit tests covering NTCIP, UTMC, traps, and discovery:
```bash
cd src_go && go test -v ./...
```

---

## 2. Real Test Directory Structure

```text
tests/
├── conftest.py                     # Shared pytest fixtures, temporary DBs & mock envs
├── mock_junctions.py               # Synthetic topology graph & node definitions
├── benchmark.py                    # Performance benchmarks (throughput & latency)
│
├── unit/                           # Isolated Unit Tests (861 Total Collected Tests)
│   ├── test_evp_service.py         # EVPService lifecycle, ingestion pipeline & preemption triggers
│   ├── test_evp_kinematics.py      # Haversine distance, speed, heading & approach gates
│   ├── test_evp_preemption_engine.py # Preemption hold arbitration, 45s dwell watchdog & clearance
│   ├── test_evp_map_topology.py    # Topology matching, incoming approaches & stage mapping
│   ├── test_evp_fleet_persistence.py # Authorized fleet CRUD operations & plate caching
│   ├── test_evp_config_repo.py     # EVP configuration repository & threshold persistence
│   ├── test_evp_fleet_controller.py # Fleet management business logic & validation
│   ├── test_evp_fleet_csv.py       # Fleet CSV export and bulk import parsing
│   ├── test_evp_fleet_save_flow.py # End-to-end fleet UI form save & database commit
│   ├── test_evp_hardware_parity_persistence.py # Hardware state parity across DB engines
│   ├── test_evp_settings_handler.py # EVP settings persistence in settings.ini & .env
│   ├── test_evp_vehicle_marker.py  # Flet canvas EVP vehicle marker glyphs & strobe animations
│   ├── test_local_agent.py         # PPO Tactical Agent action selection & update loop
│   ├── test_guardian_agent.py      # D3QN safety sentinel & risk threshold validation
│   ├── test_strategist_agent.py    # ST-GATv2 Lite Graph Attention arterial coordinator
│   ├── test_settings_modular.py    # Modular SettingsService, Schema, Providers & INI
│   ├── test_settings_view.py       # Flet Settings View & UI persistence
│   ├── test_monitor_client.py      # Polymorphic MonitorClient, HTTP & MQTT transports
│   ├── test_monitor_disconnect.py  # Telemetry retry, buffer flush & disconnect flows
│   ├── test_core_components.py     # DecisionCoordinator & ActionAuthorizer tests
│   ├── test_go_gateway_bridge.py   # Go Hardware Gateway subprocess & pipe IPC bridge
│   ├── test_traffic_light_driver.py # High-level traffic light driver abstraction
│   ├── test_traffic_modular_components.py # Traffic light modular components
│   ├── test_driver_factory_brand_model.py # Driver instantiation (NTCIP / UTMC / Go)
│   ├── test_hardware_event_listener.py    # SNMP trap listeners & fault parsing
│   ├── test_connection_db_persistence.py  # Controller endpoints persistence
│   ├── test_connection_manager_orchestrator.py # Connection state machine orchestration
│   ├── test_fenix_supervisor.py    # FENIX supervisor lifecycle, recovery & resurrection
│   ├── test_fenix_process_runner.py # Subprocess runner process control (SIGTERM/SIGKILL)
│   ├── test_fenix_recovery_policy.py # Windowed crash recovery policy & exponential backoff
│   ├── test_fenix_state_reconciler.py # Clean boundary handover & FROZEN_SYNC synchronization
│   ├── test_watchdog_fenix_integration.py # Watchdog timeout trigger to FENIX resurrection
│   ├── test_security_modular.py    # AuthService, UserService, PBKDF2 & Lockdown
│   ├── test_security_manager.py    # Legacy SecurityManager facade validation
│   ├── test_captum_analyzer.py     # Integrated Gradients attribution tests
│   ├── test_xai_report_builder.py  # ABNT Word report generation with OMML equations
│   ├── test_multi_agent_modular_builder.py # Multi-agent report block assembling
│   ├── test_mfd_processor.py       # Macroscopic Fundamental Diagram core processor
│   ├── test_mfd_report_generator.py # MFD report generation and curve fitting
│   ├── test_mfd_db_reconstruction.py # MFD reconstruction from PostgreSQL tables
│   ├── test_mfd_new_report.py      # MFD new report generation pipeline
│   ├── test_sas_report_generator.py # Smart Analysis System warrant tests
│   ├── test_sas_data_transducer.py # SAS telemetry transducer
│   ├── test_sas_helpers.py         # SAS mathematical calculation helpers
│   ├── test_sas_mfd_db_cache.py    # SAS MFD database caching
│   ├── test_semantic_transducer_device.py # Offline SLM transducer & VRAM allocation
│   ├── test_planning_view.py       # Flet Planning View UI tests
│   ├── test_planning_architecture.py # Planning canvas presenter & export handlers
│   ├── test_planning_export_handler.py # Signal timing plan CSV export handlers
│   ├── test_planning_panel_presenter.py # Planning panel UI presenter
│   ├── test_live_canvas_map_widget.py # Flet custom canvas drawing roads and signals
│   ├── test_map_interaction_precision.py # Zoom math, coordinate drift & street hit caching
│   ├── test_map_event_router_precision.py # Semaphore vs street click disambiguation
│   ├── test_interactive_map_precision.py # InteractiveMap tap precision and layer hit
│   ├── test_planning_map_sync.py   # PlanningMapRenderer hit radius & canvas sync
│   ├── test_live_data_provider_ipc.py # LiveDataProvider in-memory IPC queue streaming
│   ├── test_watchdog.py            # Watchdog heartbeat logic and process timers
│   ├── test_consolidation_purge.py # Fluid dynamics delta storage consolidation
│   ├── test_csv_template_export_import.py # Controller endpoint CSV import/export
│   ├── test_db_schema_isolation.py # Schema isolation for tests
│   ├── test_infrastructure_client.py # Client for infrastructure warrants
│   ├── test_intersection_state_manager.py # Multi-intersection stage tracking
│   ├── test_main_components.py     # Central controller main components
│   ├── test_manual_override_hft.py # High-frequency manual phase overrides
│   ├── test_pushdown_query.py      # Pushdown SQL query evaluation
│   ├── test_tls_state_provider.py  # Traffic light state provider
│   ├── test_ui_main_orchestrator.py # Main UI orchestration tests
│   ├── test_window_manager.py      # Desktop window lifecycle management
│   ├── test_population_manager_pbt.py # Intra-Phase PBT cohort isolation & tensor mismatch safety
│   ├── test_performance_margin_calculator.py # Fluid dynamics graduation margin & childhood telemetry
│   ├── test_reward_weights_calculator.py # Physical reward balancing (HCM link traversal time)
│   ├── test_maturity_pacing_calculator.py # Auto-pacing of episode durations from network topology
│   ├── test_yellow_schedule_manager.py # Overnight flashing yellow schedule evaluator
│   └── test_yellow_schedule_card.py # Yellow schedule UI card & time window controls
│
└── integration/                    # End-to-End System Integration Tests (5 Modules)
    ├── test_system_integration.py    # Full gRPC telemetry-to-actuation cycle
    ├── test_gateway_ipc_pipeline.py  # Go Gateway anonymous pipe NDJSON IPC pipeline
    ├── test_hft_performance_sla.py   # Sub-millisecond HFT loop latency & SLA validation
    ├── test_postgres_migrations.py   # PostgreSQL Alembic schema migrations & rollback
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
