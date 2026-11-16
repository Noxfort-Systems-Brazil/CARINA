---
tags: [hardware, drivers, ntcip, utmc, snmp, failsafe, controllers]
aliases: [Hardware Drivers, Physical Controllers, NTCIP 1202, UTMC Integration]
---

# 🚦 Hardware Drivers & Physical Controller Integration

This document specifies CARINA's physical hardware integration layer located in [`src/drivers/`](../../src/drivers) and [`src/controller/`](../../src/controller). It details communication protocols (**NTCIP 1202**, **UTMC / UTMC2**, **SNMP v2c/v3**), connection lifecycle management, hardware telemetry acquisition, and deterministic fail-safe handoff.

⬅️ Back to [Main Documentation Hub](carina_moc.md) | 🏛️ See [Multiprocessing Architecture](architecture.md) | 🛡️ See [Safety & Watchdog](safety_and_watchdog.md) | 🚑 See [EVP Preemption](evp_and_preemption.md)

---

## 1. Architectural Overview

CARINA interfaces with real-world traffic signal controllers (e.g., Econolite, Siemens, Peek, SWARCO, Yunex) using a high-performance **Go Hardware Gateway** (`bin/carina-go` built from [`src_go/`](../../src_go)). Communication between the CARINA Python core and the Go Gateway runs strictly through **operating system standard pipes (`stdin`/`stdout`)** using Line-Delimited JSON (NDJSON). This ensures **zero local IPC ports opened on the host machine**, sub-millisecond execution, and total freedom from Python GIL overhead.

### 1.1 Single Gateway Ownership (`CARINA_GATEWAY_ROLE`) & Closed-Loop Architecture
To prevent duplicate `bin/carina-go` processes, UDP `162` trap-listener port collisions, and split-brain SNMP state:
- **`CentralController` (`CARINA_GATEWAY_ROLE=owner`):** Exclusively spawns `bin/carina-go`, hosts [`HardwareGatewayCoordinator`](../../src/controller/hardware_gateway_coordinator.py) (composed of `GatewayRuntimeWorker`, `HardwareCommandService`, `FenixStageDispatcher`, and `TailscaleGatewayAdapter`), owns `HardwareConnectionManager` local SNMP connections, and broadcasts snapshots to downstream workers.
- **`AI_Process`, `SDS`, and `UI` (`CARINA_GATEWAY_ROLE=remote`):** Operate as remote mirrors without launching local Go binaries or binding UDP `162`. [`RemoteHardwareDriverProxy`](../../src/drivers/remote_hardware_driver.py) (materialized by [`sync_remote_driver_proxies`](../../src/drivers/remote_proxy_synchronizer.py)) forwards actions (`ai_hardware_cmd`) and EVP preemptions (`ai_evp_preempt`) back to `CentralController` over [`ThreadSafePipeConnection`](../../src/communication/pipe_utils.py).
- **Closed-Loop Telemetry Decoding:** [`HardwareTelemetrySynchronizer`](../../src/engine/hardware_telemetry_synchronizer.py) and [`decode_stage_from_telemetry`](../../src/drivers/hardware_telemetry_decoder.py) translate real controller bitmasks (`active_greens`, `active_yellows`, `active_reds`, `current_stage`) back into 0-based SUMO stage indices for AI state extraction and F.E.N.I.X. handover reconciliation.

In addition to standard NTCIP/UTMC control, the Go gateway includes an **EVP Preemption Dispatcher** (`src_go/evp_go/dispatcher.go`) for microsecond phase hold assertions and a **Remote Web Gateway** (`src_go/web_gateway/server.go`) providing token-authenticated Tailscale mesh connectivity, TLS termination, HTTP telemetry ingestion (port `2201`), and Server-Sent Events (SSE) streaming for CCO videowalls.

