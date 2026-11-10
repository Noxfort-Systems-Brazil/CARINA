---
tags: [architecture, core, system, gatv2, pae, pbt, amp, multiprocessing]
aliases: [System Architecture, Multiprocessing Blueprint, System Overview]
---

# 🏛️ CARINA: System Blueprint & Multiprocessing Architecture

This document specifies the internal engineering architecture of the CARINA ecosystem. It details the 8 concurrent operating system microservices, the canonical deep neural network topology (LocalAgent PPO-TCN, GuardianAgent D3QN, and StrategistAgent ST-GATv2 Lite), the `TopologicalScaler`, physical controller drivers, and the asynchronous PostgreSQL delta storage engine.

⬅️ Back to [Main Documentation Hub](CARINA_MOC.md) | 🚨 See [EVP Preemption](EVP_AND_PREEMPTION.md) | 🚦 See [Hardware Drivers](HARDWARE_DRIVERS.md) | 🧠 See [Neural Formulations](RESEARCH_NOTES.md) | 🛡️ See [Safety & Watchdog](SAFETY_AND_WATCHDOG.md)

---

## 1. Multiprocessing Microservices Concurrency Model

Python's Global Interpreter Lock (GIL) prevents multi-threaded CPU-bound AI inference and heavy I/O operations from running in true parallelism. To achieve sub-millisecond actuation latency, CARINA employs a **multiprocessing microservice model** orchestrated by [`carina.py`](../carina.py) and [`src/launcher/process_manager.py`](../src/launcher/process_manager.py), combined with an industrial-grade **Go Hardware & Web Gateway** (`bin/carina-go`):

```mermaid
graph TD
    Launcher[carina.py Orchestrator / UI Tray] -->|Spawns & Monitors| PM[ProcessManager]

    PM --> CC[1. CentralController Process]
    PM --> AI[2. AI_Process Engine]
    PM --> WD[3. Watchdog Process]
    PM --> SDS[4. DashboardService SDS]
    PM --> SAS[5. AnalysisService SAS]
    PM --> DB[6. StepDecisionWorker & DatabaseWorker]
    PM --> XAI[7. XAI_Worker LLM]
    PM --> MFD[8. MFD_Worker Engine]

    CC <-->|IPC Pipe| AI
    CC -->|wd Queue (Heartbeats)| WD
    AI -->|db Queue| DB
    CC -->|sds Queue| SDS
    CC -->|sas Queue| SAS
    CC -->|mfd_trigger Queue| MFD
    MFD -->|mfd_results Queue| CC
    SAS -->|sas_results Queue| CC
    XAI -->|Disk HFT Logs| AI

    CC <-->|NDJSON Stdin/Stdout| GW[Go Gateway carina-go]
    GW --> NTCIP[NTCIP / UTMC Field Controllers UDP 161]
    GW --> WebGW[Go Web Gateway Port 2201 / Tailscale]
    WebGW --> CCO[CCO Web Map React/TSX src_tsx]
    WebGW <--|POST 204 Telemetry| EVP[EVP GPS Antennas Port 8085]
```

---

## 2. Advanced Deep Learning Architecture

```text
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        TOPOLOGICAL SCALER (O(1))                        │
    │   Auto-detects Map Nodes (N) -> Latent Dim (32/64/128/256), Heads (2/4/8/16)│
    └────────────────────────────────────┬────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
     ┌─────────────────────────────┐           ┌─────────────────────────────┐
     │     LOCAL AGENT (PPO)       │           │   STRATEGIST AGENT (GRAPH)  │
     │  Tactical TCN Backbone      │           │   ST-GATv2 Lite Coordinator │
     │  (Sub-second Actuation)     │◄──────────┤   (Arterial Green Waves)    │
     └──────────────┬──────────────┘Context Vec└──────────────┬──────────────┘
                    │                                         │
                    │ Proposed Action                         │ Network Context
                    ▼                                         ▼
     ┌───────────────────────────────────────────────────────────────────────┐
     │                      GUARDIAN AGENT (D3QN + CTB)                      │
     │   Neuro-Symbolic Safety Shield, Spillback Prevention & Traffic Veto   │
     └───────────────────────────────────┬───────────────────────────────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │  UNIVERSAL AMP & TENSORCORE │
                          │ (torch.amp.autocast FP16)   │
                          └─────────────────────────────┘
```

