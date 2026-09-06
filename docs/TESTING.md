---
tags: [testing, pytest, coverage, mocks, safety, validation]
aliases: [Testing Guidelines, Unit Testing, Safety Mocks, Quality Assurance]
---

# 🧪 Testing & Validation Guidelines

CARINA governs safety-critical municipal traffic infrastructure. Absolute reliability, deterministic unit testing, driver mocks, and continuous safety veto validation are mandatory before deploying changes.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🛡️ See [Safety & Watchdog](SAFETY_AND_WATCHDOG.md) | 🚦 See [Hardware Drivers](HARDWARE_DRIVERS.md) | 🛠️ See [Developer Guides](DEVELOPER_GUIDES.md)

---

## 1. Running the Test Suite (`pytest`)

All tests are located in [`tests/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/tests).

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

---

## 2. Real Test Directory Structure

```text
tests/
├── conftest.py                     # Shared pytest fixtures, temporary DBs & mock envs
├── mock_junctions.py               # Synthetic topology graph & node definitions
├── benchmark.py                    # Performance benchmarks (throughput & latency)
│
├── unit/                           # Isolated Unit Tests
│   ├── test_local_agent.py         # PPO Tactical Agent action selection & update loop
│   ├── test_guardian_agent.py      # D3QN safety sentinel & risk threshold validation
│   ├── test_core_components.py     # DecisionCoordinator & ActionAuthorizer tests
│   ├── test_driver_factory_brand_model.py # Driver instantiation (NTCIP / UTMC)
│   ├── test_hardware_event_listener.py    # SNMP trap listeners & fault parsing
│   ├── test_connection_db_persistence.py  # Controller endpoints persistence
│   ├── test_captum_analyzer.py     # Integrated Gradients attribution tests
│   ├── test_mfd_report_generator.py # Macroscopic Fundamental Diagram tests
│   ├── test_sas_report_generator.py # Smart Analysis System warrant tests
│   ├── test_security_manager.py    # Authentication, bcrypt & lockdown tests
│   └── test_live_canvas_map_widget.py     # Flet map canvas widget tests
│
└── integration/                    # End-to-End & Hardware Integration Tests
    ├── test_traffic_light_drivers.py # Mock NTCIP/UTMC controller communication
    └── test_system_integration.py    # Full gRPC telemetry-to-actuation cycle
```

---

## 3. Writing Safety Veto Tests (`SafetyAuditor`)

Every new action or phase transition must be validated against [`src/core/safety_auditor.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/core/safety_auditor.py):

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
```

---

## 4. Hardware Driver Mocking

When testing controllers without physical hardware present, utilize mock fixtures provided in [`tests/conftest.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/tests/conftest.py) to simulate UDP SNMP responses:

```python
def test_ntcip_driver_status_query(mock_snmp_client):
    driver = NTCIPDriver(ip_address="127.0.0.1", port=161)
    status = driver.query_phase_status()
    assert "greens" in status
    assert "reds" in status
```
