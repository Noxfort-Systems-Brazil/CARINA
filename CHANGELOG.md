# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Single-Owner Go Gateway & Closed-Loop Hardware Telemetry (`CARINA_GATEWAY_ROLE`)**: Assigned exclusive `bin/carina-go` ownership to `CentralController` (`CARINA_GATEWAY_ROLE=owner`) via `HardwareGatewayCoordinator` (`GatewayRuntimeWorker`, `HardwareCommandService`, `FenixStageDispatcher`, `TailscaleGatewayAdapter`), while `AI_Process`, `SDS`, and `UI` run as `remote` processes using `RemoteHardwareDriverProxy`, `sync_remote_driver_proxies`, `ThreadSafePipeConnection`, and `HardwareTelemetrySynchronizer` / `HardwareTelemetryDecoder`.
- **SNMPv3 USM, Per-Intersection OID Overrides & Binary SNMP Trap Decoder**: Added full SNMPv3 (`NoAuthNoPriv`, `AuthNoPriv`, `AuthPriv` with SHA-256/512 and AES-128/192/256) in `src_go/pkg/snmp/config.go` and `hardware_controller_connections.snmp_config`, per-intersection `config_path` propagation, `GetBitmask` PDU codec (`src_go/pkg/snmp/codec.go`), `src_go/pkg/traplistener/snmp_decoder.go` for binary SNMPv1/v2c/v3 Trap/Inform PDUs, and `resume_control` / `gateway_set_auth_tokens` NDJSON gateway commands.
- **Calibrated QR-D3QN Guardian Safety & `CHILD` Shadow Training (`src/safety/`)**: Implemented `GuardianPhysicsEstimator` (capacity-normalized incoming-edge slicing & clearance horizon projection), `GuardianRiskCalibrator` ($F_2$-tuned quantile spread calibration & non-compensatory Noisy-OR fusion), `GuardianShadowTrainer` (off-policy training restricted strictly to `Maturity.CHILD` followed by `freeze_for_deployment()`), and atomic `GuardianCheckpointService` (`guardian_{tl_id}.pth`).
- **Phase 1–4 Performance & Memory Optimizations**:
  - *Neural Hot-Path:* `BatchedPAEEncoder`, `FleetBatchInferencer` (`torch.func.stack_module_state` + `torch.vmap` + packed CPU decision arrays), `PhysicalActionMasker`, pure-NumPy host GAE in `PPOOptimizer`, and host-RAM `ReplayMemory` / `StateReplayMemory` (`push_batch`, $O(1)$ `_max_priority` cache).
  - *Database & IPC:* `PostgresConnectionPool` (`ThreadedConnectionPool`), SQLite WAL & pragmas (`configure_sqlite_connection`), `db_transaction`, `enable_step_worker=False` for read-only workers, 168-hour `evp_telemetry_records` auto-purge, and 1 Hz rotating `HFTDiagnostics`.
  - *SLM, XAI & Rendering:* Cross-process `slm_process_lock` (`slm_gguf.lock`), `pynvml` VRAM detection without PyTorch CUDA context bloat, `XaiWorker` Captum analysis cache reuse, `src/rendering/mpl_utils.py` offscreen Matplotlib rendering, and `read_sumo_net_cached` LRU cache.
  - *UI & CCO:* `MapAnimator` hidden-window pause & dirty-flag throttling, paginated `AuditLogWidget` (<= 100 rows), `RemoteGatewaySettingsPersister`, `WebSocketServer` backpressure, and React CCO compositor-only animations (`transform`/`opacity`) + `requestAnimationFrame` viewport refs.
- **Memory-Guarded Test Infrastructure**: Added `scripts/pytest_limited.sh` (systemd cgroup v2 `MemoryHigh=1536M` / `MemoryMax=2048M` / `MemorySwapMax=512M` or `ulimit -d`) and `tests/memory_guard.py` (`reclaim_test_resources()`), expanding the suite to **967 collected Pytest tests** (**935 unit**, **18 integration**, **14 root**) and **46 Go unit tests**.

