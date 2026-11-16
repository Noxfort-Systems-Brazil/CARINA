---
tags: [api, grpc, ipc, reference, protobuf]
aliases: [API Reference, Synapse HFT, IPC Queues, gRPC Interface]
---

# ⚡ API Reference & Synapse HFT Protocol Specifications

This document serves as the authoritative interface specification for CARINA. It covers the **Synapse HFT gRPC Protocol**, the **Prometheus Exporter Metrics**, and the **Inter-Process Communication (IPC) Schemas**.

⬅️ Back to [Main Documentation Hub](carina_moc.md) | 🚨 See [EVP Preemption](evp_and_preemption.md) | 🚦 See [Hardware Drivers](hardware_drivers.md) | 🛡️ See [Safety & Watchdog](safety_and_watchdog.md) | 🗄️ See [Database & Schemas](database_and_schemas.md)

---

## 1. Synapse HFT gRPC Service Definition (`proto/synapse_hft.proto`)

CARINA interfaces with external sensors, physical traffic controllers, and microscopic simulation environments (SUMO/CityFlow) via the **Synapse HFT Protocol** over gRPC.

- **Default Port:** `50051` (Configurable in `config/settings.ini` under `[SYNAPSE]`)
- **Transport:** HTTP/2 over TCP with optional **TLS / mTLS** (`grpc.ssl_server_credentials`) and **Bearer Token Authentication** (`BearerTokenServerInterceptor` in [`src/communication/grpc_security.py`](../../src/communication/grpc_security.py)) configured via `CARINA_GRPC_AUTH_TOKEN`, `CARINA_GRPC_TLS_ENABLED`, `CARINA_GRPC_TLS_CERT`, `CARINA_GRPC_TLS_KEY`, `CARINA_GRPC_TLS_CA`, and `CARINA_GRPC_REQUIRE_CLIENT_CERT`. Accepts `Authorization: Bearer <token>` or `x-carina-token: <token>` metadata verified via constant-time `hmac.compare_digest`.
- **Protocol Package:** `synapse.hft`

```protobuf
syntax = "proto3";
package synapse.hft;

service HFTLink {
  rpc Ping (Empty) returns (SystemState);
  rpc LoadScenario (ScenarioDefinition) returns (ScenarioStatus);
  rpc SystemControl (ControlCommand) returns (CommandResponse);
  rpc StreamTraffic (stream TrafficFrame) returns (SystemState);
}
```

### 1.1 gRPC RPC Methods Breakdown

#### `Ping`
- **Request:** `Empty`
- **Response:** `SystemState` (returns server status, active boolean flag, and UTC epoch timestamp `server_time`).
- **Latency Target:** $< 1\text{ ms}$

#### `LoadScenario`
- **Request:** `ScenarioDefinition` (transfers binary map geometry `.net.xml.gz`, topology nodes/edges, and peak schedule JSON extracted by the ADAGIO classifier).
- **Response:** `ScenarioStatus` (`accepted` boolean and status message).

#### `SystemControl`
- **Request:** `ControlCommand` (Enum action: `START`, `PAUSE`, `STOP`, `RESET`).
- **Response:** `CommandResponse` (`success` boolean and `new_state` string).

#### `StreamTraffic`
- **Request:** `stream TrafficFrame` (High-frequency streaming of edge occupancy, vehicle speeds, queue lengths, and densities).
- **Response:** `SystemState`

---

## 2. Telemetry & Control Message Schemas

### 2.1 `TrafficFrame`
```protobuf
message TrafficFrame {
  double timestamp = 1;
  uint64 sequence_id = 2;
  map<string, EdgeState> edges = 3;
}

message EdgeState {
  float occupancy = 1;      // Ratio [0.0 - 1.0] of road occupancy
  float mean_speed = 2;     // Space-mean speed in m/s
  int32 queue_length = 3;   // Number of stopped vehicles in queue
  float density = 4;        // Vehicles per kilometer
}
```

### 2.2 `ScenarioDefinition`
```protobuf
message ScenarioDefinition {
  string map_hash = 1;
  TopologyGraph graph = 2;
  MapGeometry geometry = 3;
  bytes map_file_content = 4;
  string map_file_name = 5;
  string peak_schedule_json = 6;
}
```

---

## 3. Inter-Process Communication (IPC) Queue Specifications

CARINA coordinates **12 bounded IPC queues** and **1 thread-safe duplex pipe connection** (`ThreadSafePipeConnection` in [`src/communication/pipe_utils.py`](../../src/communication/pipe_utils.py)) managed by [`ProcessManager`](../../src/launcher/process_manager.py):