### 2.1 ST-GATv2 Lite Module (`src/models/st_gatv2_lite.py`)
- **Purpose:** Spatial synchronization of arterial "Green Waves" across neighboring intersections in the urban road network graph.
- **Dynamic Weighting:** While the physical road topology is static, dynamic spatial attention coefficients $\alpha_{ij}(t)$ are recomputed in real time based on incoming vehicle densities and velocity gradients.
- **Decentralized Coordination:** The Strategist periodically computes the spatiotemporal context tensor across the network and feeds it to Local and Guardian agents, enabling emergent green waves without centralized single-point-of-failure commands.

### 2.2 Universal Predictive Autoencoder (`src/models/pae.py`)
- **Purpose:** Shared high-capacity physical representation engine compressing multi-step sequential dynamics into invariant latent spaces ($Z \in \mathbb{R}^{16\dots 128}$).
- **Targeted Enrichment:** Provides compact temporal-predictive latent state representations to empower both LocalAgent policy decisions and GuardianAgent spillback auditing.

### 2.3 $O(1)$ Topological Auto-Scaler (`src/utils/topo_scaler.py`)
- **Algorithmic Scaling:** Auto-detects network density ($N$ intersections) and autonomously adjusts neural dimensions in powers of 2 optimized for NVIDIA TensorCores:
  - $N \le 20 \implies \text{dim} = 32, \text{heads} = 2$
  - $20 < N \le 80 \implies \text{dim} = 64, \text{heads} = 4$
  - $80 < N \le 250 \implies \text{dim} = 128, \text{heads} = 8$ (e.g., Londrina Metropolitan Grid)
  - $N > 250 \implies \text{dim} = 256, \text{heads} = 16$ (Megalopolis Grid)

### 2.4 Universal AMP & TensorCore Acceleration
- All neural network forward passes are enveloped in `torch.amp.autocast`, enabling native FP16/TF32 hardware acceleration across NVIDIA TensorCores and restricting total VRAM consumption to only **~20 MB** for the core models.

---

## 3. Persistent Data & Delta Storage Engine

CARINA implements an asynchronous persistence engine featuring **Run-Length Delta Compression** in PostgreSQL:
- **`step_decisions`**: Stores suggestions, Guardian safety vetoes, and step timers dispatched via [`StepDecisionWorker`](../src/database/step_decision_worker.py) in non-blocking RAM queues ($< 0.001\text{ ms}$ overhead).
- **`edge_dictionary`**: Maps long road names to 4-byte integers for compact indexing.
- **Storage Reduction:** Achieves a **97.9% storage footprint reduction** (~380 MB/day for a 200-intersection metropolitan network).

For database schemas and query details, see [Database Architecture & Schemas](DATABASE_AND_SCHEMAS.md).

---

## 4. Modular Settings Architecture (`src/settings/`)

To adhere to the **Single Responsibility** and **Interface Segregation** principles (SOLID), CARINA's configuration management is decomposed into decoupled, testable components:

```text
       ┌────────────────────────────────────────────────────────┐
       │               SettingsService (Orchestrator)           │
       └───────────┬────────────────────────────────┬───────────┘
                   │                                │
        ┌──────────┴──────────┐          ┌──────────┴──────────┐
        ▼                     ▼          ▼                     ▼
┌───────────────┐     ┌──────────────┐ ┌────────────────┐ ┌──────────────────────┐
│SettingsSchema │     │ISettingsRead │ │IniFileStorage  │ │DotenvSecretProvider  │
│(Validation &  │     │& Write       │ │(settings.ini   │ │(.env 12-Factor App   │
│ Section Map)  │     │(Interfaces)  │ │ File I/O)      │ │ Environment Secrets) │
└───────────────┘     └──────────────┘ └────────────────┘ └──────────────────────┘
                   ▲
                   │ Backwards Compatibility Facade
        ┌──────────┴──────────┐
        │   SettingsManager   │ (src/utils/settings_manager.py)
        └─────────────────────┘
```

