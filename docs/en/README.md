<div align="center">

<img src="../assets/carina-logo.png" alt="CARINA CORE Logo" width="120" />

# CARINA — Technical Documentation Suite
### System Architecture, Hardware Integration & Safety Framework
*Noxfort Systems — A State Of Art Company*

[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat&logo=github)](https://github.com/Noxfort-Systems-Brazil/CARINA)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?style=flat&logo=go)](https://go.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

🌐 **Translations:** **[🇺🇸 English](README.md)** • **[🇧🇷 Português](../pt-br/README.md)** • **[🇪🇸 Español](../es/README.md)** • **[🇫🇷 Français](../fr/README.md)** • **[🇷🇺 Русский](../ru/README.md)** • **[🇨🇳 简体中文](../zh/README.md)** • **[📚 Central Hub](../index.md)**

---

</div>

## Welcome to the Official Technical Documentation

This directory contains the canonical English documentation suite for **CARINA** (Controlled Artificial Road-traffic Intelligence Network Architecture) — an enterprise deep reinforcement learning ecosystem designed for distributed urban traffic light control.

## Technical Guide Directory

| Document | Topic | Key Contents |
|---|---|---|
| 📚 **[Central Master (MOC)](carina_moc.md)** | Master Index & Knowledge Graph | Codebase overview, architectural directory hierarchy, and Obsidian bi-directional graph. |
| 📖 **[System Architecture](architecture.md)** | Core Architecture | 8 concurrent OS microservices, ST-GATv2 Lite Graph Attention, Universal PAE, and Universal AMP acceleration. |
| 🚑 **[Emergency Preemption (EVP)](evp_and_preemption.md)** | Emergency Vehicle Preemption | Autonomous green corridors, Haversine entry/exit kinematics gates ($60\text{--}160\text{ m}$), Tailscale Web Gateway (port 2201), and CCO React videowall. |
| 🔌 **[Hardware Drivers & Go Gateway](hardware_drivers.md)** | Field Controllers | Industrial Go Hardware Gateway (`carina-go`), zero-port NDJSON pipe IPC, NTCIP 1202, UTMC2, SNMP client pool, and atomic fail-safe. |
| 🛡️ **[Safety Architecture, Watchdog & FENIX](safety_and_watchdog.md)** | Neuro-Symbolic Safety | Symbolic veto rules (SR-01 to SR-05), D3QN Guardian spillback vetoes, real-time Watchdog (< 500 ms), and F.E.N.I.X. auto-resurrection. |
| ⚡ **[Synapse HFT API & IPC Queues](api_reference.md)** | High-Frequency Interface | Sub-millisecond Synapse HFT gRPC interface (port 50051), 11 bounded IPC channels, and polymorphic telemetry transports. |
| 🗄️ **[Database Architecture & Schemas](database_and_schemas.md)** | Persistence & Schemas | PostgreSQL asynchronous delta storage engine achieving **97.9% storage reduction**, 1-byte Smallint enums, and 12-Factor `.env`. |
| 🧠 **[Neural Research & Formulations](research_notes.md)** | Mathematical Modeling | PPO-TCN temporal convolutions, PAE latent projections, Dueling DQN, ST-GATv2 Lite, and the DA SILVA curriculum. |
| 🚦 **[Traffic Signal Warrants (MUTCD)](traffic_engineering_warrants.md)** | Traffic Engineering | Algorithmic evaluation of formal FHWA/MUTCD regulatory signal warrants (Warrants 1, 2, 3, 4). |
| 📈 **[MFD & Network Traffic Analytics](mfd_and_analytics.md)** | Macroscopic Physics | Macroscopic Fundamental Diagram (MFD) regressions, capacity drop mitigation, perimeter gating, and incident filter cache. |
| 🔍 **[Explainable AI (XAI) & SAS](xai_and_sas.md)** | Municipal Audit & XAI | Google Captum Integrated Gradients, 5 formal mathematical equations, and Guardian veto forensic audit engine. |
| 📄 **[Report Blocks Engine](report_blocks_and_templates.md)** | Automated Reporting | ABNT NBR 14724 compliant Word (.docx) generation with native Office Math Markup Language (OMML) equations. |
| 🤖 **[Small Language Models (SLM)](slm_and_local_llm.md)** | Offline Private AI | Local 100% offline LLM inference (Qwen3.5 2B / llama.cpp) generating forensic textual explanations without cloud leakage. |
| 🖥️ **[Desktop UI & Planning View](ui_and_dashboard.md)** | Frontend Architecture | Native Flet desktop GUI, interactive vector planning view, system tray management, and single instance lock (port 42123). |
| 🗺️ **[Vector Map Rendering & Heatmaps](rendering_and_heatmaps.md)** | Geospatial Visualization | SUMO `.net.xml` offline vector parser and asynchronous real-time Kernel Density Estimation (KDE) heatmaps. |
| 🔐 **[Security & Authentication](security_and_auth.md)** | Governance & Access | Role-based access control (RBAC), salted PBKDF2 hashing, brute-force lockdown, and 12-Factor isolation. |
| 🛠️ **[Developer Guides](developer_guides.md)** | Engineering & Extension | Environment setup, custom neural agent implementation, and SOLID modular settings architecture. |
| 🧪 **[Testing & Quality Assurance](testing.md)** | QA & Test Suite | Pytest suite with 861 automated tests, native Go unit tests (`go test`), Guardian safety mocks, and coverage validation. |
| 🚀 **[Deployment & Packaging](deployment_and_packaging.md)** | Operations & Packaging | Multi-stage Docker containerization with CUDA acceleration and Linux Systemd daemon units. |

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>Intelligent Mobility Engineering • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. Licensed under AGPLv3 or later (SPDX: <code>AGPL-3.0-or-later</code>).</small>
</div>