| Queue Name | Max Size | Producer Process | Consumer Process | Payload Schema / Message Type |
| :--- | :---: | :--- | :--- | :--- |
| **`controller_conn` / `ai_conn`** | Pipe | `CentralController` ↔ `AI_Process` | Bidirectional | `("custom", "hft_step", ...)`, `("hft_telemetry_push", ...)`, `("ai_hardware_cmd", ...)`, `("ai_evp_preempt", ...)`, `("fenix_handover_complete", ...)` |
| **`wd`** | 500 | `CentralController` / Microservices | `Watchdog` | `{"process": str, "timestamp": float, "status": "ALIVE"}` |
| **`fenix`** | 50 | `Watchdog` / `CentralController` | `FenixSupervisionController` | `("TRIGGER_RESURRECTION", reason)` / `("HANDOVER_COMPLETE", payload)` |
| **`sds`** | 500 | `CentralController` | `DashboardService` | `("hft_rich_update", payload)` (fast 0.5s & slow heatmap telemetry + `hardware_status`) |
| **`sas`** | 500 | `CentralController` | `AnalysisService` | Historical traffic metrics for PostgreSQL aggregation |
| **`ui`** | 500 | `UITrayManager` / `LiveDataProvider` | `CentralController` | UI commands, `set_hardware_connection`, `tailscale_*`, `fenix_post_resurrection` |
| **`ui_telemetry`** | 500 | `DashboardService` | `LiveDataProvider` | Zero-port in-memory real-time telemetry packets, congestion & maturity |
| **`db`** | 500 | `AI_Process` | `DatabaseWorker` | `(state_tensor, action_int, reward_float, next_state_tensor)` |
| **`g_state`** | 500 | `AI_Process` | `GuardianWorker` | `(lane_queues, pae_latent_vector_z, strategic_gat_vector)` |
| **`g_signal`** | 500 | `GuardianWorker` | `AI_Process` | `{"veto": bool, "forced_phase": int, "risk_score": float}` |
| **`sas_results`** | 10 | `AnalysisService` | `InfrastructureClient` | Engineering warrant reports & signal timing recommendations |
| **`mfd_trigger`** | 10 | `MfdAnalysisClient` / `CC` | `MFD_Worker` | `{"action": "COMPUTE_MFD", "time_window_seconds": 3600}` |
| **`mfd_results`** | 10 | `MFD_Worker` | `MfdAnalysisClient` / `CC` | `{"critical_density": float, "max_capacity_flow": float, "curve": list}` |

For physical controller actuation via NTCIP and UTMC, see [Hardware Drivers](hardware_drivers.md).

---

## 4. Prometheus Exporter Metrics

The `MetricsManager` exposes real-time operational telemetry on **HTTP port 8001** (path `/metrics`).

```text
# Prometheus Metric Summary:
carina_step_latency_seconds_bucket{le="0.005"}   # gRPC telemetry to actuation latency histogram
carina_ppo_reward_total                          # Cumulative reward for PPO Tactical Agent
carina_guardian_veto_total{type="symbolic"}      # Counter of symbolic safety vetoes
carina_guardian_veto_total{type="neural"}        # Counter of PAE neural spillback vetoes
carina_mfd_network_density_veh_km               # Macroscopic network density
carina_mfd_network_flow_veh_hr                   # Macroscopic network throughput
carina_active_processes_count                    # Count of alive backend microservices
```

---

## 5. External Monitor Telemetry & Polling Protocols (`src/transports/`)

CARINA dispatches real-time state heartbeats and hardware alerts to external operations dashboards and cloud telemetry platforms via [`MonitorClient`](../../src/communication/monitor_client.py) and [`src/transports/`](../../src/transports).

### 5.1 Telemetry Payloads

#### Incident Alert Payload (`noxfort/incidents/` or HTTP POST)
```json
{
  "intersection_id": "cruzamento_av_jk_01",
  "level": "CRITICAL",
  "category": "HARDWARE_DISCONNECT",
  "message": "[FailsafeManager] Controller dropped connection. Reverting to fixed-time.",
  "occurred_at": "2026-09-15T01:30:00Z",
  "is_active": true
}
```

#### Heartbeat Telemetry Payload (`noxfort/telemetry/` or HTTP POST)
```json
{
  "message": "heartbeat",
  "timestamp": 1789458600.0,
  "system_status": "ONLINE",
  "active_intersections": 12,
  "failsafe_active": false
}
```

### 5.2 Transport Protocols