- **`SettingsSchema` (`src/settings/schema.py`):** Authoritative registry defining key-to-section mappings, default fallback values, and type validation rules.
- **`IniFileStorage` (`src/settings/ini_storage.py`):** Handles file reading and persistent writing to `config/settings.ini`.
- **`DotenvSecretProvider` (`src/settings/env_provider.py`):** Resolves sensitive infrastructure secrets from `.env` using `python-dotenv` with fallback file parsing.
- **`SettingsService` (`src/settings/service.py`):** Core service orchestrating configuration retrieval, validation, and serialization.
- **`SettingsManager` (`src/utils/settings_manager.py`):** Drop-in backwards compatibility facade guaranteeing zero regressions for legacy callers.

---

## 5. Polymorphic Monitoring & Transport Architecture (`src/transports/`)

CARINA features a **polymorphic telemetry and incident transport layer** enabling real-time remote monitoring over local MQTT brokers, remote webhooks, Cloud REST APIs, or tunneling solutions (e.g., Ngrok):

```text
IncidentReporter / TelemetryLoop
            │
            ▼
┌───────────────────────┐
│     MonitorClient     │ (Singleton Facade)
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│create_monitor_transport│ (Factory with Automatic Endpoint Resolution)
└───────────┬───────────┘
            ├──────────────────────────────────────────┐
            ▼                                          ▼
┌───────────────────────────┐             ┌───────────────────────────┐
│   MonitorMqttTransport    │             │   MonitorHttpTransport    │
│  (Local / Network Broker) │             │(REST API / Cloud / Ngrok) │
│ - Host:Port (e.g. :1883)  │             │ - http:// or https://     │
│ - QoS 0/1 Telemetry       │             │ - Persistent HTTP Session │
│ - Topics: noxfort/telem/  │             │ - Exponential backoff retry│
└───────────────────────────┘             └───────────────────────────┘
```

### 5.1 Transport Abstraction (`BaseMonitorTransport`)
Defines the strict contract for all external telemetry exporters:
- `setup()`: Configures endpoints, timeouts, and credentials.
- `ensure_connected()`: Establishes or validates connectivity.
- `publish(topic, payload)`: Transmits JSON payloads asynchronously or in dedicated worker threads.
- `disconnect()`: Flushes pending buffers and cleanly terminates sessions.

### 5.2 Automatic Endpoint Resolution (`endpoint_resolver.py`)
Intelligently classifies target endpoints without requiring explicit protocol configuration:
- URLs starting with `http://` or `https://` (or domains containing `ngrok`, `run.app`, or `/api/`) instantiate `MonitorHttpTransport`.
- Standard hostname/IP strings (`localhost`, `10.0.0.1`, `broker:1883`) instantiate `MonitorMqttTransport`.

### 5.3 Incident Deduplication & Alert Filtering (`src/drivers/`)
- [`IncidentReporter`](../src/drivers/incident_reporter.py) broadcasts hardware connection state changes and controller errors to external monitoring tools.
- [`IncidentFilter`](../src/drivers/incident_filter.py) suppresses alert floods by caching active incident hashes with timestamp debouncing, maintaining `.carina_incident_filter_cache.json` across system lifecycles.

---

## 6. High-Performance Field Hardware Gateway (`src_go/`)

To achieve industrial-grade reliability, sub-millisecond network determinism, and zero GIL contention in field deployments, CARINA offloads all real-world traffic signal controller communication (UDP ports 161 and 162) to a dedicated, compiled **Go Hardware Gateway** (`bin/carina-go` built from `src_go/`):