### Security
- **gRPC Transport Security (`src/communication/grpc_security.py`)**: Added optional TLS/mTLS (`CARINA_GRPC_TLS_ENABLED`, `CARINA_GRPC_REQUIRE_CLIENT_CERT`) and `BearerTokenServerInterceptor` (`CARINA_GRPC_AUTH_TOKEN`) on `:50051`.
- **Fail-Closed Web Gateway, Token Auth & Certificate Pinning**: Changed `gateway_enabled` default to `False` (returning `503 Service Unavailable` when disabled), enforced constant-time token checks (`CARINA_EVP_AUTH_TOKEN`, `CARINA_CCO_AUTH_TOKEN`) in `src_go/web_gateway/auth.go` and `evp_http_server.go`, added explicit CORS (`CARINA_CCO_ALLOWED_ORIGIN`), Gateway HTTPS/TLS, and SHA-256 leaf pinning in `CCOBroadcastClient` (`PinnedHTTPSConnection`).
- **Parameterized PostgreSQL Intervals**: Replaced `%s` string interpolation inside PostgreSQL `INTERVAL` literals with `make_interval(...)` in `config/database/fluid_dynamics_queries.json`.

### Changed
- **Corrected NTCIP 1202 & UTMC2 OID Profiles (`src_go/configs/`)**: Aligned `ntcip_oids.json` with standard NTCIP 1202 ASC MIBs (`.4.1.2/3/4/8/9.1` telemetry and `.5.1.2/4/5/6/7.1` control) and added UTMC2 `demand` OID (`1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1`).
- **Unified TCN & Action-Conditioned iTransformer PAE (`src/models/`)**: Replaced deprecated `weight_norm` with `TemporalConv1d` + `GroupNorm(1, C)` + `SiLU` + `TemporalAttentionPool`, upgraded `PredictiveAutoencoder` to an action-conditioned iTransformer with `key_padding_mask` and `decode_with_uncertainty`, and added auxiliary prediction + CTDE value heads to `STGATv2Lite`.
- **SOLID Refactoring (`src/launcher/`, `src/controller/`, `src/drivers/`, `src/repositories/`, `src/interfaces/`)**: Modularized `process_manager.py`, `connection_operation_handler.py`, `traffic_frame_processor.py`, `connection_config_repo.py`, `agent_evaluator.py`, and `local_agent.py` into focused SRP collaborators with segregated protocols in `src/interfaces/`.
- **Unconsumed Consultant Agent (`src/agents/consultant_agent.py`)**: Removed obsolete background mentor agent whose cache was never consumed by decision or safety layers. The underlying `PredictiveAutoencoder` (`src/models/pae.py`) remains active as a direct physical representation model.
- **Dead Cross-Attention Module (`src/models/cross_attention.py`)**: Removed dead cross-attention module; neural fusion is performed via direct spatiotemporal tensor concatenation and TCN/MLP processing.
- **Consolidation into Canonical 3-Agent Architecture**: Streamlined the multi-agent hierarchy into three clear, orthogonal roles:
  1. `LocalAgent` (Tactical PPO-TCN, sub-second execution at each junction)
  2. `GuardianAgent` (Safety QR-D3QN + CTB symbolic safety vetoes)
  3. `StrategistAgent` (Spatiotemporal network coordination via ST-GATv2 Lite running every 5s)
- **Decoupled Strategic Coordinator (`src/engine/strategic_coordinator.py`)**: Preserved graph telemetry aggregation, non-mutating `peek_state()` sampling, and online self-supervised/CTDE updates.
- **Documentation & Report Harmonization**: Updated root and multilingual documentation (PT-BR, EN, ES, FR, RU, ZH), architecture specs, OID tables, security guides, and testing documentation.

---

## [1.2.0] - 2026-09-25