| Protocol | Config Example (`CARINA_MQTT_HOST`) | Implementation | Characteristics |
| :--- | :--- | :--- | :--- |
| **MQTT Broker** | `127.0.0.1:1883` or `broker.emqx.io` | [`MonitorMqttTransport`](../../src/transports/mqtt_transport.py) | Paho MQTT v2, keepalive 60s, topics `noxfort/telemetry/` and `noxfort/incidents/`. |
| **HTTP / HTTPS REST** | `https://monitor.noxfort.com/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | JSON `POST`, persistent `requests.Session`, exponential backoff, timeout 3.0s. |
| **Cloud Tunnels (Ngrok)** | `https://xxxx.ngrok-free.dev/api/telemetry` | [`MonitorHttpTransport`](../../src/transports/http_transport.py) | Automatic detection via `endpoint_resolver.py` routing through secure HTTPS tunnel. |

### 5.3 Endpoint Classification Rules
The factory function [`create_monitor_transport()`](../../src/transports/factory.py) automatically resolves the correct transport:
1. If the host string starts with `http://` or `https://` $\implies$ **HTTP Transport**.
2. If the host string contains `.ngrok`, `.run.app`, or an `/api/` path $\implies$ **HTTP Transport** (auto-prepends `https://` if protocol scheme was omitted).
3. If the host string contains an IP address or domain with optional port (e.g. `10.0.0.1:1883`) $\implies$ **MQTT Transport**.

---

## 6. Emergency Vehicle Telemetry Ingestion HTTP API

The compiled Go Web Gateway exposes high-throughput, unidirectional (fire-and-forget) ingestion for emergency vehicle GPS transponders:

- **Endpoint:** `POST /api/v1/evp/telemetry` (alias: `POST /amb` or `POST /amb/`)
- **Port:** `2201` (`CARINA_GATEWAY_PORT`, Go Web Gateway / Tailscale Funnel) or `8085` (dedicated Go EVP server [`src_go/evp_go/`](../../src_go/evp_go))
- **Security:** Fail-closed when `CARINA_GATEWAY_ENABLED=False` (returns `503 Service Unavailable`); validates `CARINA_EVP_AUTH_TOKEN` in constant time via `Authorization: Bearer <token>`, `X-EVP-Token`, or `X-Auth-Token` (returns `401 Unauthorized` on mismatch) and supports HTTPS/TLS (`CARINA_GATEWAY_TLS_CERT` / `CARINA_GATEWAY_TLS_KEY`).
- **Response:** `204 No Content` (Immediate return for sub-millisecond execution)
- **Payload Schema:**
  ```json
  {
    "vehicle_id": "SAMU-01",
    "corporation": "SAMU",
    "latitude": -23.31028,
    "longitude": -51.16278,
    "speed_kmh": 65.4,
    "heading_deg": 180.0,
    "siren_active": true,
    "timestamp": 1789458600.0
  }
  ```

---

## 7. Go Hardware & Web Gateway NDJSON IPC Command Set

Commands dispatched from CARINA's owner process (`CentralController`) to `bin/carina-go` via anonymous standard pipes (`stdin`/`stdout`):

| Command (`cmd`) | Arguments / Payload | Response Data | Description |
| :--- | :--- | :--- | :--- |
| **`ping`** | None | `"pong"` | Verifies gateway liveness ($< 1\text{ ms}$). |
| **`connect`** | `intersection_id`, `ip`, `port`, `community`, `snmp_config`, `config_path`, `protocol`, `green_stages` | Connection metadata | Establishes SNMPv2c/v3 UDP session and optional custom OID JSON profile. |
| **`disconnect`** | `intersection_id` | `success: true` | Closes connection and releases socket. |
| **`apply_logical_action`** | `action` (0=NEXT, 1=HOLD), `current_stage_idx`, `green_stages`, `stage_codes` | `success: bool` | Applies neural or safety action to physical signal groups. |
| **`evp_preempt`** | `intersection_id`, `action_type` ("activate_preempt"/"release_preempt"), `target_stage`, `stage_idx`, `stage_codes`, `vehicle_id` | Action executed string | Dispatches microsecond stage preemption holds to field controllers. |
| **`cco_broadcast`** | `data: dict` | `success: true` | Transmits fire-and-forget telemetry frames to connected CCO SSE clients. |
| **`gateway_set_enabled`** / **`gateway_get_status`** | `enabled: bool` | Status JSON | Toggles Web Gateway active guard (`503` when disabled) or inspects state. |
| **`gateway_set_auth_tokens`** | `evp_auth_token`, `cco_auth_token`, `allowed_origin` | Config flags | Dynamically rotates EVP/CCO tokens and CORS origin on running Go gateway. |
| **`tailscale_status`** / **`tailscale_enable`** / **`tailscale_disable`** | `port`, `domain` | `TailscaleStatus` JSON | Manages Tailscale Funnel domain, node state, and public CCO URLs. |
| **`emergency_release`** | None | `success: true` | Pauses heartbeats and releases phase holds while preserving drivers for recovery. |
| **`resume_control`** | None | `resumed: int` | Restarts paused controller heartbeats after Watchdog failsafe recovery. |