```text
       ┌────────────────────────────────────────────────────────┐
       │                      CARINA CORE                       │
       │                                                        │
       │   [Synapse Perception]  <-- gRPC (50051) -->  [Camera] │
       │            │                                           │
       │      [AI Engine / NN]                                  │
       │            │                                           │
       │     [ActionSupervisor]                                 │
       │            │                                           │
       │ [HardwareConnectionManager] (Python Orchestrator)      │
       │            │                                           │
       │    [GoGatewayClient] (Pipe Subprocess Manager)         │
       └────────────┬───────────────────────────────────────────┘
                    │ stdin / stdout (Line-Delimited JSON)
                    │ ZERO OPEN NETWORK PORTS ON HOST
                    ▼
       ┌────────────────────────────────────────────────────────┐
       │          CARINA HARDWARE GATEWAY (Go Daemon)           │
       │                    (bin/carina-go)                     │
       │                                                        │
       │  +-- [NDJSON IPC Scanner & Concurrent Writer]          │
       │  +-- [HardwareManager Connection Registry]             │
       │  +-- [Atomic Fail-Safe on EOF / SIGPIPE]               │
       │  +-- [Heartbeat Engine: time.Ticker per intersection]  │
       │  +-- [NTCIP 1202 & UTMC2 Protocol Dispatchers]         │
       │  +-- [GoSNMP Client Pool (UDP 161)]                    │
       │  +-- [TrapListener Server (UDP 162)]                   │
       └────────────────────┬──────────────────┬────────────────┘
                            │ UDP 161          │ UDP 162 (Traps)
                            ▼                  ▼
                    [Field Controller]   [Field Controller] ...
```

### 6.1 Key Architectural Properties
- **Zero Host Ports Opened:** The control link between Python and Go runs exclusively over standard anonymous pipes (`pipe(2)` kernel ring buffers). No localhost ports, sockets, or HTTP services are exposed.
- **Atomic Safety Fail-Safe:** If the Python AI process crashes or closes, the kernel closes the pipe. The Go binary detects `EOF` on `os.Stdin` in microseconds and immediately triggers `EmergencyReleaseControlAll()` via SNMP, safely releasing remote holds and returning controllers to their local autonomous plans.
- **Zero GIL Contention:** Goroutines handle concurrent polling, 2.0s keepalive heartbeats, and UDP 162 trap reception independently of Python's heavy PyTorch tensor operations.
- **Seamless Adapter (`GoTrafficDriverProxy`):** Adheres to the Liskov Substitution Principle (LSP) by implementing `BaseTrafficDriver`, making the Go gateway 100% transparent to the rest of the CARINA codebase.

---

## 7. F.E.N.I.X. Process Supervisor & Crash Recovery Subsystem (`src/fenix/`)

CARINA incorporates **F.E.N.I.X.** (Fault-tolerant Engine for Networked Intelligent eXecution) to guarantee 24/7 continuous autonomous self-healing for the AI inference engine:

```text
       ┌────────────────────────────────────────────────────────┐
       │                 Watchdog Health Monitor                │
       └───────────────────────────┬────────────────────────────┘
                                   │ Timeout / Missed Heartbeat
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │            FenixSupervisor (Orchestrator)              │
       └──────────────┬───────────────────────────┬─────────────┘
                      │                           │
                      ▼                           ▼
       ┌────────────────────────────┐ ┌─────────────────────────┐
       │WindowedCrashRecoveryPolicy │ │    SubprocessRunner     │
       │- Sliding window backoff    │ │- Subprocess lifecycle   │
       │- Max restarts quota limiter│ │- SIGTERM / SIGKILL      │
       └────────────────────────────┘ └───────────┬─────────────┘
                                                  │ Respawn
                                                  ▼
                                      ┌─────────────────────────┐
                                      │     StateReconciler     │
                                      │- FROZEN_SYNC telemetry  │
                                      │- Boundary Handshake     │
                                      │- Zero-collision handover│
                                      └─────────────────────────┘
```

- **`FenixSupervisor` (`src/fenix/fenix_supervisor.py`):** Coordinates subprocess termination, recovery backoff, child resurrection, and state reconciliation.
- **`WindowedCrashRecoveryPolicy` (`src/fenix/recovery_policy.py`):** Computes exponential backoffs and enforces restart rate limits to prevent cascading restart storms.
- **`SubprocessRunner` (`src/fenix/process_runner.py`):** Low-level subprocess management ensuring deterministic process isolation and clean SIGTERM/SIGKILL termination.
- **`StateReconciler` (`src/fenix/state_reconciler.py`):** Ensures the resurrected AI engine operates in `FROZEN_SYNC` mode and only assumes actuation control at clean phase boundaries when physical controllers transition stages naturally.

