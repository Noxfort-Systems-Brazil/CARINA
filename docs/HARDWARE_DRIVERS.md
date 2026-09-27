---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers]
aliases: [Hardware Drivers, Physical Controllers, NTCIP 1202, UTMC Integration]
---

# 🚦 Hardware Drivers & Physical Controller Integration

This document specifies CARINA's physical hardware integration layer located in [`src/drivers/`](../src/drivers) and [`src/controller/`](../src/controller). It details communication protocols (**NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**), connection lifecycle management, hardware telemetry acquisition, and deterministic fail-safe handoff.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🏛️ See [Multiprocessing Architecture](../ARCHITECTURE.md) | 🛡️ See [Safety & Watchdog](SAFETY_AND_WATCHDOG.md)

---

## 1. Architectural Overview

CARINA interfaces with real-world traffic signal controllers (e.g., Econolite, Siemens, Peek, SWARCO, Yunex) using a high-performance **Go Hardware Gateway** (`bin/carina-go` built from [`src_go/`](../src_go)). Communication between the CARINA Python core and the Go Gateway runs strictly through **operating system standard pipes (`stdin`/`stdout`)** using Line-Delimited JSON (NDJSON). This ensures **zero network ports opened on the host machine**, sub-millisecond execution, and total freedom from Python GIL overhead.

```text
       ┌────────────────────────────────────────────────────────┐
       │                   CentralController                    │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
       ┌──────────────────────┐        ┌──────────────────────┐
       │  ConnectionManager   │        │ FailsafeManager      │
       │  (State & Pooling)   │        │ (Heartbeat Watchdog) │
       └──────────┬───────────┘        └──────────┬───────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │     GoGatewayClient     │ (src/drivers/go_gateway_client.py)
                     │ (Python Pipe Subprocess)│
                     └────────────┬────────────┘
                                  │ stdin / stdout (NDJSON IPC - Zero Host Ports)
                                  ▼
      ┌───────────────────────────────────────────────────────┐
      │          CARINA HARDWARE GATEWAY (Go Binary)          │
      │                    (bin/carina-go)                    │
      │                                                       │
      │   ┌────────────────────┐     ┌────────────────────┐   │
      │   │    NTCIP Driver    │     │    UTMC Driver     │   │
      │   │ (NTCIP 1202 v02)   │     │ (UTMC2 UK Standard)│   │
      │   └─────────┬──────────┘     └─────────┬──────────┘   │
      │             │                          │              │
      │             └─────────────┬────────────┘              │
      │                           │                           │
      │             ┌─────────────┴─────────────┐             │
      │             ▼                           ▼             │
      │  ┌──────────────────────┐    ┌─────────────────────┐  │
      │  │    GoSNMP Client     │    │  TrapListener UDP   │  │
      │  │    (UDP Port 161)    │    │      (Port 162)     │  │
      │  └──────────────────────┘    └─────────────────────┘  │
      └───────────────────────────────────────────────────────┘
```

---

## 2. NTCIP 1202 Actuated Signal Controller (ASC) Driver

The **NTCIP 1202 standard** (National Transportation Communications for ITS Protocol) is the predominant standard across North America and modern ITS deployments worldwide.

### 2.1 File Architecture
**Go Gateway Implementation (`src_go/`):**
- [`src_go/pkg/ntcip/driver.go`](../src_go/pkg/ntcip/driver.go): Native Go NTCIP driver orchestrator.
- [`src_go/pkg/ntcip/telemetry.go`](../src_go/pkg/ntcip/telemetry.go): Telemetry poller for active phase, ring status, and detector actuations.
- [`src_go/pkg/ntcip/action_executor.go`](../src_go/pkg/ntcip/action_executor.go): Phase hold, force-off, and call injection engine.
- [`src_go/pkg/ntcip/stage_mapper.go`](../src_go/pkg/ntcip/stage_mapper.go): Translates CARINA discrete actions into NTCIP phase bitmasks.
- [`src_go/pkg/ntcip/config.go`](../src_go/pkg/ntcip/config.go) & [`src_go/configs/ntcip_oids.json`](../src_go/configs/ntcip_oids.json): Embedded OID profile definitions.

**Python Bridge & Proxy Layer (`src/drivers/`):**
- [`src/drivers/go_gateway_client.py`](../src/drivers/go_gateway_client.py): NDJSON anonymous pipe IPC client managing the `bin/carina-go` subprocess.
- [`src/drivers/go_driver_proxy.py`](../src/drivers/go_driver_proxy.py): Drop-in `BaseTrafficDriver` proxy forwarding commands to the Go daemon.
- [`src/drivers/driver_factory.py`](../src/drivers/driver_factory.py): Instantiates driver proxies based on brand/model autodetection.