```text
       ┌────────────────────────────────────────────────────────┐
       │      CentralController (CARINA_GATEWAY_ROLE=owner)     │
       │            [HardwareGatewayCoordinator]                │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
       ┌──────────────────────┐   │   ┌──────────────────────┐
       │  ConnectionManager   │   │   │ FailsafeManager      │
       │  (State & SNMPv2/v3) │   │   │ (Heartbeat Watchdog) │
       └──────────┬───────────┘   │   └──────────┬───────────┘
                  │               │              │
                  │   ┌───────────┴──────────┐   │
                  │   │      EVPService      │   │
                  │   │(Preemption Dispatch) │   │
                  │   └───────────┬──────────┘   │
                  └───────────────┼──────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │     GoGatewayClient     │ (src/drivers/go_gateway_client.py)
                     │ (Python Pipe Subprocess)│
                     └────────────┬────────────┘
                                  │ stdin / stdout (NDJSON IPC - Zero Local Control Ports)
                                  ▼
      ┌───────────────────────────────────────────────────────────┐
      │            CARINA HARDWARE GATEWAY (Go Binary)            │
      │                      (bin/carina-go)                      │
      │                                                           │
      │   ┌────────────────────┐         ┌────────────────────┐   │
      │   │    NTCIP Driver    │         │    UTMC Driver     │   │
      │   │ (NTCIP 1202 v02)   │         │ (UTMC2 UK Standard)│   │
      │   └─────────┬──────────┘         └─────────┬──────────┘   │
      │             │                             │               │
      │             └──────────────┬──────────────┘               │
      │                            │                              │
      │             ┌──────────────┼──────────────┐               │
      │             ▼              ▼              ▼               │
      │  ┌──────────────────┐ ┌──────────┐ ┌──────────────────┐   │
      │  │  EVP Dispatcher  │ │GoSNMP v2/3│ │ Binary Trap Dec. │   │
      │  │ (Direct OID Hold)│ │UDP Pt 161│ │ (SNMPv1/v2c/v3)  │   │
      │  └──────────────────┘ └──────────┘ └──────────────────┘   │
      └────────────────────────────┬──────────────────────────────┘
                                   │ Remote Web Ingestion & Mesh
                                   ▼
      ┌───────────────────────────────────────────────────────────┐
      │        Web Gateway & Tailscale Mesh (Port 2201 / TLS)     │
      │  - Fail-closed by default (HTTP 503 when disabled)        │
      │  - POST /api/v1/evp/telemetry (Token Auth, HTTP 204)      │
      │  - GET /cco/stream (Token Auth, CORS, SSE Videowall)      │
      │  - Tailscale Funnel / Encrypted Peer Mesh Networking      │
      └───────────────────────────────────────────────────────────┘
```

---

## 2. NTCIP 1202 Actuated Signal Controller (ASC) Driver

The **NTCIP 1202 standard** (National Transportation Communications for ITS Protocol) is the predominant standard across North America and modern ITS deployments worldwide.

### 2.1 File Architecture
**Go Gateway Implementation (`src_go/`):**
- [`src_go/pkg/ntcip/driver.go`](../../src_go/pkg/ntcip/driver.go): Native Go NTCIP driver orchestrator.
- [`src_go/pkg/ntcip/telemetry.go`](../../src_go/pkg/ntcip/telemetry.go): Telemetry poller for active phase, ring status, and detector actuations.
- [`src_go/pkg/ntcip/action_executor.go`](../../src_go/pkg/ntcip/action_executor.go): Phase hold, force-off, and call injection engine.
- [`src_go/pkg/ntcip/stage_mapper.go`](../../src_go/pkg/ntcip/stage_mapper.go): Translates CARINA discrete actions into NTCIP phase bitmasks.
- [`src_go/pkg/ntcip/config.go`](../../src_go/pkg/ntcip/config.go) & [`src_go/configs/ntcip_oids.json`](../../src_go/configs/ntcip_oids.json): Embedded OID profile definitions.

**Python Bridge & Proxy Layer (`src/drivers/`):**
- [`src/drivers/go_gateway_client.py`](../../src/drivers/go_gateway_client.py): NDJSON anonymous pipe IPC client managing the `bin/carina-go` subprocess.
- [`src/drivers/go_driver_proxy.py`](../../src/drivers/go_driver_proxy.py): Drop-in `BaseTrafficDriver` proxy forwarding commands to the Go daemon.
- [`src/drivers/driver_factory.py`](../../src/drivers/driver_factory.py): Instantiates driver proxies based on brand/model autodetection.

### 2.2 Standard OID Mapping Table (`src_go/configs/ntcip_oids.json`)

All NTCIP 1202 status (`phaseStatusGroup`) and control (`phaseControlGroup`) OIDs support both integer and `OCTET STRING`/`BitString` PDUs via [`DecodeBitmaskPDU`](../../src_go/pkg/snmp/codec.go), and can be overridden per intersection via `config_path`:

| Object Key | ASN.1 OID | Group / Type | Description |
| :--- | :--- | :---: | :--- |
| `status_reds` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1` | Status / Bitmask | Bitmask of phases currently in Red display. |
| `status_yellows` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1` | Status / Bitmask | Bitmask of phases currently in Yellow display. |
| `status_greens` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1` | Status / Bitmask | Bitmask of phases currently in Green display. |
| `status_veh_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.8.1` | Status / Bitmask | Active vehicle detection calls reported by controller. |
| `status_ped_calls` | `1.3.6.1.4.1.1206.4.2.1.1.4.1.9.1` | Status / Bitmask | Active pedestrian push-button calls reported by controller. |
| `omit` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.2.1` | Control / Bitmask | Omits specific phases from service. |
| `hold` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1` | Control / Bitmask | Holds active phase green (`ascPhaseControlHold`). |
| `force_off` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.5.1` | Control / Bitmask | Forces termination of current green phase (`ascPhaseControlForceOff`). |
| `veh_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.6.1` | Control / Bitmask | Injects synthetic vehicle detection call (`ascPhaseControlVehCall`). |
| `ped_call` | `1.3.6.1.4.1.1206.4.2.1.1.5.1.7.1` | Control / Bitmask | Injects synthetic pedestrian call (`ascPhaseControlPedCall`). |

