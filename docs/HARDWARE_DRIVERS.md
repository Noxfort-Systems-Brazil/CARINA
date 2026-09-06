---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers]
aliases: [Hardware Drivers, Physical Controllers, NTCIP 1202, UTMC Integration]
---

# 🚦 Hardware Drivers & Physical Controller Integration

This document specifies CARINA's physical hardware integration layer located in [`src/drivers/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers) and [`src/controller/`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/controller). It details communication protocols (**NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**), connection lifecycle management, hardware telemetry acquisition, and deterministic fail-safe handoff.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🏛️ See [Multiprocessing Architecture](../ARCHITECTURE.md) | 🛡️ See [Safety & Watchdog](SAFETY_AND_WATCHDOG.md)

---

## 1. Architectural Overview

CARINA interfaces with real-world traffic signal controllers (e.g., Econolite, Siemens, Peek, SWARCO, Yunex) using decoupled asynchronous drivers. Hardware communication runs through isolated worker threads to guarantee that network jitter or controller response delays never stall the sub-millisecond AI inference loop.

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
                     ┌────────────┴────────────┐
                     ▼                         ▼
         ┌──────────────────────┐   ┌──────────────────────┐
         │     NTCIPDriver      │   │      UTMCDriver      │
         │ (NTCIP 1202 v02 ASC) │   │  (UTMC2 UK Standard) │
         └──────────┬───────────┘   └──────────┬───────────┘
                    │                          │
                    └─────────────┬────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
         ┌──────────────────────┐    ┌─────────────────────┐
         │   PySNMPClient       │    │ HardwareEventListener│
         │   (UDP Port 161)     │    │ (SNMP Traps / Alerts)│
         └──────────────────────┘    └─────────────────────┘
```

---

## 2. NTCIP 1202 Actuated Signal Controller (ASC) Driver

The **NTCIP 1202 standard** (National Transportation Communications for ITS Protocol) is the predominant standard across North America and modern ITS deployments worldwide.

### 2.1 File Architecture
- [`src/drivers/ntcip_driver.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/ntcip_driver.py): High-level driver orchestrator.
- [`src/drivers/ntcip_telemetry.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/ntcip_telemetry.py): Telemetry poller for active phase, ring status, and detector actuations.
- [`src/drivers/ntcip_action_executor.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/ntcip_action_executor.py): Phase hold, force-off, and call injection engine.
- [`src/drivers/ntcip_stage_mapper.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/ntcip_stage_mapper.py): Translates CARINA discrete actions into NTCIP phase bitmasks.
- [`src/drivers/ntcip_config.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/ntcip_config.py): Controller connection parameters and timeout tolerances.

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
- [`src/drivers/utmc_driver.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/utmc_driver.py): Principal UTMC communication handler.
- [`src/drivers/utmc_telemetry.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/utmc_telemetry.py): Stage confirmation and reply frame parser.
- [`src/drivers/utmc_action_executor.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/utmc_action_executor.py): Stage demand and stage move execution.
- [`src/drivers/utmc_stage_mapper.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/utmc_stage_mapper.py): Maps UTMC stages (Stage 1..8) to CARINA neural actions.
- [`src/drivers/utmc2_parser.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/drivers/utmc2_parser.py): XML/JSON schema parser for UTMC2 objects.

---

## 4. Hardware Management & Fail-Safe Architecture

### 4.1 Connection Lifecycle & Pooling (`src/controller/`)
- [`src/controller/connection_manager.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/controller/connection_manager.py): Manages connection state machines (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`).
- [`src/controller/connection_config_repo.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/controller/connection_config_repo.py): Persists IP addresses, ports, protocols, and credentials in the `hardware_controller_connections` table.
- [`src/controller/failsafe_manager.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/controller/failsafe_manager.py): Executes emergency reversion.

### 4.2 Fail-Safe Determinism
1. **Heartbeat Loss (< 500 ms):** If communication with an active controller drops for more than 3 consecutive polling intervals, CARINA releases all Phase Holds and Force-Off commands.
2. **Local Controller Reversion:** The physical controller immediately reverts to its local internal coordinated fixed-time plan (Time-of-Day / Flash Mode), guaranteeing uninterrupted intersection safety.
3. **Safety Conflict Intercept:** All outgoing actions pass through [`src/controller/stage_validator.py`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/src/controller/stage_validator.py) before dispatch, verifying intergreen clearance and conflict matrices.

---

## 5. Security & Network Credentials

Hardware credentials must never be hardcoded. CARINA resolves SNMP and controller secrets through environment variables defined in [`.env`](file:///home/gabriel-moraes/Documentos/CARINA_CORE/.env.example):

```bash
CARINA_SNMP_COMMUNITY=public
CARINA_ENV=production
```

For security configurations and user roles, see [Security & Authentication](SECURITY_AND_AUTH.md).
For telemetry serialization schemas, see [API Reference](API_REFERENCE.md).