### 2.2 Standard OID Mapping Table

| Object Name | ASN.1 OID | Type | Description |
| :--- | :--- | :---: | :--- |
| `ascPhaseStatusGroupReds` | `1.3.6.1.4.1.1206.4.2.1.1.1` | `OCTET STRING` | Bitmask of phases currently in Red display. |
| `ascPhaseStatusGroupYellows` | `1.3.6.1.4.1.1206.4.2.1.1.2` | `OCTET STRING` | Bitmask of phases currently in Yellow display. |
| `ascPhaseStatusGroupGreens` | `1.3.6.1.4.1.1206.4.2.1.1.3` | `OCTET STRING` | Bitmask of phases currently in Green display. |
| `ascPhaseHold` | `1.3.6.1.4.1.1206.4.2.1.1.5` | `OCTET STRING` | Holds active phase green (prevents phase change). |
| `ascPhaseForceOff` | `1.3.6.1.4.1.1206.4.2.1.1.6` | `OCTET STRING` | Forces termination of current green phase. |
| `ascPhaseCall` | `1.3.6.1.4.1.1206.4.2.1.1.7` | `OCTET STRING` | Injects synthetic vehicle detection call to request phase. |

---

## 3. UTMC / UTMC2 Driver (UK Standard)

For intersections utilizing the UK **Urban Traffic Management and Control (UTMC)** framework:

### 3.1 File Architecture
**Go Gateway Implementation (`src_go/`):**
- [`src_go/pkg/utmc/driver.go`](../src_go/pkg/utmc/driver.go): Native Go UTMC communication handler.
- [`src_go/pkg/utmc/telemetry.go`](../src_go/pkg/utmc/telemetry.go): Stage confirmation and reply frame parser.
- [`src_go/pkg/utmc/action_executor.go`](../src_go/pkg/utmc/action_executor.go): Stage demand and stage move execution.
- [`src_go/pkg/utmc/stage_mapper.go`](../src_go/pkg/utmc/stage_mapper.go): Maps UTMC stages (Stage 1..8) to CARINA neural actions.
- [`src_go/pkg/utmc/config.go`](../src_go/pkg/utmc/config.go) & [`src_go/configs/utmc_oids.json`](../src_go/configs/utmc_oids.json): Embedded UTMC OID profile definitions.

---

## 4. Hardware Management & Fail-Safe Architecture

### 4.1 Connection Lifecycle & Pooling (`src/controller/`)
- [`src/controller/connection_manager.py`](../src/controller/connection_manager.py): Manages connection state machines (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`).
- [`src/controller/connection_config_repo.py`](../src/controller/connection_config_repo.py): Persists IP addresses, ports, protocols, and credentials in the `hardware_controller_connections` table.
- [`src/controller/failsafe_manager.py`](../src/controller/failsafe_manager.py): Executes emergency reversion.

### 4.2 Fail-Safe Determinism
1. **Heartbeat Loss (< 500 ms):** If communication with an active controller drops for more than 3 consecutive polling intervals, CARINA releases all Phase Holds and Force-Off commands.
2. **Local Controller Reversion:** The physical controller immediately reverts to its local internal coordinated fixed-time plan (Time-of-Day / Flash Mode), guaranteeing uninterrupted intersection safety.
3. **Safety Conflict Intercept:** All outgoing actions pass through [`src/controller/stage_validator.py`](../src/controller/stage_validator.py) before dispatch, verifying intergreen clearance and conflict matrices.

### 4.3 Hardware Incident Reporting & Deduplication (`src/drivers/`)
- [`src/drivers/incident_reporter.py`](../src/drivers/incident_reporter.py): Intercepts controller hardware status changes (`CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`) and constructs standardized incident JSON messages.
- [`src/drivers/incident_filter.py`](../src/drivers/incident_filter.py): Prevents notification storms by caching active incident hashes with timestamp debouncing in `.carina_incident_filter_cache.json`.
- Dispatches alerts dynamically via `MonitorClient` to the configured telemetry transport (local MQTT broker or remote HTTP/Ngrok endpoint).

---

## 5. Security & Network Credentials

Hardware credentials must never be hardcoded. CARINA resolves SNMP and controller secrets through environment variables defined in [`.env`](../.env.example):

```bash
CARINA_SNMP_COMMUNITY=public
CARINA_ENV=production
```

For security configurations and user roles, see [Security & Authentication](SECURITY_AND_AUTH.md).
For telemetry serialization schemas, see [API Reference](API_REFERENCE.md).