---

## 3. UTMC / UTMC2 Driver & SNMPv3 USM Support

For intersections utilizing the UK **Urban Traffic Management and Control (UTMC)** framework or authenticated **SNMPv3** field cabinets:

### 3.1 File Architecture
**Go Gateway Implementation (`src_go/`):**
- [`src_go/pkg/utmc/driver.go`](../../src_go/pkg/utmc/driver.go): Native Go UTMC communication handler with thread-safe `Probe()` and `CloseTransport()`.
- [`src_go/pkg/utmc/telemetry.go`](../../src_go/pkg/utmc/telemetry.go): Stage confirmation (`status_active`, `status_leaving`, `status_demand` -> `1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1`, `status_ped_demand`).
- [`src_go/pkg/utmc/action_executor.go`](../../src_go/pkg/utmc/action_executor.go): Stage demand, hold, force-off, and intergreen-safe logical action execution.
- [`src_go/pkg/utmc/stage_mapper.go`](../../src_go/pkg/utmc/stage_mapper.go): Maps UTMC stages (Stage 1..8) to CARINA neural actions.
- [`src_go/pkg/utmc/config.go`](../../src_go/pkg/utmc/config.go) & [`src_go/configs/utmc_oids.json`](../../src_go/configs/utmc_oids.json): Embedded UTMC OID profile definitions.
- [`src_go/pkg/snmp/config.go`](../../src_go/pkg/snmp/config.go): **SNMPv3 USM Engine** supporting `NoAuthNoPriv`, `AuthNoPriv`, and `AuthPriv` with auth protocols (`MD5`, `SHA`, `SHA224`, `SHA256`, `SHA384`, `SHA512`) and privacy encryption (`DES`, `AES`, `AES192`, `AES256`, `AES192C`, `AES256C`). Per-intersection `snmp_config` JSON metadata and `config_path` OID overrides propagate from [`HardwareConnectionRepository`](../../src/repositories/hardware_connection_repo.py) and [`ConnectionCSVStore`](../../src/repositories/connection_csv_store.py) through [`DriverFactory`](../../src/drivers/driver_factory.py) to `GoGatewayClient`.

---

## 4. EVP Hardware Preemption Dispatcher (`src_go/evp_go/`)

The **EVP Preemption Dispatcher** ([`src_go/evp_go/dispatcher.go`](../../src_go/evp_go/dispatcher.go)) handles real-time emergency green corridor requests with sub-millisecond physical controller actuation:

- **Bypasses Inference Cycle:** Preemption triggers bypass the standard neural network action selection and inter-intersection coordination cycles, directly asserting green holds on target signal phases.
- **SNMP OID Hold Insertion:** Translates green stage indices (`stage_idx` and `stage_codes`) to NTCIP `phase_control.hold` (`1.3.6.1.4.1.1206.4.2.1.1.5.1.4.1`) or UTMC stage hold bitmasks, maintaining conflicting traffic in red while granting uninterrupted right-of-way.
- **Microsecond IPC Protocol:** Activated via the `evp_preempt` NDJSON command over OS pipes:
  ```json
  {"cmd": "evp_preempt", "intersection_id": "cruzamento_av_jk_01", "action_type": "activate_preempt", "target_stage": 1, "vehicle_id": "SAMU-01"}
  ```
- **Failsafe Watchdog & Hold Release:** Holds are released either when the vehicle crosses the exit threshold ($\le 15\text{ m}$) or upon expiration of the maximum dwell watchdog timer ($45\text{ s}$). If the gateway crashes or disconnects, physical controllers automatically release holds after 3 dropped heartbeats.

---

## 5. Remote Web Gateway & Mesh Networking (`src_go/web_gateway/`)

For distributed smart city architectures where emergency vehicles or central operators need remote connectivity without public IP exposure:

