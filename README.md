<div align="center">

<img src="docs/assets/carina-logo.png" alt="CARINA CORE Logo" width="130" />

# CARINA CORE
### Controlled Artificial Road-traffic Intelligence Network Architecture
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](LICENSE)

[![CARINA GitHub Repository Card](https://github-readme-stats.vercel.app/api/pin/?username=Noxfort-Systems-Brazil&repo=CARINA&theme=dark)](https://github.com/Noxfort-Systems-Brazil/CARINA)

---

🌐 **Translations / Idiomas:** **[🇺🇸 English](README.md)** • **[🇧🇷 Português do Brasil](docs/pt-br/README.md)** • **[🇪🇸 Español](docs/es/README.md)** • **[🇫🇷 Français](docs/fr/README.md)** • **[🇷🇺 Русский](docs/ru/README.md)** • **[🇨🇳 简体中文](docs/zh/README.md)** • **[📚 Documentation Hub](docs/README.md)**

---

</div>

**CARINA** is a massively distributed Deep Reinforcement Learning ecosystem designed for real-time traffic control and smart city orchestration. Bypassing Python's Global Interpreter Lock (GIL) via 8 concurrent OS processes, it integrates a Tactical PPO agent, an ST-GATv2 Lite Graph Coordinator (Strategist Agent), a shared Predictive Autoencoder (PAE), and a Guardian Agent (D3QN) to provide 100% ABNT-compliant forensic auditability and neuro-symbolic safety.

---

## 📚 Documentation Hub & Knowledge Vault

Explore the full architecture, internal mechanics, and developer guides for the CARINA ecosystem:

| Card / Subsystem | Focus Area | Direct Link |
| :--- | :--- | :---: |
| 📚 **Documentation Hub** | Central Index & Navigation for all technical docs | [Explore Hub](docs/CARINA_MOC.md) |
| 🏛️ **Core Architecture** | 8 Concurrent OS microservices, ST-GATv2 Lite & Universal PAE | [View Blueprint](ARCHITECTURE.md) |
| ⚡ **Synapse HFT API** | Sub-millisecond gRPC telemetry & Protobuf IPC specifications | [View API Reference](docs/API_REFERENCE.md) |
| 🧠 **Neural Formulations** | PPO-TCN, ST-GATv2 Lite & Predictive Autoencoder (PAE) | [View Research](docs/RESEARCH_NOTES.md) |
| 🚦 **Hardware Drivers** | Physical controllers (NTCIP 1202, UTMC2, SNMP Client & Traps) | [View Drivers](docs/HARDWARE_DRIVERS.md) |
| 🛡️ **Safety Firewall & Watchdog** | Guardian D3QN Vetoes, Symbolic rules & Watchdog | [View Safety Guide](docs/SAFETY_AND_WATCHDOG.md) |
| 🚑 **Emergency Preemption (EVP)** | Autonomous green corridors, kinematics gates & Web Gateway | [View EVP Guide](docs/EVP_AND_PREEMPTION.md) |
| 📊 **Engineering Warrants** | MUTCD / FHWA Traffic Signal Warrants 1, 2, 3, 4 | [View Warrants](docs/TRAFFIC_ENGINEERING_WARRANTS.md) |
| 📈 **MFD & Traffic Analytics** | Network density-flow curves, capacity drop & gating | [View MFD Guide](docs/MFD_AND_ANALYTICS.md) |
| 🗄️ **Database & Schemas** | PostgreSQL Delta Storage (97.9% reduction), 12-Factor Setup | [View DB Specs](docs/DATABASE_AND_SCHEMAS.md) |
| 🔍 **Explainable AI (XAI)** | Captum Integrated Gradients, 5 Formal Equations & Audits | [View XAI & SAS](docs/XAI_AND_SAS.md) |
| 📄 **Report Blocks Engine** | ABNT NBR 14724 Word (.docx) Builder & OMML Math Equations | [View Reports](docs/REPORT_BLOCKS_AND_TEMPLATES.md) |
| 🤖 **Small Language Models** | Local Qwen3.5 2B / llama.cpp Offline Textual Justification | [View SLM Guide](docs/SLM_AND_LOCAL_LLM.md) |
| 🖥️ **UI, CCO & Dashboard** | Native Flet desktop app, React 18 CCO Videowall & Mobile | [View UI Guide](docs/UI_AND_DASHBOARD.md) |
| 🗺️ **Rendering & Heatmaps** | Vector Map Rendering & Asynchronous Heatmap Interpolation | [View Rendering](docs/RENDERING_AND_HEATMAPS.md) |
| 🔐 **Security & Auth** | User accounts, salted PBKDF2 hashing & brute-force lockdown | [View Security](docs/SECURITY_AND_AUTH.md) |
| 🛠️ **Developer Guides** | Agent development, settings configuration & setup | [View Guides](docs/DEVELOPER_GUIDES.md) |
| 🧪 **Testing & Validation** | Pytest suite (967 tests, cgroup/RSS memory guard) & Go tests (`go test`) | [View Guidelines](docs/TESTING.md) |
| 🚀 **Deployment & Packaging** | Docker containerization & Systemd service daemons | [View Deployment](docs/DEPLOYMENT_AND_PACKAGING.md) |

---

## ⚡ Core Architecture (GOMES & DA SILVA)

- **Tactical Layer (PPO-TCN Edge AI):** Hyper-focused on local intersection throughput with sub-millisecond ($< 0.5\text{ ms}$) execution, unified causal `TemporalConv1d` + `TemporalAttentionPool`, physical logit action masking (`PhysicalActionMasker`), and vectorized multi-intersection `torch.vmap` batch inference (`FleetBatchInferencer`).
- **Strategic Layer (ST-GATv2 Lite):** Dynamic spatiotemporal graph attention coordinating Green Waves across urban avenues with online next-step prediction and CTDE cooperative value estimation (`StrategicCoordinator`).
- **Predictive Layer (Universal Action-Conditioned iTransformer PAE):** Shared world model with per-variable RevIN, `key_padding_mask` over variable lengths, binary action conditioning, and heteroscedastic uncertainty (`decode_with_uncertainty`) projecting future spatiotemporal states ($t + \Delta t$).
- **Guardian Layer (Calibrated QR-D3QN + Noisy-OR Safety Firewall):** Distributional 32-quantile Dueling Double DQN (`CVaR_0.20`) paired with capacity-normalized kinematic spillback estimation, `CHILD`-only off-policy shadow training (`GuardianShadowTrainer`), $F_2$-tuned quantile calibration, non-compensatory Noisy-OR risk fusion (`GuardianRiskCalibrator`), and immutable deployment freezing (`freeze_for_deployment`).
- **Explainable AI (XAI Engine):** Google Captum Integrated Gradients (with frozen parameter grads and cached multi-agent analysis) exporting ABNT NBR 14724 reports with 5 formal neural equations and Guardian veto audit tables, plus offline Qwen3.5 2B SLM inference serialized across workers (`slm_process_lock`) and `pynvml` VRAM probing.
- **PostgreSQL Delta Storage & Pooling:** Non-blocking async queue with 1-byte Smallint enums, run-length encoding (**97.9% storage reduction**, ~380 MB/day for 200 intersections), thread-safe `PostgresConnectionPool`, SQLite WAL pragmas (`busy_timeout=30000`), parameterized `make_interval` queries, and automated 168-hour EVP telemetry retention.
- **Single-Owner Go Hardware Gateway & Closed-Loop Control (`CARINA_GATEWAY_ROLE`):** Compiled CGO-free Go binary (`bin/carina-go`) exclusively owned by `CentralController` (`CARINA_GATEWAY_ROLE=owner`), while `AI_Process` and the UI mirror hardware state via `RemoteHardwareDriverProxy` and `ThreadSafePipeConnection` (`CARINA_GATEWAY_ROLE=remote`). Supports NTCIP 1202 (ASC `.4.1.*`/`.5.1.*`), UTMC2, SNMPv2c/SNMPv3 USM, per-intersection OID JSON profiles (`config_path`), binary SNMPv1/v2c/v3 trap decoding, closed-loop hardware stage decoding (`HardwareTelemetryDecoder`), and atomic fail-safe reversion with `resume_control` recovery.
- **Emergency Vehicle Preemption (EVP Subsystem):** Autonomous green corridors with two-factor activation (geometric approach gates $60\text{--}160\text{ m}$ + siren detection), direct SNMP phase holds via Go gateway (`stage_idx`/`stage_codes`), cross-process `EVPSnapshotSynchronizer`, Tailscale mesh Web Gateway (port 2201, HTTP 204 ingestion), and real-time CCO videowall streaming.
- **Transport & Endpoint Security (Zero-Trust Defaults):** Optional TLS/mTLS and Bearer token authentication (`CARINA_GRPC_*`) on Synapse gRPC (`:50051`), fail-closed `gateway_enabled=False` default (`503` when disabled), constant-time Bearer/Header token guards (`CARINA_EVP_AUTH_TOKEN`, `CARINA_CCO_AUTH_TOKEN`), explicit CORS (`CARINA_CCO_ALLOWED_ORIGIN`), Gateway HTTPS/TLS, and SHA-256 certificate pinning in `CCOBroadcastClient`.
- **Web CCO & Modern UI/UX (React 18 & Flet):** Real-time React 18 CCO videowall and mobile app with compositor-only animations (`transform`/`opacity`), `requestAnimationFrame` viewport pan/zoom, and `document.hidden` pauses; Flet desktop UI with paginated `AuditLogWidget`, hidden-window `MapAnimator` pause, and `RemoteGatewaySettingsPersister`.
- **Polymorphic Monitoring & Transports:** Dynamic dual-mode telemetry dispatcher supporting MQTT brokers and HTTP/HTTPS REST/Webhook cloud endpoints (Ngrok, Cloud services) with automatic protocol resolution and incident deduplication.
- **Modular Settings Subsystem (SOLID):** Decoupled configuration architecture combining typed schemas (`SettingsSchema`), INI storage, and 12-Factor `.env` secret providers with backward-compatible facades.
- **F.E.N.I.X. Self-Healing Subsystem (High Availability):** Autonomous process supervisor (`FenixSupervisor`, `fenix_supervision_loop.py`) monitoring AI engine health, with windowed exponential backoff crash recovery and closed-loop field stage reconciliation (`FenixStageDispatcher`).
- **Intra-Phase PBT & Developmental Maturation:** Evolutionary Population-Based Training with strict cohort isolation (`TEEN` $\leftrightarrow$ `TEEN`, `ADULT` $\leftrightarrow$ `ADULT`), childhood shadow shielding, and empirical fluid dynamics graduation margins ($\delta^*$).
- **Physical Reward Balancing (HCM Traffic Physics):** Dynamic Characteristic Travel Time link scaling ($\tau$) eliminating dimensional scale disparities between queue delay penalties and vehicle throughput incentives.

---

## 🚀 Quick Start

### 1. Requirements
Ensure you have Python 3.10+ and a CUDA-compatible GPU (accelerated via PyTorch AMP & NVIDIA TensorCores).

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Running the Ecosystem
```bash
python carina.py
```

---

<div align="center">
  <img src="docs/assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="48" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Controlled Artificial Road-traffic Intelligence Network Architecture • CARINA CORE v1.2.0</i><br/>
  <small>Licensed under the <a href="LICENSE">GNU Affero General Public License v3.0 or later</a> (SPDX: <code>AGPL-3.0-or-later</code>). © 2026 Noxfort Systems.</small>
</div>