### Added
- **Native Go Hardware Gateway (`src_go/` & `bin/carina-go`)**: Ultra-high-performance, compiled Go field micro-daemon handling real-world traffic signal controller communication (UDP 161 and 162). Transcribes NTCIP 1202 and UTMC2 protocols from Python to Go with sub-millisecond determinism, zero GIL contention, and minimal memory footprint (~3.5 MB static binary, `CGO_ENABLED=0`).
- **Autonomous JSON OID Engine (`src_go/configs/` & `//go:embed`)**: Fully dynamic, configuration-driven OID mappings for NTCIP 1202 and UTMC2 loaded from JSON with embedded defaults, decoupling hardware variations from compiled code.
- **Zero-Port Anonymous Pipe IPC (`src/drivers/go_gateway_client.py`)**: Communication between CARINA Python core and the Go Gateway runs strictly through standard OS pipes (`stdin`/`stdout`) via Line-Delimited JSON (NDJSON), opening zero host network ports and eliminating firewall/port collision risks.
- **Atomic Safety Fail-Safe**: Immediate kernel-level fail-safe on `EOF` or `SIGPIPE`—if the Python AI process closes or encounters a fatal crash, the Go Gateway detects the closed pipe in microseconds and dispatches an emergency `release_control` via SNMP, restoring physical cabinets to their local fixed-time plans.
- **Concurrent Keepalive & Trap Engine (`src_go/pkg/heartbeat/` & `traplistener/`)**: Microsecond-resolution ticker goroutines for 2.0s keepalive heartbeats per intersection and asynchronous UDP 162 trap decoding with automatic push dispatch to CARINA's `IncidentReporter`, `IncidentFilter`, and UI layers.
- **Python Liskov Adapter (`src/drivers/go_driver_proxy.py` & `driver_factory.py`)**: Drop-in `BaseTrafficDriver` proxy seamlessly integrated into `DriverFactory` and `HardwareConnectionManager`, with zero breaking changes for `ActionSupervisor`, `StepProcessor`, or UI components.
- **F.E.N.I.X. Process Supervisor & Self-Healing (`src/fenix/`)**: Complete crash recovery and high-availability subsystem. Features `FenixSupervisor` facade, `WindowedCrashRecoveryPolicy` with exponential backoff and crash rate limiting, `SubprocessRunner` with clean signal management, and `StateReconciler` with zero-collision stage boundary handover.
- **Watchdog F.E.N.I.X. Integration (`src/watchdog/watchdog_logic.py`)**: Automatic trigger of F.E.N.I.X. resurrection (`on_fenix_trigger`) when process heartbeat failure is detected.
- **Unit Test Suite Expansion (`tests/unit/`)**: Expanded test suite to 53 isolated test modules, adding comprehensive coverage for FENIX supervisor, process runner, recovery policy, state reconciler, Go gateway bridge, and Watchdog integration.

---

## [1.1.0] - 2026-09-15

### Added
- **Modular Settings Architecture (`src/settings/`)**: Fully decoupled configuration system conforming to SOLID principles. Features `ISettingsReader`, `ISettingsWriter`, `ISettingsStorage`, and `IEnvironmentProvider` interfaces, typed schema validation via `SettingsSchema`, INI file persistence via `IniFileStorage`, and 12-Factor `.env` secret resolution via `DotenvSecretProvider`, with backwards-compatible `SettingsManager` facade.
- **Polymorphic Monitoring & Telemetry Transports (`src/transports/`)**: Flexible Strategy & Factory transport architecture (`BaseMonitorTransport`, `MonitorHttpTransport`, `MonitorMqttTransport`, `create_monitor_transport`). Supports both local/network MQTT brokers and remote HTTP/HTTPS cloud endpoints (REST APIs, Webhooks, Ngrok tunnels) with automated URL/IP classification.
- **Hardware Incident Reporting & Filtering (`src/drivers/incident_reporter.py` & `incident_filter.py`)**: Asynchronous incident publisher capturing controller disconnects, failsafes, and status transitions with hash-based caching and debounce deduplication.
- **Native System Tray Integration (`ui/handlers/tray_handler.py`)**: Multi-backend tray support (AyatanaAppIndicator and X11) powered by `pystray` and `Pillow`, featuring window minimization to tray and context menus.

