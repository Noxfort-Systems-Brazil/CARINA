---
tags: [api, grpc, ipc, reference, protobuf]
aliases: [API Reference, Synapse HFT, IPC Queues, gRPC Interface]
---

# ⚡ API Reference & Synapse HFT Protocol Specifications

This document serves as the authoritative interface specification for CARINA. It covers the **Synapse HFT gRPC Protocol**, the **Prometheus Exporter Metrics**, and the **Inter-Process Communication (IPC) Schemas**.

⬅️ Back to [Main Documentation Hub](../CARINA_MOC.md) | 🚦 See [Hardware Drivers](hardware_drivers.md) | 🛡️ See [Safety & Watchdog](safety_and_watchdog.md) | 🗄️ See [Database & Schemas](database_and_schemas.md)

---

## 1. Synapse HFT gRPC Service Definition (`proto/synapse_hft.proto`)

CARINA interfaces with external sensors, physical traffic controllers, and microscopic simulation environments (SUMO/CityFlow) via the **Synapse HFT Protocol** over gRPC.

- **Default Port:** `50051` (Configurable in `config/settings.ini`)
- **Transport:** HTTP/2 over TCP with optional TLS encryption.
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

CARINA manages 10 bounded IPC channels created by [`ProcessManager`](../../src/launcher/process_manager.py).

| Queue Name | Max Size | Producer Process | Consumer Process | Payload Schema / Message Type |
| :--- | :---: | :--- | :--- | :--- |
| **`controller_conn`** | Pipe | `CentralController` | `AI_Process` | `("state", frame_id, traffic_frame_dict)` |
| **`ai_conn`** | Pipe | `AI_Process` | `CentralController` | `("actuation", frame_id, signal_group_actions)` |
| **`wd`** | 500 | All Microservices | `Watchdog` | `{"process": str, "timestamp": float, "status": "ALIVE"}` |
| **`sds`** | 500 | `CentralController` | `DashboardService` | `{"timestamp": float, "telemetry": dict, "active_phase": int}` |
| **`sas`** | 500 | `CentralController` | `AnalysisService` | Historical traffic metrics for PostgreSQL aggregation |
| **`ui`** | 500 | `UITrayManager` / `LiveDataProvider` | `CentralController` | UI commands, overrides, manual timing & settings |
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