---

## 8. Agent Lifecycle, Intra-Phase PBT & Promotion Engine (`src/maturity/`, `src/promotion/`, `src/core/`)

CARINA structures reinforcement learning policies as an evolving organism undergoing a 3-stage developmental curriculum:

```text
  ┌──────────────────┐        Entropy Drop & Pacing       ┌──────────────────┐       Entropy & Fluid Margin (delta*)     ┌──────────────────┐
  │   CHILD STAGE    │ ─────────────────────────────────> │    TEEN STAGE    │ ───────────────────────────────────────>  │   ADULT STAGE    │
  │  (Shadow Mode)   │                                    │(Off-Peak Autonomy│                                           │ (Full Autonomy)  │
  └────────┬─────────┘                                    └────────┬─────────┘                                           └────────┬─────────┘
           │                                                       │                                                              │
           ▼                                                       ▼                                                              ▼
  [Shielded from PBT]                                     [Intra-Phase PBT]                                             [Intra-Phase PBT]
  [Observes Fluid Dynamics]                               (TEEN <-> TEEN only)                                          (ADULT <-> ADULT only)
  [1-Week Safety Floor]                                   [Peak Gated Shadow Mode]                                      [24/7 Full Actuation]
```

- **`MaturityManager` (`src/maturity/maturity_manager.py`):** Central Application Service and Facade orchestrating agent maturity evaluations, supported by the rich entity `AgentMaturity`, `MaturityConfig`, and `MaturityPromotionService`.
- **`PopulationManager` (`src/core/population_manager.py`):** Executes **Intra-Phase Population-Based Training**. Agents clone and mutate strictly within their peer cohort (`TEEN` with `TEEN`, `ADULT` with `ADULT`), while `CHILD` agents remain completely shielded. Includes tensor dimension verification to prevent crashes across heterogeneous intersections.
- **`PromotionEvaluator` (`src/promotion/promotion_evaluator.py`):** Rigorously checks Shannon policy entropy, minimum episode durations, and performance targets.
- **`EpisodeStepCalculator` (`src/utils/episode_step_calculator.py`):** Dynamically scales episode step horizons from network graph topology (collapsing bidirectional two-way corridors, filtering internal connectors `:`, and applying sub-linear $\sqrt{N}$ and $D_{\text{km}}$ scaling), determining the inviolable 1-week safety floor ($E_{\text{week}}$ episodes at $\Delta t = 250\text{ ms}$).
- **`WeeklyCoverageTracker` (`src/core/weekly_coverage_tracker.py`):** Tracks and atomically persists coverage across all 168 calendar hours of the real week ($7\text{ days} \times 24\text{ hours}$), ensuring tolerance to process pauses and server maintenance without progress reset.
- **`ActionAuthorizer` (`src/core/action_authorizer.py`):** Restricts physical signal control for `TEEN` stage agents, forcing shadow mode during classical urban peak hours (06:30-09:00 & 17:00-19:30 Monday-Friday) or Synapse dynamic schedules.
- **`MaturityPacingCalculator` (`src/promotion/maturity_pacing_calculator.py`):** Orchestrates dynamic pacing integrating `EpisodeStepCalculator` and enforcing the inviolable 1-week floor ($t_{\min} = \max(E_{\text{week}}, \text{user\_config})$).
- **`PerformanceMarginCalculator` (`src/promotion/performance_margin_calculator.py`):** Continuously calculates required graduation margins $\delta^* \in [3.0\%, 25.0\%]$ using empirical childhood speed and occupancy telemetry from `synapse_fluid_dynamics`.

---

## 9. Physical Reward Balancing Subsystem (`src/engine/reward_weights_calculator.py`)

To eliminate gradient distortion where cumulative waiting times dwarf vehicle throughput by orders of magnitude, CARINA balances the reward equation according to Highway Capacity Manual (HCM) link traversal physics:

$$\tau = \frac{\bar{L}_{\text{links}}}{\bar{v}_{\text{limit}}}$$
$$w_{\text{wait}} = -1.0, \quad w_{\text{flow}} = \text{clamp}(2.0, 25.0, \text{round}(\tau \times \alpha, 2))$$