### Changed
- **Dependencies Update (`requirements.txt` & `pyproject.toml`)**:
  - Added missing `python-dotenv>=1.0.0` for 12-Factor environment secrets.
  - Added `Pillow>=10.0.0` for desktop system tray icon processing.
  - Upgraded `pysnmp` from deprecated `>=5.0.0` to modern LeXtudio `>=7.0.0` for Python 3.12 compatibility.
  - Documented `pynvml>=11.5.0` for optional GPU/VRAM hardware metrics.
- **Comprehensive Documentation Sync**: Updated `README.md`, `ARCHITECTURE.md`, `CARINA_MOC.md`, `API_REFERENCE.md`, `DEVELOPER_GUIDES.md`, `HARDWARE_DRIVERS.md`, `SECURITY_AND_AUTH.md`, and `TESTING.md` to reflect new modular subsystems, transport protocols, and 45 unit tests.

---

## [1.0.0] - 2026-08-13

### Added
- **ST-GATv2 Lite Module (`st_gatv2_lite.py`)**: Spatiotemporal Graph Attention Network coordinating Green Waves across physical urban graph topologies.
- **Global Consultant Agent (`consultant_agent.py`)**: Event-triggered background mentor running a high-capacity Predictive Autoencoder (PAE 64/128 channels) for future horizon projection ($t + \Delta t$).
- **Topological Scaler (`topo_scaler.py`)**: $O(1)$ algorithmic auto-scaling of latent dimensions (32, 64, 128, 256) and attention heads (2, 4, 8, 16) based on city network node count $N$.
- **Dual Cross-Attention Mode (`cross_attention.py`)**: Adaptive PBT (Population-Based Training) temperature evolution for LocalAgent PPO vs Fixed Deterministic weights for GuardianAgent D3QN safety audits.
- **Universal AMP & TensorCores Acceleration**: Wrapped all deep neural network inference loops with `torch.amp.autocast(FP16)` reducing VRAM consumption to ~20 MB.
- **5 Formal Neural Equations in ABNT Report**: Rendered TCN Causal Convolution, ST-GATv2 Lite Attention, Cross-Attention Transformer, Guardian Dueling D3QN, and Captum Integrated Gradients equations natively in `xai.docx`.
- **Guardian Agent Safety Veto Audit Table**: Real-time audit metrics (Total Evaluated, Approved, Vetoed, Compliance Rate %, Top Veto Reasons) queried from PostgreSQL for Section 4 and Anexo I.
- **PostgreSQL Async Delta Storage Engine (`step_decision_worker.py` & `step_decision_repo.py`)**: Non-blocking RAM push (< 0.001 ms) with 1-byte Smallint Enums, Edge Dictionary mapping, and Run-Length Encoding achieving **97.9% global database storage reduction** (~380 MB/day for 200 intersections).

### Changed
- Replaced legacy `gatv2_lite.py` with `st_gatv2_lite.py`.
- Updated `xai_report_templates.json` across 6 languages (`pt_br`, `en`, `es`, `fr`, `de`, `zh`).
- Silenced PyTorch tensor conversion warning via native C-contiguous `numpy.array` array wrappers.

---

## [0.9.0] - 2026-08-12

### Added
- **Ultimate Documentation Overhaul**: Complete rewrite of `README.md`, `ARCHITECTURE.md`, and creation of a multi-document library in `docs/`.
- **Explainable AI Integration**: Qwen3 1.7B LLM backend generating natural language Laudos Técnicos via Captum tensors.
- **Smart Dashboard Service (SDS)**: Flet UI decoupled from AI Engine using WebSocket aggregation.
- **Synapse HFT Protocol**: gRPC infrastructure implemented for sub-millisecond physical controller communication.
- **DA SILVA Curriculum**: Automated Policy Entropy validation for agent maturation from CHILD to ADULT.

### Changed
- Refactored `EpisodeRunner` to run asynchronously across isolated `multiprocessing` Queues.
- Switched default Recurrent Neural Network backbone from LSTM to TCN (Temporal Convolutional Networks) for massive parallel inference.

### Security
- Implemented deterministic `GuardianAgent` with hardcoded Symbolic Vetoes to override catastrophic neural hallucinations.