- **Tailscale Encrypted Mesh:** Integrated via [`src_go/web_gateway/tailscale.go`](../../src_go/web_gateway/tailscale.go), enabling CARINA edge controllers to form secure, end-to-end encrypted zero-trust overlay networks.
- **Tailscale Funnel (Port 2201):** Publicly exposes high-throughput ingestion endpoints over TLS without opening local firewall ports or configuring port forwarding.
- **High-Throughput Telemetry Receiver:** Exposes `POST /api/v1/evp/telemetry` (HTTP 204 fire-and-forget) to ingest high-frequency vehicle GPS beacons with sub-millisecond response latency.
- **Server-Sent Events (SSE) Broadcast Hub:** [`src_go/web_gateway/sse_hub.go`](../../src_go/web_gateway/sse_hub.go) streams real-time intersection telemetry, emergency vehicle tracks, and signal states to Central Control Operator (CCO) videowalls via `GET /cco/stream`.

---

## 6. Hardware Management & Fail-Safe Architecture

### 6.1 Connection Lifecycle & Pooling (`src/controller/`, `src/repositories/`)
- [`src/controller/connection_manager.py`](../../src/controller/connection_manager.py) & [`connection_operation_handler.py`](../../src/controller/connection_operation_handler.py): Manage connection state machines (`DISCONNECTED`, `CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`), passive mirror views in `remote` mode (`update_remote_hardware_status`), simulator port autodetection ([`LocalSimulatorProber`](../../src/controller/local_simulator_prober.py)), and bulk CSV restoration ([`ConnectionBatchImporter`](../../src/controller/connection_batch_importer.py)).
- [`src/repositories/hardware_connection_repo.py`](../../src/repositories/hardware_connection_repo.py) & [`src/repositories/connection_csv_store.py`](../../src/repositories/connection_csv_store.py): Persist IP endpoints and optional `snmp_config` JSON (SNMPv3 USM / custom OID `config_path`) in `hardware_controller_connections` and CSV templates, preserving [`ConnectionConfigRepository`](../../src/controller/connection_config_repo.py) as a backward-compatible facade.
- [`src/controller/failsafe_manager.py`](../../src/controller/failsafe_manager.py): Executes emergency reversion via `HardwareGatewayCoordinator.on_failsafe_triggered()` and recovery via `on_failsafe_recovered()`.

### 6.2 Fail-Safe Determinism, Recovery & Binary SNMP Traps
1. **Heartbeat Loss & Reversible Failsafe:** If communication with an active controller drops or Watchdog failsafe triggers, `EmergencyReleaseControlAll()` pauses heartbeats and releases phase holds while keeping SNMP drivers and the trap listener alive so `resume_control` (`ResumeControlAll()`) can resume smoothly on recovery. On process exit or `EOF`/`SIGPIPE`, `ShutdownAll()` permanently releases holds and closes sockets.
2. **Intergreen Protection (`HardwareStageActuator`):** [`src/drivers/hardware_stage_actuator.py`](../../src/drivers/hardware_stage_actuator.py) skips conflicting `send_stage_hold` calls during yellow/all-red intergreen intervals (`_is_intergreen_stage`) and resolves `tl_`-prefixed IDs uniformly.
3. **Binary SNMPv1/v2c/v3 Trap Decoder (`src_go/pkg/traplistener/snmp_decoder.go`):** Parses ASN.1 BER binary Trap/Inform packets on UDP port `162` (`CARINA_TRAP_PORT`), classifying `coldStart`, `warmStart`, `linkDown`, `linkUp`, `authenticationFailure`, NTCIP (`.1206.*`), and UTMC (`.13267.*`, `.2825.*`) alarms by severity (`CRITICAL`, `WARNING`, `INFO`).
4. **Safety Conflict Intercept:** All outgoing actions pass through [`src/controller/stage_validator.py`](../../src/controller/stage_validator.py) before dispatch, verifying intergreen clearance and conflict matrices.

### 6.3 Hardware Incident Reporting & Deduplication (`src/drivers/`)
- [`src/drivers/incident_reporter.py`](../../src/drivers/incident_reporter.py): Intercepts controller hardware status changes (`CONNECTING`, `ONLINE`, `DEGRADED`, `FAILSAFE`) and constructs standardized incident JSON messages.
- [`src/drivers/incident_filter.py`](../../src/drivers/incident_filter.py): Prevents notification storms by caching active incident hashes with timestamp debouncing in `.carina_incident_filter_cache.json`.
- Dispatches alerts dynamically via `MonitorClient` to the configured telemetry transport (local MQTT broker or remote HTTP/Ngrok endpoint).

---

## 7. Security & Network Credentials

Hardware credentials must never be hardcoded. CARINA resolves SNMP and controller secrets through environment variables defined in [`.env`](../../.env.example):

```bash
CARINA_SNMP_COMMUNITY=public
CARINA_ENV=production
```

For security configurations and user roles, see [Security & Authentication](security_and_auth.md).
For telemetry serialization schemas, see [API Reference](api_reference.md).

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
