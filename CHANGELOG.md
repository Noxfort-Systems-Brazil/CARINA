# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