---

## 8. Central Control Operator (CCO) REST & SSE Endpoints

Available on Go Web Gateway port `2201` (`CARINA_GATEWAY_PORT`, HTTPS when TLS is configured, returning `503 Service Unavailable` when disabled):

- **`GET /` & `GET /health`**: Returns system health status and gateway availability.
- **`GET /cco` & `GET /cco/`**: Serves the compiled React 18 CCO web interface.
- **`GET /cco/stream`**: Server-Sent Events (SSE) persistent stream broadcasting real-time signal states, congestion heatmaps, and emergency vehicle locations to videowalls (enforces `CARINA_CCO_AUTH_TOKEN` via `Authorization: Bearer`, `X-CCO-Token`, or `?token=` query parameter, plus `CARINA_CCO_ALLOWED_ORIGIN` CORS).
- **`GET /cco/topology`**: Serves GeoJSON/JSON street link geometries, lane mappings, and junction coordinates for map rendering (token-protected).
- **`POST /cco/broadcast`**: Protected ingestion endpoint called by SDS [`CCOBroadcastClient`](../../src/sds/cco_broadcast_client.py) using latest-wins non-blocking batching, `X-CCO-Token` auth, and optional SHA-256 certificate pinning ([`PinnedHTTPSConnection`](../../src/sds/cco_tls_transport.py)).

---

## 9. Pacing, Maturation, and Weekly Coverage Utility APIs

Core Python modules and interfaces governing temporal horizons, step scaling, and maturation safety floors:

### 9.1 `EpisodeStepCalculator` (`src.utils.episode_step_calculator`)
Dynamically computes episode step horizons and weekly maturation requirements from network graph topology:
- **`calculate(net_or_path: Union[str, Any], telemetry_delta_ms: float = 250.0) -> EpisodePacingResult`**
  Parses the SUMO network (`.net.xml`/`.net.xml.gz` or in-memory `net`), collapses bidirectional two-way street pairs, excludes internal junction connectors (`:`), computes topological complexity $C_{\text{topo}}$, sub-linear physical relaxation time $T_{\text{physical}}$, and returns an immutable `EpisodePacingResult` containing `episode_steps`, `duration_seconds`, and 1-week episode safety floors (`child_episodes_1_week`, `teen_episodes_1_week`).

### 9.2 `WeeklyCoverageTracker` (`src.core.weekly_coverage_tracker`)
Tracks observation across the 168 calendar hours of the real week ($7\text{ days} \times 24\text{ hours}$) with atomic state persistence:
- **`register_step(raw_timestamp: float) -> Tuple[int, int]`**: Records telemetry frame arrivals in the `(weekday, hour)` matrix based on real UNIX timestamps.
- **`is_week_completed() -> bool`**: Returns `True` if all 168 hourly calendar slots have received observation.
- **`get_completion_ratio() -> float`**: Returns current weekly coverage proportion in $[0.0, 1.0]$.
- **`save_state() / load_state()`**: Atomically saves and restores matrix progress to/from disk (`weekly_coverage_{phase}.json`), ensuring tolerance to process pauses and server maintenance.

### 9.3 `ActionAuthorizer` (`src.core.action_authorizer`)
Authorizes physical hardware control based on maturity lifecycle stage and real calendar time:
- **`is_action_authorized(agent_id: str, maturity: Maturity, sim_time: float, raw_timestamp: float = 0.0) -> Tuple[bool, str]`**: Evaluates whether an agent may act on physical signal controllers. Restricts `TEEN` stage agents to off-peak periods, forcing shadow mode during classical urban peak hours (06:30-09:00 & 17:00-19:30 Monday-Friday) or Synapse dynamic schedules.
- **`load_peak_schedule_json(schedule_data: dict) -> None`**: Loads custom municipal or regional peak period schedules provided by Synapse.

### 9.4 `MaturityPacingCalculator` (`src.promotion.maturity_pacing_calculator`)
- **`calculate_pacing(net: Any, tls_list: Any, settings: Any = None) -> Tuple[int, int, int, int]`**: Returns `(child_episodes, teen_episodes, child_steps, teen_steps)` strictly clamped to the inviolable 1-week safety floor ($E_{\text{week}} \times S \times \Delta t \ge 604,800\text{ s}$).
- **`apply_if_enabled(maturity_manager: Any, net: Any, tls_list: Any, settings: Any) -> bool`**: Automatically injects dynamic pacing durations into `MaturityManager` and `PromotionEvaluator`.

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