- **`RewardWeightsCalculator` (`src/engine/reward_weights_calculator.py`):** Computes normalized reward weights upon network topology loading (`TopologyManager.load_topology`).
- **`RewardCalculator` (`src/engine/reward_calculator.py`):** Ingests dynamic weights via `set_reward_weights`, establishing an equilibrium where vehicle discharge incentives match the scale of accumulated queue delay.

---

## 10. Nighttime Yellow Flashing Schedule Subsystem (`src/controller/yellow_schedule_manager.py`)

For traffic safety and legal compliance during low-volume overnight hours, CARINA integrates an autonomous flashing yellow schedule subsystem:
- **`YellowScheduleManager` (`src/controller/yellow_schedule_manager.py`):** Evaluates scheduled time windows (e.g., 23:00 to 05:00) against current system time, autonomously commanding physical controllers into flashing yellow mode or transitioning back to adaptive AI control at window boundaries.
- **`YellowScheduleCard` (`ui/cards/yellow_schedule_card.py`):** UI interface enabling operators to enable/disable schedules, customize time ranges, and selectively assign individual intersections or entire metropolitan networks.

## 11. Emergency Vehicle Preemption (EVP) Subsystem (`src/evp/`, `src_go/evp_go/`)

To grant instantaneous Green Corridors for emergency response vehicles (SAMU, Fire Department, Police) in compliance with Brazilian CONTRAN Resolution nº 960 and CTB Art. 29, CARINA incorporates a dedicated Emergency Vehicle Preemption subsystem:

```text
 GPS Antenna / Beacon       Go Web Gateway (:2201 / :8085)        EVPService (src/evp/)
          │                             │                                   │
          │── POST /api/v1/evp/telemetry ─>│                                   │
          │   (HTTP 204 No Content)     │── NDJSON / In-Memory Stream ─────>│
          │                             │                                   ├── Kinematics (Haversine WGS84)
          │                             │                                   ├── Block Entry (60m <= d <= 160m)
          │                             │                                   └── Siren Active Verification
          │                             │                                           │
          │                             │                                           ▼
          │                             │                                 SafetyAuditor (Rule #0)
          │                             │                                 (Clearance -> ACTION_HOLD)
          │                             │                                           │
          │<───── Green Corridor ───────┼── SNMP ascPhaseHold (Go Dispatcher) <─────┘
```

- **Two-Factor Trigger:** Preemption requires simultaneous approach block entry ($60\text{ m} \le d \le 160\text{ m}$) AND active siren (`siren_active = True`).
- **SafetyAuditor Priority Intercept:** Rule #0 intercepts proposed actions, respects clearance intervals (yellow and all-red), and holds green (`ACTION_HOLD = 1`).
- **CONTRAN Watchdog Limit ($45\text{ s}$):** Aborts holds unconditionally after 45 seconds to prevent cross-arterial gridlock.
- **Immediate Checkout:** As soon as the vehicle crosses the stop line ($d \le 15\text{ m}$), preemption is released immediately.

For full technical specifications, see [Emergency Vehicle Preemption (EVP)](EVP_AND_PREEMPTION.md).

---

## 12. Central Control Operator (CCO) Web Architecture (`src_go/web_gateway/`, `src_tsx/src_cco/`)

CARINA provides a web-based operations center for municipal videowalls and remote monitoring:
- **`WebGatewayServer` (`src_go/web_gateway/server.go`):** Embedded Go HTTP server running on port 2201 (or configured port) providing SSE event streaming (`/cco/stream`), topology endpoints (`/cco/topology`), and Tailscale Funnel encrypted remote tunneling.
- **`CCO Web Application` (`src_tsx/src_cco/`):** Modern React 18, TypeScript, Tailwind CSS, SVG map layer renderer, and Apache ECharts dashboard displaying real-time vehicle positions, signal timings, and preemption alert toasts.

---

<div align="center">
  <img src="assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Controlled Artificial Road-traffic Intelligence Network Architecture • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licenciado sob AGPLv3 ou posterior (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
