---
tags: [readme, home, carina]
aliases: [Projeto CARINA, Root]
---

<div align="center">

<img src="docs/assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="120" />

# CARINA CORE
### Cognitive Autonomous Real-time Intersection Network Architecture
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![License](https://img.shields.io/badge/License-AGPL_v3-blue?style=flat)](LICENSE)

[![CARINA GitHub Repository Card](https://github-readme-stats.vercel.app/api/pin/?username=Noxfort-Systems-Brazil&repo=CARINA&theme=dark)](https://github.com/Noxfort-Systems-Brazil/CARINA)

---

🌐 **Translations / Idiomas:** **[🇺🇸 English](README.md)** • **[🇧🇷 Português do Brasil](docs/pt-br/README.md)** • **[🇪🇸 Español](docs/es/README.md)** • **[🇫🇷 Français](docs/fr/README.md)** • **[🇷🇺 Русский](docs/ru/README.md)** • **[🇨🇳 简体中文](docs/zh/README.md)** • **[📚 Documentation Hub](docs/README.md)**

---

</div>

**CARINA** is a massively distributed Deep Reinforcement Learning ecosystem designed for real-time traffic control and smart city orchestration. Bypassing Python's Global Interpreter Lock (GIL) via 8 concurrent OS processes, it integrates a Tactical PPO agent, an ST-GATv2 Lite Graph Coordinator, a Global Consultant Agent (PAE 128-channel), and a Guardian Agent (D3QN) to provide 100% ABNT-compliant forensic auditability and neuro-symbolic safety.

---

## 📚 Documentation Hub & Knowledge Vault

Explore the full architecture, internal mechanics, and developer guides for the CARINA ecosystem:

| Card / Subsystem | Focus Area | Direct Link |
| :--- | :--- | :---: |
| 📚 **Documentation Hub** | Central Index & Navigation for all technical docs | [Explore Hub](docs/CARINA_MOC.md) |
| 🏛️ **Core Architecture** | 8 Concurrent OS microservices, ST-GATv2 Lite & Consultant PAE | [View Blueprint](ARCHITECTURE.md) |
| ⚡ **Synapse HFT API** | Sub-millisecond gRPC telemetry & Protobuf IPC specifications | [View API Reference](docs/API_REFERENCE.md) |
| 🧠 **Neural Formulations** | PPO-TCN, ST-GATv2 Lite, Cross-Attention & Consultant PAE | [View Research](docs/RESEARCH_NOTES.md) |
| 🚦 **Hardware Drivers** | Physical controllers (NTCIP 1202, UTMC2, SNMP Client & Traps) | [View Drivers](docs/HARDWARE_DRIVERS.md) |
| 🛡️ **Safety Firewall & Watchdog** | Guardian D3QN Vetoes, Symbolic rules & Watchdog | [View Safety Guide](docs/SAFETY_AND_WATCHDOG.md) |
| 📊 **Engineering Warrants** | MUTCD / FHWA Traffic Signal Warrants 1, 2, 3, 7, 8 | [View Warrants](docs/TRAFFIC_ENGINEERING_WARRANTS.md) |
| 📈 **MFD & Traffic Analytics** | Network density-flow curves, capacity drop & gating | [View MFD Guide](docs/MFD_AND_ANALYTICS.md) |
| 🗄️ **Database & Schemas** | PostgreSQL Delta Storage (97.9% reduction), 12-Factor Setup | [View DB Specs](docs/DATABASE_AND_SCHEMAS.md) |
| 🔍 **Explainable AI (XAI)** | Captum Integrated Gradients, 5 Formal Equations & Audits | [View XAI & SAS](docs/XAI_AND_SAS.md) |
| 📄 **Report Blocks Engine** | ABNT NBR 14724 Word (.docx) Builder & OMML Math Equations | [View Reports](docs/REPORT_BLOCKS_AND_TEMPLATES.md) |
| 🤖 **Small Language Models** | Local Qwen3 1.7B / llama.cpp Offline Textual Justification | [View SLM Guide](docs/SLM_AND_LOCAL_LLM.md) |
| 🖥️ **Flet UI & Planning** | Native desktop UI, Planning Canvas, System Tray & SDS | [View UI Guide](docs/UI_AND_DASHBOARD.md) |
| 🗺️ **Rendering & Heatmaps** | Vector Map Rendering & Asynchronous Heatmap Interpolation | [View Rendering](docs/RENDERING_AND_HEATMAPS.md) |
| 🔐 **Security & Auth** | User accounts, salted bcrypt hashing & brute-force lockdown | [View Security](docs/SECURITY_AND_AUTH.md) |
| 🛠️ **Developer Guides** | Agent development, settings configuration & setup | [View Guides](docs/DEVELOPER_GUIDES.md) |
| 🧪 **Testing & Validation** | Pytest suite, coverage reports & Guardian safety mocks | [View Guidelines](docs/TESTING.md) |
| 🚀 **Deployment & Packaging** | Docker containerization, Systemd services & Debian packages | [View Deployment](docs/DEPLOYMENT_AND_PACKAGING.md) |

---

## ⚡ Core Architecture (GOMES & DA SILVA)

- **Tactical Layer (PPO-TCN Edge AI):** Hyper-focused on local intersection throughput with sub-millisecond ($< 0.5\text{ ms}$) execution.
- **Strategic Layer (ST-GATv2 Lite):** Dynamic spatiotemporal graph attention coordinating Green Waves across urban avenues.
- **Global Consultant Layer (PAE 128-channel):** Event-triggered background mentor projecting future traffic states ($t + \Delta t$).
- **Guardian Layer (Neuro-Symbolic D3QN):** Inviolable safety firewall validating or vetoing actions against traffic codes and spillback risks.
- **Explainable AI (XAI Engine):** Google Captum Integrated Gradients exporting ABNT NBR 14724 reports with 5 formal neural equations and Guardian veto audit tables.
- **PostgreSQL Delta Storage:** Non-blocking async queue with 1-byte Smallint enums and run-length encoding achieving **97.9% storage reduction** (~380 MB/day for 200 intersections).
- **Go Hardware Gateway (Industrial Safety):** Dedicated, compiled CGO-free Go binary (`bin/carina-go`) handling field controller I/O (NTCIP 1202 & UTMC2 over UDP 161/162) with zero host open ports via OS pipe NDJSON IPC and atomic fail-safe reversion on disconnect.
- **Polymorphic Monitoring & Transports:** Dynamic dual-mode telemetry dispatcher supporting MQTT brokers and HTTP/HTTPS REST/Webhook cloud endpoints (Ngrok, Cloud services) with automatic protocol resolution and incident deduplication.
- **Modular Settings Subsystem (SOLID):** Decoupled configuration architecture combining typed schemas (`SettingsSchema`), INI storage, and 12-Factor `.env` secret providers with backward-compatible facades.
- **F.E.N.I.X. Self-Healing Subsystem (High Availability):** Autonomous process supervisor (`FenixSupervisor`) monitoring AI engine health, with windowed exponential backoff crash recovery and zero-collision stage boundary handover.

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
  <i>Cognitive Autonomous Real-time Intersection Network Architecture • CARINA CORE v1.2.0</i><br/>
  <small>Licensed under the <a href="LICENSE">GNU Affero General Public License v3.0</a>. © 2026 Noxfort Systems.</small>
</div>
