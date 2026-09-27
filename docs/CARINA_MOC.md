---
tags: [moc, hub, docs, obsidian, carina, index]
aliases: [CARINA MOC, Master Documentation Hub, Documentation Index, Knowledge Vault]
---

# 📚 CARINA Technical Master Documentation Hub

Welcome to the **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture) technical documentation library. Designed as a massively concurrent, high-frequency Deep Reinforcement Learning ecosystem for real-time traffic light control, CARINA bridges high-level neuro-symbolic AI, real-time gRPC hardware actuation, and multi-process OS isolation.

This master documentation index provides deep technical coverage for core developers, academic researchers, municipal traffic engineers, and system integrators. It is fully compatible with both **GitHub** and **[Obsidian](https://obsidian.md/)**.

---

## 🗺️ Codebase Map & Directory Hierarchy

```text
CARINA_CORE/
├── carina.py                   # Master Orchestrator (SingleInstanceLock, ProcessManager, UI/Tray)
├── ARCHITECTURE.md             # 8-Process Multiprocessing Blueprint & IPC Topology
├── pyproject.toml              # Build toolchain & project metadata
├── requirements.txt            # Python runtime dependencies
├── .env.example                # 12-Factor App environment variables & credentials
│
├── config/                     # Configuration Systems
│   ├── settings.ini            # System-wide parameters (AI, PBT, Watchdog, MFD, Logging)
│   ├── database/               # Dynamic SQL queries & schemas (schema_queries.json, fluid_dynamics_queries.json)
│   ├── rules/                  # Safety and semantic consistency rules (safety_rules.json, semantic_rules.json)
│   └── templates/              # Multi-language report, MFD, SAS & XAI templates
│
├── proto/                      # gRPC Protocol Specifications
│   └── synapse_hft.proto       # High-Frequency Telemetry & Actuation Protobuf Definitions
│
├── docs/                       # Comprehensive Knowledge Vault
│   ├── CARINA_MOC.md           # Master Documentation Hub (This File)
│   ├── index.md                # MkDocs Entry Point & Portal
│   ├── API_REFERENCE.md        # Synapse HFT gRPC Protocol & IPC Queue Schemas
│   ├── RESEARCH_NOTES.md       # PPO-TCN, PAE, GATv2 & DA SILVA Mathematical Formulations
│   ├── HARDWARE_DRIVERS.md     # Physical Controllers: NTCIP 1202, UTMC2 & SNMP Integration
│   ├── SAFETY_AND_WATCHDOG.md  # Guardian Safety Firewall, Veto Rules & Watchdog
│   ├── TRAFFIC_ENGINEERING_WARRANTS.md # MUTCD / FHWA Traffic Signal Warrants 1, 2, 3, 7, 8
│   ├── MFD_AND_ANALYTICS.md    # Macroscopic Fundamental Diagram & Network Density Dynamics
│   ├── DATABASE_AND_SCHEMAS.md # Persistence Tier, Async Delta Storage & SQL Schemas
│   ├── XAI_AND_SAS.md          # Explainable AI, Captum Integrated Gradients & SAS Analytics
│   ├── REPORT_BLOCKS_AND_TEMPLATES.md # Modular ABNT Word (.docx) & OMML Math Equations
│   ├── SLM_AND_LOCAL_LLM.md    # Local Offline LLM Integration (Qwen3 1.7B / llama.cpp)
│   ├── UI_AND_DASHBOARD.md     # Flet Desktop Application, Planning View & SDS Architecture
│   ├── RENDERING_AND_HEATMAPS.md # Vector Map Rendering & Asynchronous Heatmap Interpolation
│   ├── SECURITY_AND_AUTH.md    # User Accounts, Salted Bcrypt Hashing & Brute-Force Lockdown
│   ├── DEVELOPER_GUIDES.md     # Environment Setup, Agent Hierarchy, Settings & Packaging
│   ├── TESTING.md              # Pytest Test Suite, Driver Mocks & Coverage Validation
│   └── DEPLOYMENT_AND_PACKAGING.md # Docker Builds, Systemd Daemons & Debian Packages
│
├── bin/                        # Compiled native binaries (carina-go)
├── src_go/                     # Go Hardware Gateway (NTCIP 1202, UTMC2, UDP 161/162)
│   ├── cmd/gateway/            # Gateway entrypoint & NDJSON stdin/stdout IPC loop
│   ├── configs/                # Embedded NTCIP & UTMC OID JSON profiles
│   └── pkg/                    # snmp, ntcip, utmc, discovery, heartbeat, traplistener, manager
├── src/                        # Primary Source Code
│   ├── agents/                 # PPO LocalAgent, GuardianAgent, ConsultantAgent & StrategistAgent
│   ├── analysis/               # MUTCD WarrantEvaluator, WarrantMath & Traffic Analysis
│   ├── blocks/                 # Modular .docx builder, OMML math converters & text cleaners
│   ├── central_controller.py   # High-Frequency gRPC Telemetry Server
│   ├── communication/          # MonitorClient, HFT server & external telemetry bridging
│   ├── controller/             # ConnectionManager, FailSafeManager, StageValidator & Overrides
│   ├── core/                   # DecisionCoordinator, SafetyAuditor, MaturityManager & ActionAuthorizer
│   ├── database/               # DatabaseEngine, DatabaseWorker & StepDecisionWorker
│   ├── drivers/                # Go Gateway Python Proxy, DriverFactory, IncidentReporter & IncidentFilter
│   ├── engine/                 # EpisodeRunner, StepProcessor, PPO/DQN Optimizers & Trainers
│   ├── fenix/                  # F.E.N.I.X. Self-Healing & Process Supervisor (Supervisor, Runner, Reconciler)
│   ├── handlers/               # AI requests, UI commands & watchdog command handlers
│   ├── launcher/               # ProcessManager, SingleInstanceLock & UITrayManager
│   ├── mfd/                    # Macroscopic Fundamental Diagram (MFD) Analyzer & Worker
│   ├── models/                 # Neural Architectures (PAE, TCN, ST-GATv2 Lite, CrossAttention)
│   ├── rendering/              # StaticMapRenderer & AsyncHeatmapRenderer
│   ├── repositories/           # StepDecisionRepo, FluidDynamicsRepo & CloudVaultRepo
│   ├── safety/                 # GuardianWorker process & IPC signal routing
│   ├── sas/                    # Smart Analysis System (Offline Infrastructure Warrants)
│   ├── sds/                    # Smart Dashboard Service (Flet UI bridge & WebSockets)
│   ├── settings/               # Modular Settings (SOLID interfaces, schemas, INI & .env)
│   ├── slm/                    # Small Language Model (Qwen3 / llama.cpp offline inference)
│   ├── transports/             # Polymorphic transports (Base, HTTP, MQTT, EndpointResolver)
│   ├── utils/                  # SettingsManager, MetricsManager, Paths & Security Subsystem
│   │   └── security/           # AuthService, UserService, Bcrypt Hasher & LockdownManager
│   ├── watchdog/               # Real-time process heartbeat monitor & fail-safe fallback
│   └── xai/                    # Integrated Gradients attribution, report builder & worker
│
├── ui/                         # Native Flet Desktop Application
│   ├── cards/                  # Modular settings & telemetry cards (MonitorSettingsCard)
│   ├── handlers/               # Event handlers, SettingsHandler & native SystemTrayHandler
│   ├── views/                  # DashboardView, PlanningView, DiagnosticsView, SettingsView
│   ├── widgets/                # LiveCanvasMapWidget, PlanningControlPanel, MFDViewer, XAIViewer
│   ├── renderers/              # PlanningMapRenderer, MapVisualSyncer, MapDrawer
│   ├── animators/              # MapAnimator & transition controllers
│   └── locales/                # Multi-language JSON dictionaries (pt_br, en_us, es_es, etc.)
│
└── tests/                      # Pytest Test Suite (Unit, Integration & Hardware Mocks)
```

---

## 📖 System Dimensions & Knowledge Vault Navigation

### 1. Core Infrastructure & Hardware Drivers
- **[Architecture Deep-Dive](../ARCHITECTURE.md)**: Exhaustive technical blueprint detailing all 8 concurrent OS microservices, process isolation via `multiprocessing`, IPC Pipe/Queue channels, and the execution loop.
- **[Hardware Drivers & Physical Controllers](HARDWARE_DRIVERS.md)**: Specifications for compiled Go Hardware Gateway (`carina-go`), NDJSON standard pipes IPC, NTCIP 1202 (ASC), UTMC / UTMC2 UK standard, SNMP v2c/v3 client, connection pooling, and deterministic hardware fail-safe reversion.
- **[API Reference & HFT Protocol](API_REFERENCE.md)**: Complete specifications for the `Synapse HFT` gRPC interface, external Monitor telemetry (MQTT/HTTP), Prometheus metric endpoints (port 8001), and IPC queue schemas.
- **[Database Architecture & Schemas](DATABASE_AND_SCHEMAS.md)**: Specifications for `DatabaseWorker`, `StepDecisionWorker`, connection pooling, 12-Factor `.env` setup, and PostgreSQL delta storage (97.9% reduction).
- **[Security & Authentication](SECURITY_AND_AUTH.md)**: User account management, salted `bcrypt` hashing, brute-force lockdown defense, and role-based access control.
- **[Modular Settings Architecture](../ARCHITECTURE.md#4-modular-settings-architecture-srcsettings)**: SOLID configuration subsystem decoupling schemas, INI persistence, and 12-Factor `.env` secrets.
- **[Polymorphic Monitoring & Transports](../ARCHITECTURE.md#5-polymorphic-monitoring--transport-architecture-srctransports)**: Telemetry and incident streaming over MQTT brokers and HTTP/HTTPS REST/Ngrok cloud endpoints.

### 2. Artificial Intelligence & Neuro-Symbolic Safety
- **[Neural Research & Formulations](RESEARCH_NOTES.md)**: Deep mathematical formulations for PPO-TCN, Predictive Autoencoder (PAE) latent projection $Z$, Dueling DQN-TCN value/advantage streams, ST-GATv2 Lite Graph Attention, and the DA SILVA maturation curriculum.
- **[Safety Architecture, Watchdog & F.E.N.I.X.](SAFETY_AND_WATCHDOG.md)**: Inventory of Symbolic Veto rules (SR-01 to SR-05), PAE Neural Veto thresholds, real-time Watchdog heartbeat monitoring (< 500 ms), and F.E.N.I.X. autonomous process resurrection with clean boundary state reconciliation.
- **[Explainable AI, SAS & MFD Analytics](XAI_AND_SAS.md)**: Operational details of the modular XAI pipeline, Captum Integrated Gradients attribution, and municipal forensic audits.
- **[Report Blocks Engine & Word Generator](REPORT_BLOCKS_AND_TEMPLATES.md)**: Automated generation of ABNT NBR 14724 Word (`.docx`) reports with native Office Math Markup Language (OMML) LaTeX formulas.
- **[Small Language Models (SLM)](SLM_AND_LOCAL_LLM.md)**: Local, 100% offline LLM inference (Qwen3 1.7B / llama.cpp) generating forensic textual explanations without cloud dependencies.

### 3. Traffic Physics, Warrants & Graphics
- **[Traffic Engineering Signal Warrants](TRAFFIC_ENGINEERING_WARRANTS.md)**: Automated evaluation of formal MUTCD / FHWA signal warrants (Warrants 1, 2, 3, 7, 8) and infrastructure warrants.
- **[Macroscopic Fundamental Diagram & Dynamics](MFD_AND_ANALYTICS.md)**: Network-wide flow-density physics, critical density ($K_{crit}$), perimeter gating, capacity drop detection, and incident filter caching.
- **[Map Rendering & Heatmaps](RENDERING_AND_HEATMAPS.md)**: Offline vector map parsing from SUMO `.net.xml` networks and asynchronous Kernel Density Estimation (KDE) heatmaps.

### 4. Desktop Frontend & Operations
- **[UI & Smart Dashboard Service](UI_AND_DASHBOARD.md)**: Architectural breakdown of the native Flet desktop UI, Planning View, single-instance socket locking (port 42123), and WebSocket telemetry streaming.
- **[Developer & Integration Guides](DEVELOPER_GUIDES.md)**: Guide for setting up environments, modifying configurations, extending agents, and building packages.
- **[Testing & Validation](TESTING.md)**: Guidelines for running `pytest`, generating coverage reports (`--cov=src`), mocking controllers, and validating Guardian safety vetoes.
- **[Deployment, Packaging & Containerization](DEPLOYMENT_AND_PACKAGING.md)**: Guide for Docker containerization (`Dockerfile`), Systemd service units, and Debian `.deb` packages.

---

> 💡 **Obsidian Knowledge Graph:** This documentation suite maintains full native support for [Obsidian](https://obsidian.md/). Open the `CARINA_CORE` repository folder as an Obsidian Vault to navigate the interactive technical graph and backlinks.
